from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func

from app.database.database import Base


class Worker(Base):
    __tablename__ = "workers"

    worker_id = Column(String(100), primary_key=True)
    last_heartbeat = Column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
    status = Column(
        String(50),
        nullable=False,
        default="ALIVE"
    )