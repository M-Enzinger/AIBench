import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import requests

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import select

from .database import get_session, init_db
from .models import (
    AnswerType,
    BatchItem,
    Experiment,
    ExperimentExercise,
    ExperimentStatus,
    Exercise,
    ExerciseOption,
    Run,
    RunStatus,
    Settings,
)

app = FastAPI(title="AIBench")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


class OptionPayload(BaseModel):
    id: Optional[int]
    text: str
    position: int = 0


class ExercisePayload(BaseModel):
    question_text: str
    answer_type: AnswerType
    options: List[OptionPayload] = []


class ExperimentPayload(BaseModel):
    name: str
    description: str = ""
    provider: str
    model: str
    temperature: float = 0.0
    runs: int = 1
    exercise_ids: List[int]


class SettingsPayload(BaseModel):
    openai_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    gemini_key: Optional[str] = None
    grok_key: Optional[str] = None


def get_settings(session) -> Settings:
    settings = session.exec(select(Settings)).first()
    if not settings:
        settings = Settings()
        session.add(settings)
        session.commit()
        session.refresh(settings)
    return settings


def build_prompt(exercise: Exercise, options: List[ExerciseOption]):
    """Construct a JSON template the model must complete."""

    response_format = {}
    if exercise.answer_type == AnswerType.FREE_TEXT:
        response_format = {"response": {"text": "<fill with concise answer text>"}}
    elif exercise.answer_type == AnswerType.TRUE_FALSE:
        response_format = {"response": {"value": "true or false"}}
    elif exercise.answer_type == AnswerType.SINGLE_CHOICE:
        response_format = {
            "response": {
                "selected_option_id": "id from provided options",
                "options": [{"id": opt.id, "text": opt.text} for opt in options],
            }
        }
    elif exercise.answer_type == AnswerType.RANKING:
        response_format = {
            "response": {
                "ordered_option_ids": "array of option ids ordered best to worst (or as requested)",
                "options": [{"id": opt.id, "text": opt.text} for opt in options],
            }
        }

    return {
        "question": exercise.question_text,
        "answer_type": exercise.answer_type,
        "options": [{"id": opt.id, "text": opt.text} for opt in options],
        "response": response_format.get("response", {}),
        "instructions": "Return ONLY JSON. Do not include explanations.",
    }


def call_openai(model: str, temperature: float, prompt: dict, api_key: str):
    system_message = (
        "You are an assistant that answers strictly in JSON. "
        "Use the provided JSON schema and fill only the response fields without extra text."
    )
    user_message = """
Read the JSON template below. Fill only the `response` fields with the answer.
Return ONLY JSON with the same top-level keys.
""".strip()
    full_payload = {"template": prompt}
    payload = {
        "model": model,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_message},
            {
                "role": "user",
                "content": f"{user_message}\n{json.dumps(full_payload, ensure_ascii=False)}",
            },
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    response = requests.post(
        "https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=60
    )
    response.raise_for_status()
    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"response": {"text": content}}


def generate_model_response(
    provider: str, model: str, temperature: float, prompt: dict, settings: Settings, exercise: Exercise, options: List[ExerciseOption]
):
    if provider == "openai" and settings.openai_key:
        return call_openai(model, temperature, prompt, settings.openai_key)
    # Additional providers could be added here; fallback to deterministic sample
    if exercise.answer_type == AnswerType.FREE_TEXT:
        return {"response": {"text": ""}}
    if exercise.answer_type == AnswerType.TRUE_FALSE:
        return {"response": {"value": True}}
    if exercise.answer_type == AnswerType.SINGLE_CHOICE:
        chosen = options[0].id if options else None
        return {"response": {"selected_option_id": chosen}}
    if exercise.answer_type == AnswerType.RANKING:
        ordered = [opt.id for opt in sorted(options, key=lambda o: o.position)]
        return {"response": {"ordered_option_ids": ordered}}
    return {}


def store_batch_item(
    session, run: Run, experiment: Experiment, settings: Settings, exercise: Exercise, options: List[ExerciseOption]
):
    prompt = build_prompt(exercise, options)
    parse_success = True
    try:
        response_json = generate_model_response(
            experiment.provider, experiment.model, experiment.temperature, prompt, settings, exercise, options
        )
    except Exception:
        response_json = {}
        parse_success = False
    answer_text = None
    answer_bool = None
    answer_option_id = None
    answer_ranking = None
    try:
        # Handle both current "response" key and legacy "expected.response" structures
        response_section = response_json.get("response") or response_json.get("expected", {}).get("response", {})
        if exercise.answer_type == AnswerType.FREE_TEXT:
            answer_text = str(response_section.get("text", "")).strip()
        elif exercise.answer_type == AnswerType.TRUE_FALSE:
            val = response_section.get("value")
            if isinstance(val, str):
                val_lower = val.strip().lower()
                if val_lower in {"true", "yes", "y"}:
                    val = True
                elif val_lower in {"false", "no", "n"}:
                    val = False
            answer_bool = bool(val) if val is not None else None
        elif exercise.answer_type == AnswerType.SINGLE_CHOICE:
            answer_option_id = response_section.get("selected_option_id")
        elif exercise.answer_type == AnswerType.RANKING:
            ranking_ids = response_section.get("ordered_option_ids")
            if isinstance(ranking_ids, list):
                answer_ranking = json.dumps(ranking_ids)
    except Exception:
        parse_success = False

    batch_item = BatchItem(
        run_id=run.id,
        exercise_id=exercise.id,
        question_text=exercise.question_text,
        answer_type=exercise.answer_type,
        options_json=json.dumps([{"id": opt.id, "text": opt.text} for opt in options]),
        answer_text=answer_text,
        answer_boolean=answer_bool,
        answer_option_id=answer_option_id,
        answer_ranking_json=answer_ranking,
        parse_success=parse_success,
    )
    session.add(batch_item)


def execute_experiment(experiment_id: int):
    with get_session() as session:
        experiment = session.get(Experiment, experiment_id)
        if not experiment:
            return
        try:
            experiment.status = ExperimentStatus.RUNNING
            session.commit()
            settings = get_settings(session)
            ex_links = session.exec(
                select(ExperimentExercise)
                .where(ExperimentExercise.experiment_id == experiment_id)
                .order_by(ExperimentExercise.position)
            ).all()
            exercises = []
            for link in ex_links:
                ex = session.get(Exercise, link.exercise_id)
                if ex:
                    options = session.exec(
                        select(ExerciseOption)
                        .where(ExerciseOption.exercise_id == ex.id)
                        .order_by(ExerciseOption.position)
                    ).all()
                    exercises.append((ex, options))
            for idx in range(1, experiment.runs + 1):
                run = Run(
                    experiment_id=experiment.id,
                    run_index=idx,
                    provider=experiment.provider,
                    model=experiment.model,
                    temperature=experiment.temperature,
                    status=RunStatus.RUNNING,
                )
                session.add(run)
                session.commit()
                session.refresh(run)

                for exercise, options in exercises:
                    store_batch_item(session, run, experiment, settings, exercise, options)
                run.status = RunStatus.COMPLETED
                run.completed_at = datetime.utcnow()
                session.commit()
            experiment.status = ExperimentStatus.FINISHED
            session.commit()
        except Exception:
            experiment.status = ExperimentStatus.FAILED
            session.commit()


@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/api/settings")
def read_settings():
    with get_session() as session:
        settings = get_settings(session)
        return settings


@app.post("/api/settings")
def update_settings(payload: SettingsPayload):
    with get_session() as session:
        settings = get_settings(session)
        for field, value in payload.dict().items():
            setattr(settings, field, value)
        settings.updated_at = datetime.utcnow()
        session.add(settings)
        session.commit()
        session.refresh(settings)
        return settings


@app.get("/api/exercises")
def list_exercises():
    with get_session() as session:
        exercises = session.exec(select(Exercise)).all()
        response = []
        for ex in exercises:
            options = session.exec(
                select(ExerciseOption)
                .where(ExerciseOption.exercise_id == ex.id)
                .order_by(ExerciseOption.position)
            ).all()
            response.append({
                "id": ex.id,
                "question_text": ex.question_text,
                "answer_type": ex.answer_type,
                "options": options,
            })
        return response


@app.post("/api/exercises")
def create_exercise(payload: ExercisePayload):
    with get_session() as session:
        exercise = Exercise(question_text=payload.question_text, answer_type=payload.answer_type)
        session.add(exercise)
        session.commit()
        session.refresh(exercise)
        for opt in payload.options:
            option = ExerciseOption(exercise_id=exercise.id, text=opt.text, position=opt.position)
            session.add(option)
        session.commit()
        return {"id": exercise.id}


@app.put("/api/exercises/{exercise_id}")
def update_exercise(exercise_id: int, payload: ExercisePayload):
    with get_session() as session:
        exercise = session.get(Exercise, exercise_id)
        if not exercise:
            raise HTTPException(status_code=404, detail="Exercise not found")
        exercise.question_text = payload.question_text
        exercise.answer_type = payload.answer_type
        session.commit()
        existing = session.exec(select(ExerciseOption).where(ExerciseOption.exercise_id == exercise_id)).all()
        for opt in existing:
            session.delete(opt)
        session.commit()
        for opt in payload.options:
            option = ExerciseOption(exercise_id=exercise_id, text=opt.text, position=opt.position)
            session.add(option)
        session.commit()
        return {"status": "updated"}


@app.post("/api/exercises/{exercise_id}/duplicate")
def duplicate_exercise(exercise_id: int):
    with get_session() as session:
        exercise = session.get(Exercise, exercise_id)
        if not exercise:
            raise HTTPException(status_code=404, detail="Exercise not found")
        new_ex = Exercise(question_text=exercise.question_text, answer_type=exercise.answer_type)
        session.add(new_ex)
        session.commit()
        session.refresh(new_ex)
        options = session.exec(
            select(ExerciseOption).where(ExerciseOption.exercise_id == exercise_id)
        ).all()
        for opt in options:
            session.add(ExerciseOption(exercise_id=new_ex.id, text=opt.text, position=opt.position))
        session.commit()
        return {"id": new_ex.id}


@app.delete("/api/exercises/{exercise_id}")
def delete_exercise(exercise_id: int):
    with get_session() as session:
        exercise = session.get(Exercise, exercise_id)
        if not exercise:
            raise HTTPException(status_code=404, detail="Exercise not found")
        options = session.exec(select(ExerciseOption).where(ExerciseOption.exercise_id == exercise_id)).all()
        for opt in options:
            session.delete(opt)
        links = session.exec(select(ExperimentExercise).where(ExperimentExercise.exercise_id == exercise_id)).all()
        for link in links:
            session.delete(link)
        session.delete(exercise)
        session.commit()
        return {"status": "deleted"}


@app.get("/api/experiments")
def list_experiments():
    with get_session() as session:
        experiments = session.exec(select(Experiment)).all()
        results = []
        for exp in experiments:
            completed = session.exec(
                select(Run).where(Run.experiment_id == exp.id, Run.status == RunStatus.COMPLETED)
            ).all()
            results.append(
                {
                    "id": exp.id,
                    "name": exp.name,
                    "description": exp.description,
                    "provider": exp.provider,
                    "model": exp.model,
                    "temperature": exp.temperature,
                    "runs": exp.runs,
                    "status": exp.status,
                    "created_at": exp.created_at,
                    "completed_runs": len(completed),
                }
            )
        return results


@app.get("/api/experiments/{experiment_id}")
def get_experiment(experiment_id: int):
    with get_session() as session:
        experiment = session.get(Experiment, experiment_id)
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
        completed_runs = session.exec(
            select(Run).where(Run.experiment_id == experiment_id, Run.status == RunStatus.COMPLETED)
        ).all()
        return {
            "id": experiment.id,
            "name": experiment.name,
            "description": experiment.description,
            "provider": experiment.provider,
            "model": experiment.model,
            "temperature": experiment.temperature,
            "runs": experiment.runs,
            "status": experiment.status,
            "created_at": experiment.created_at,
            "completed_runs": len(completed_runs),
        }


@app.get("/api/experiments/{experiment_id}/exercises")
def experiment_exercises(experiment_id: int):
    with get_session() as session:
        experiment = session.get(Experiment, experiment_id)
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
        links = session.exec(
            select(ExperimentExercise)
            .where(ExperimentExercise.experiment_id == experiment_id)
            .order_by(ExperimentExercise.position)
        ).all()
        response = []
        run_ids = [r.id for r in session.exec(select(Run).where(Run.experiment_id == experiment_id)).all()]
        for link in links:
            ex = session.get(Exercise, link.exercise_id)
            options = session.exec(
                select(ExerciseOption)
                .where(ExerciseOption.exercise_id == link.exercise_id)
                .order_by(ExerciseOption.position)
            ).all()
            count_items = []
            if run_ids:
                count_items = session.exec(
                    select(BatchItem).where(BatchItem.exercise_id == link.exercise_id, BatchItem.run_id.in_(run_ids))
                ).all()
            response.append(
                {
                    "exercise_id": ex.id,
                    "question_text": ex.question_text,
                    "answer_type": ex.answer_type,
                    "options": options,
                    "completed_items": len(count_items),
                }
            )
        return response


@app.get("/api/experiments/{experiment_id}/exercises/{exercise_id}/batch_items")
def list_batch_items(experiment_id: int, exercise_id: int):
    with get_session() as session:
        runs = session.exec(select(Run).where(Run.experiment_id == experiment_id)).all()
        run_ids = [r.id for r in runs]
        if not run_ids:
            return []
        items = session.exec(
            select(BatchItem).where(BatchItem.run_id.in_(run_ids), BatchItem.exercise_id == exercise_id)
        ).all()
        response = []
        for item in items:
            run = session.get(Run, item.run_id)
            display_answer = None
            if item.answer_type == AnswerType.FREE_TEXT:
                display_answer = item.answer_text
            elif item.answer_type == AnswerType.TRUE_FALSE:
                display_answer = item.answer_boolean
            elif item.answer_type == AnswerType.SINGLE_CHOICE:
                display_answer = item.answer_option_id
            elif item.answer_type == AnswerType.RANKING and item.answer_ranking_json:
                display_answer = json.loads(item.answer_ranking_json)
            response.append(
                {
                    "id": item.id,
                    "run_index": run.run_index if run else None,
                    "parse_success": item.parse_success,
                    "answer": display_answer,
                }
            )
        return response


@app.post("/api/experiments")
def create_experiment(payload: ExperimentPayload, background_tasks: BackgroundTasks):
    with get_session() as session:
        settings = get_settings(session)
        provider_key_map = {
            "openai": settings.openai_key,
            "anthropic": settings.anthropic_key,
            "gemini": settings.gemini_key,
            "grok": settings.grok_key,
        }
        if payload.provider in provider_key_map and not provider_key_map[payload.provider]:
            raise HTTPException(status_code=400, detail="API key missing for selected provider")
        if not payload.exercise_ids:
            raise HTTPException(status_code=400, detail="Select at least one exercise")
        experiment = Experiment(
            name=payload.name,
            description=payload.description,
            provider=payload.provider,
            model=payload.model,
            temperature=payload.temperature,
            runs=payload.runs,
            status=ExperimentStatus.PLANNED,
        )
        session.add(experiment)
        session.commit()
        session.refresh(experiment)
        for idx, ex_id in enumerate(payload.exercise_ids):
            link = ExperimentExercise(experiment_id=experiment.id, exercise_id=ex_id, position=idx)
            session.add(link)
        session.commit()
        background_tasks.add_task(execute_experiment, experiment.id)
        return {"id": experiment.id}


@app.get("/")
async def serve_frontend():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return {"message": "Frontend not built yet."}
    return FileResponse(index_file)


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Not found"}
