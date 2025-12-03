import json
import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api import deps
from app.models.experiment import Experiment, Run
from app.models.scenario import Scenario
from app.schemas.experiment import ExperimentCreate, ExperimentRead, RunRead

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("/", response_model=List[ExperimentRead])
def list_experiments(db: Session = Depends(deps.get_db)):
    return db.query(Experiment).order_by(Experiment.created_at.desc()).all()


@router.post("/", response_model=ExperimentRead)
def create_experiment(payload: ExperimentCreate, db: Session = Depends(deps.get_db)):
    scenario = db.query(Scenario).get(payload.scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    experiment = Experiment(**payload.model_dump(exclude={"ai_sources"}))
    experiment.ai_sources = json.dumps([src.model_dump() for src in payload.ai_sources])
    if payload.ai_sources:
        primary = payload.ai_sources[0]
        experiment.model_provider = primary.provider
        experiment.model_name = primary.model
    db.add(experiment)
    db.commit()
    db.refresh(experiment)

    # Create illustrative runs to show multi-source storage
    ai_sources = [src.model_dump() for src in payload.ai_sources] or [
        {
            "label": f"{payload.model_provider}:{payload.model_name}",
            "provider": payload.model_provider,
            "model": payload.model_name,
            "runs": payload.run_count,
        }
    ]

    for source in ai_sources:
        for i in range(int(source.get("runs", 0))):
            run = Run(
                experiment_id=experiment.id,
                source_label=source.get("label") or f"{source.get('provider')}:{source.get('model')}",
                prompt=f"Prompt for {source.get('label', 'ai source')} run {i+1}",
                raw_response=json.dumps({"answers": {"example": random.random()}}),
                parsed_response=json.dumps({"answers": {"example": random.random()}}),
                status="completed",
            )
            db.add(run)

    if payload.human_enabled and payload.human_participants > 0:
        for i in range(payload.human_participants):
            run = Run(
                experiment_id=experiment.id,
                source_label="human",
                prompt=f"Human task sheet {i+1}",
                raw_response=json.dumps({"answers": {"example": random.random()}}),
                parsed_response=json.dumps({"answers": {"example": random.random()}}),
                status="completed",
            )
            db.add(run)
    db.commit()
    return experiment


@router.get("/{experiment_id}", response_model=ExperimentRead)
def get_experiment(experiment_id: int, db: Session = Depends(deps.get_db)):
    experiment = db.query(Experiment).get(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@router.get("/{experiment_id}/runs", response_model=List[RunRead])
def get_runs(experiment_id: int, db: Session = Depends(deps.get_db)):
    return db.query(Run).filter(Run.experiment_id == experiment_id).order_by(Run.created_at.desc()).all()
