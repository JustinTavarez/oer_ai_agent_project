from typing import Any, Literal, Optional

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


# ---------------------------------------------------------------------------
# Search request
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str
    course_code: Optional[str] = None
    source: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=20)
    grounded: bool = False


# ---------------------------------------------------------------------------
# Internal retrieval models (kept for raw-hit normalisation)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Evaluated response models (steps 9-11)
# ---------------------------------------------------------------------------

RUBRIC_BASIS = Literal["verified", "inferred", "unavailable"]
LICENSE_STATUS = Literal["open", "unclear", "not_open", "unknown"]

NEUTRAL_SCORE = 3.0


class RubricScore(BaseModel):
    score: float = Field(ge=1.0, le=5.0, default=NEUTRAL_SCORE)
    reasoning: str = ""
    basis: RUBRIC_BASIS = "unavailable"


class RubricEvaluation(BaseModel):
    relevance_and_comprehensiveness: RubricScore = Field(default_factory=RubricScore)
    interactivity_and_engagement: RubricScore = Field(default_factory=RubricScore)
    pedagogical_soundness: RubricScore = Field(default_factory=RubricScore)
    licensing_clarity: RubricScore = Field(default_factory=RubricScore)
    accessibility_compliance: RubricScore = Field(default_factory=RubricScore)
    modularity_and_adaptability: RubricScore = Field(default_factory=RubricScore)
    supplementary_resources: RubricScore = Field(default_factory=RubricScore)


class LicenseInfo(BaseModel):
    status: LICENSE_STATUS = "unknown"
    details: str = ""


class RelevanceInfo(BaseModel):
    score: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning: str = ""


class EvaluatedResource(BaseModel):
    resource_id: str
    title: str = ""
    description: str = ""
    source: str = ""
    url: str = ""
    course_code: str = ""
    relevance: RelevanceInfo = Field(default_factory=RelevanceInfo)
    license: LicenseInfo = Field(default_factory=LicenseInfo)
    integration_tips: list[str] = Field(default_factory=list)
    rubric_evaluation: RubricEvaluation = Field(default_factory=RubricEvaluation)
    warnings: list[str] = Field(default_factory=list)


class EvaluatedSearchResponse(BaseModel):
    query: str
    timestamp: str
    log_id: str
    summary: str = ""
    results: list[EvaluatedResource] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
