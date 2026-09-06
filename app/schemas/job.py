from pydantic import BaseModel
from typing import Dict, Any, Optional,List
from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    type: str
    input: Dict[str, Any]
    idempotency_key: Optional[str] = None
    priority: int = 5
    depends_on: Optional[int] = None
    dependencies: List[int] = Field(default_factory=list)