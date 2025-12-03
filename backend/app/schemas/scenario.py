from pydantic import BaseModel
from datetime import datetime


class ScenarioBase(BaseModel):
    name: str
    version: str = "1.0"
    description: str = ""
    specification: str


class ScenarioCreate(ScenarioBase):
    pass


class ScenarioRead(ScenarioBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
