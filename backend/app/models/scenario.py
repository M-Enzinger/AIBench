from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.db.session import Base


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    version = Column(String, default="1.0")
    description = Column(Text, default="")
    specification = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
