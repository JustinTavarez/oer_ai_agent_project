from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

_SAFE_BOOL_TRUE = {True, 1, "true", "True", "TRUE"}
_SAFE_BOOL_FALSE = {False, 0, "false", "False", "FALSE"}


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

    @field_validator("has_accessibility_info", "has_supplementary_materials", mode="before")
    @classmethod
    def _coerce_safe_bool(cls, v: Any) -> bool:
        if v in _SAFE_BOOL_TRUE:
            return True
        if v in _SAFE_BOOL_FALSE:
            return False
        raise ValueError(
            f"Unsafe boolean value: {v!r}. "
            f"Accepted: True, False, 0, 1, 'true', 'false'."
        )


class SearchResult(BaseModel):
    id: str
    content: str
    title: str = ""
    source: str = ""
    course_code: str = ""
    license: str = ""
    url: str = ""
    chunk_index: int = 0
    score: float
    metadata: SearchResultMetadata = Field(default_factory=SearchResultMetadata)


class GroundedResponse(BaseModel):
    summary: str
    recommendations: list[dict]


class SearchResponse(BaseModel):
    results: list[SearchResult]
    grounded_response: Optional[GroundedResponse] = None
    message: str = ""
