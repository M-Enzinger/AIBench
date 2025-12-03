from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List
import json


class AISource(BaseModel):
    label: Optional[str] = None
    provider: str
    model: str
    runs: int = 1
    temperature: Optional[float] = None


class ExperimentBase(BaseModel):
    name: str
    scenario_id: int
    model_provider: str
    model_name: str
    ai_sources: List[AISource] = []
    run_count: int = 10
    temperature: str = "0.7"
    human_enabled: bool = False
    human_participants: int = 0
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

    @field_validator("ai_sources", mode="before")
    @classmethod
    def parse_ai_sources(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v


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
