from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ExperimentBase(BaseModel):
    name: str
    scenario_id: int
    model_provider: str
    model_name: str
    run_count: int = 10
    temperature: str = "0.7"
    human_enabled: bool = False
    ai_enabled: bool = True
    parallel_requests: int = 1
    settings: str = "{}"


class ExperimentCreate(ExperimentBase):
    pass


class ExperimentRead(ExperimentBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class RunRead(BaseModel):
    id: int
    experiment_id: int
    status: str
    source_label: str
    prompt: Optional[str]
    raw_response: Optional[str]
    parsed_response: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
