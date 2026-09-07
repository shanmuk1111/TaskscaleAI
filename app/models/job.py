from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    input = Column(JSONB, nullable=False)
    result = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)

    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    priority = Column(Integer, nullable=False, default=5)
    worker_id = Column(String(100), nullable=True)
    idempotency_key = Column(String(255), nullable=True)
    
    dependencies = Column(JSONB, nullable=False, default=list)
    depends_on = Column(Integer, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)