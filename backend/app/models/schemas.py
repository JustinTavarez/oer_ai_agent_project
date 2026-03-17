from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    prompt: str
    course: Optional[str] = None
    source_filter: Optional[str] = None


class ChatResponse(BaseModel):
    response: str


class HealthResponse(BaseModel):
    status: str
    lm_studio: str
