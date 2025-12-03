from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api import deps
from app.models.scenario import Scenario
from app.schemas.scenario import ScenarioCreate, ScenarioRead

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("/", response_model=List[ScenarioRead])
def list_scenarios(db: Session = Depends(deps.get_db)):
    return db.query(Scenario).order_by(Scenario.created_at.desc()).all()


@router.post("/", response_model=ScenarioRead)
def create_scenario(payload: ScenarioCreate, db: Session = Depends(deps.get_db), user=Depends(deps.get_current_user)):
    scenario = Scenario(
        name=payload.name,
        version=payload.version,
        description=payload.description,
        specification=payload.specification,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario


@router.get("/{scenario_id}", response_model=ScenarioRead)
def get_scenario(scenario_id: int, db: Session = Depends(deps.get_db)):
    scenario = db.query(Scenario).get(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.delete("/{scenario_id}")
def delete_scenario(scenario_id: int, db: Session = Depends(deps.get_db), user=Depends(deps.get_current_user)):
    scenario = db.query(Scenario).get(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    db.delete(scenario)
    db.commit()
    return {"status": "deleted"}
