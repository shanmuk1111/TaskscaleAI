from pydantic import BaseModel
from typing import Dict, Any, Optional


class JobCreate(BaseModel):
    type: str
    input: Dict[str, Any]
    idempotency_key: Optional[str] = None