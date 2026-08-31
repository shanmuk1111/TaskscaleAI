from pydantic import BaseModel


class JobCreate(BaseModel):
    type: str
    input: dict