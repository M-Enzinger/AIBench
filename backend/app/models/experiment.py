from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func, Boolean
from sqlalchemy.orm import relationship
from app.db.session import Base


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"))
    model_provider = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    ai_sources = Column(Text, default="[]")
    run_count = Column(Integer, default=10)
    temperature = Column(String, default="0.7")
    human_enabled = Column(Boolean, default=False)
    human_participants = Column(Integer, default=0)
    ai_enabled = Column(Boolean, default=True)
    parallel_requests = Column(Integer, default=1)
    settings = Column(Text, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    scenario = relationship("Scenario")
    runs = relationship("Run", back_populates="experiment", cascade="all, delete-orphan")


class Run(Base):
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"))
    source_label = Column(String, default="ai")
    prompt = Column(Text)
    raw_response = Column(Text)
    parsed_response = Column(Text)
    status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    experiment = relationship("Experiment", back_populates="runs")
