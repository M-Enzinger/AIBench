from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class AnswerType(str, Enum):
    FREE_TEXT = "free_text"
    TRUE_FALSE = "true_false"
    SINGLE_CHOICE = "single_choice"
    RANKING = "ranking"


class Exercise(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    question_text: str
    answer_type: AnswerType
    created_at: datetime = Field(default_factory=datetime.utcnow)
    options: List["ExerciseOption"] = Relationship(back_populates="exercise")


class ExerciseOption(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    exercise_id: int = Field(foreign_key="exercise.id")
    text: str
    position: int = 0
    exercise: Optional[Exercise] = Relationship(back_populates="options")


class ExperimentExercise(SQLModel, table=True):
    experiment_id: int = Field(foreign_key="experiment.id", primary_key=True)
    exercise_id: int = Field(foreign_key="exercise.id", primary_key=True)
    position: int = 0
    exercise: Optional[Exercise] = Relationship()
    experiment: Optional["Experiment"] = Relationship(back_populates="exercises")


class ExperimentStatus(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"


class Experiment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str = ""
    provider: str
    model: str
    temperature: float = 0.0
    runs: int = 1
    status: ExperimentStatus = Field(default=ExperimentStatus.PLANNED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    exercises: List[ExperimentExercise] = Relationship(back_populates="experiment")


class RunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Run(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_id: int = Field(foreign_key="experiment.id")
    run_index: int
    provider: str
    model: str
    temperature: float
    status: RunStatus = Field(default=RunStatus.RUNNING)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class BatchItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="run.id")
    exercise_id: int = Field(foreign_key="exercise.id")
    question_text: str
    answer_type: AnswerType
    options_json: Optional[str] = None
    answer_text: Optional[str] = None
    answer_boolean: Optional[bool] = None
    answer_option_id: Optional[int] = None
    answer_ranking_json: Optional[str] = None
    parse_success: bool = True


class Settings(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    openai_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    gemini_key: Optional[str] = None
    grok_key: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
