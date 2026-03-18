from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str
    course: Optional[str] = None
    source_filter: Optional[str] = None


class ChatResponse(BaseModel):
    response: str


class HealthResponse(BaseModel):
    status: str
    lm_studio: str


# Search schemas:
class SearchRequest(BaseModel):
    query: str
    course_code: Optional[str] = None
    source: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=20)
    grounded: bool = False


class SearchResultMetadata(BaseModel):
    resource_type: str = ""
    subject: str = ""
    term: str = ""
    institution: str = ""
    has_accessibility_info: bool = False
    has_supplementary_materials: bool = False


class SearchResult(BaseModel):
    id: str
    content: str
    title: str
    source: str
    course_code: str
    license: str
    url: str
    chunk_index: int
    score: float
    metadata: SearchResultMetadata


class GroundedResponse(BaseModel):
    summary: str
    recommendations: list[dict]


class SearchResponse(BaseModel):
    results: list[SearchResult]
    grounded_response: Optional[GroundedResponse] = None
    message: str = ""
