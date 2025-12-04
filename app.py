import os
import csv
import io
from datetime import datetime
from typing import List, Dict, Any

from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///storage/data.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
CORS(app)


class ExerciseTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ExerciseExecution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey("exercise_template.id"), nullable=False)
    provider = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(255), nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    runs_requested = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    template = db.relationship("ExerciseTemplate", backref=db.backref("executions", lazy=True))


class ExerciseRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    execution_id = db.Column(db.Integer, db.ForeignKey("exercise_execution.id"), nullable=False)
    run_index = db.Column(db.Integer, nullable=False)
    provider = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(255), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    answer_text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    execution = db.relationship("ExerciseExecution", backref=db.backref("runs", lazy=True))


def init_db():
    os.makedirs("storage", exist_ok=True)
    db.create_all()


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/templates", methods=["GET"])
def list_templates():
    templates = ExerciseTemplate.query.order_by(ExerciseTemplate.created_at.desc()).all()
    return jsonify([
        {
            "id": t.id,
            "title": t.title,
            "question_text": t.question_text,
            "created_at": t.created_at.isoformat(),
        }
        for t in templates
    ])


@app.route("/api/templates", methods=["POST"])
def create_template():
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    question_text = (data.get("question_text") or "").strip()
    if not title or not question_text:
        return jsonify({"error": "Title and question text are required."}), 400

    template = ExerciseTemplate(title=title, question_text=question_text)
    db.session.add(template)
    db.session.commit()
    return jsonify({"id": template.id}), 201


@app.route("/api/templates/<int:template_id>/executions", methods=["GET"])
def list_executions(template_id: int):
    executions = (
        ExerciseExecution.query.filter_by(template_id=template_id)
        .order_by(ExerciseExecution.created_at.desc())
        .all()
    )
    return jsonify([
        {
            "id": e.id,
            "provider": e.provider,
            "model": e.model,
            "temperature": e.temperature,
            "runs_requested": e.runs_requested,
            "created_at": e.created_at.isoformat(),
        }
        for e in executions
    ])


@app.route("/api/executions/<int:execution_id>/runs", methods=["GET"])
def list_runs(execution_id: int):
    runs = (
        ExerciseRun.query.filter_by(execution_id=execution_id)
        .order_by(ExerciseRun.run_index.asc())
        .all()
    )
    return jsonify([
        {
            "id": r.id,
            "run_index": r.run_index,
            "provider": r.provider,
            "model": r.model,
            "question_text": r.question_text,
            "answer_text": r.answer_text,
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ])


@app.route("/api/executions/<int:execution_id>/runs/csv", methods=["GET"])
def export_runs_csv(execution_id: int):
    runs = (
        ExerciseRun.query.filter_by(execution_id=execution_id)
        .order_by(ExerciseRun.run_index.asc())
        .all()
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["run_index", "provider", "model", "question_text", "answer_text", "created_at"])
    for r in runs:
        writer.writerow([
            r.run_index,
            r.provider,
            r.model,
            r.question_text,
            r.answer_text,
            r.created_at.isoformat(),
        ])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"execution_{execution_id}_runs.csv",
    )


@app.route("/api/executions", methods=["POST"])
def start_execution():
    data = request.get_json() or {}
    try:
        template_id = int(data.get("template_id"))
        runs_requested = int(data.get("runs_requested"))
        temperature = float(data.get("temperature"))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid numeric input."}), 400

    provider = (data.get("provider") or "").strip().lower()
    model = (data.get("model") or "").strip()

    if provider not in {"openai", "anthropic", "gemini", "grok"}:
        return jsonify({"error": "Invalid provider."}), 400
    if not model:
        return jsonify({"error": "Model is required."}), 400
    if runs_requested < 1:
        return jsonify({"error": "Runs must be at least 1."}), 400

    template = ExerciseTemplate.query.get(template_id)
    if not template:
        return jsonify({"error": "Template not found."}), 404

    required_key = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "grok": "GROK_API_KEY",
    }[provider]
    api_key = os.environ.get(required_key)
    if not api_key:
        return jsonify({"error": f"Missing API key for {provider}. Set {required_key}."}), 400

    execution = ExerciseExecution(
        template_id=template.id,
        provider=provider,
        model=model,
        temperature=temperature,
        runs_requested=runs_requested,
    )
    db.session.add(execution)
    db.session.commit()

    runs = []
    for idx in range(1, runs_requested + 1):
        answer = call_model(
            provider=provider,
            model=model,
            temperature=temperature,
            api_key=api_key,
            question_text=template.question_text,
        )
        run = ExerciseRun(
            execution_id=execution.id,
            run_index=idx,
            provider=provider,
            model=model,
            question_text=template.question_text,
            answer_text=answer,
        )
        db.session.add(run)
        runs.append(run)
    db.session.commit()

    return jsonify({"execution_id": execution.id, "runs_created": len(runs)}), 201


def call_model(provider: str, model: str, temperature: float, api_key: str, question_text: str) -> str:
    system_message = "You are a helpful assistant. Follow the user instructions exactly."
    user_message = question_text
    format_instruction = (
        "Answer exactly in the format requested in the question. "
        "Return only the answer, with no explanations, no extra words, no quotes, and no surrounding text."
    )

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
                {"role": "system", "content": format_instruction},
            ],
        )
        return response.choices[0].message.content.strip()

    if provider == "grok":
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
                {"role": "system", "content": format_instruction},
            ],
        )
        return response.choices[0].message.content.strip()

    if provider == "anthropic":
        import anthropic

        client = anthropic.Client(api_key=api_key)
        message = client.messages.create(
            model=model,
            temperature=temperature,
            max_tokens=1000,
            system=system_message,
            messages=[
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": format_instruction},
            ],
        )
        return "".join([block.text for block in message.content])

    if provider == "gemini":
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model_client = genai.GenerativeModel(model)
        prompt = f"{system_message}\n\n{user_message}\n\n{format_instruction}"
        response = model_client.generate_content(prompt, generation_config={"temperature": temperature})
        return response.text or ""

    raise ValueError("Unsupported provider")


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 2222)))
