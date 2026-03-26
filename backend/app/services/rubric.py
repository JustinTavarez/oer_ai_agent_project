"""Hybrid rule-based + LLM-based rubric evaluation for OER resources."""

import re
from typing import Any, Dict

from app.models.schemas import (
    NEUTRAL_SCORE,
    LicenseInfo,
    RubricEvaluation,
    RubricScore,
)

_CC_PATTERNS = re.compile(
    r"(?i)\b(CC\s*BY(?:-(?:SA|NC|ND)){0,3}\s*\d[\d.]*|"
    r"Creative\s+Commons|Public\s+Domain|CC0)\b"
)

_NON_OPEN_PATTERNS = re.compile(
    r"(?i)\b(All\s+Rights\s+Reserved|proprietary|copyrighted)\b"
)


def classify_license(license_text: str) -> LicenseInfo:
    """Classify a license string into status + details using rule-based checks."""
    if not license_text or not license_text.strip():
        return LicenseInfo(status="unknown", details="No license information available.")

    text = license_text.strip()

    if _CC_PATTERNS.search(text):
        return LicenseInfo(status="open", details=text)

    if _NON_OPEN_PATTERNS.search(text):
        return LicenseInfo(status="not_open", details=text)

    return LicenseInfo(status="unclear", details=f"License listed as '{text}' but not a recognized open license.")


def _score_licensing_clarity(license_text: str) -> RubricScore:
    """Rule-based: score licensing clarity from the raw license string."""
    info = classify_license(license_text)
    if info.status == "open":
        return RubricScore(score=5.0, reasoning=f"Recognized open license: {license_text}", basis="verified")
    if info.status == "unclear":
        return RubricScore(score=3.0, reasoning=f"License listed but not clearly open: {license_text}", basis="verified")
    if info.status == "not_open":
        return RubricScore(score=1.0, reasoning=f"Non-open license: {license_text}", basis="verified")
    return RubricScore(score=NEUTRAL_SCORE, reasoning="No license information available.", basis="unavailable")


def _score_accessibility(has_info: bool) -> RubricScore:
    """Rule-based: score accessibility from metadata boolean."""
    if has_info:
        return RubricScore(score=4.0, reasoning="Resource indicates accessibility information is available.", basis="verified")
    return RubricScore(score=NEUTRAL_SCORE, reasoning="No accessibility information declared in metadata.", basis="unavailable")


def _score_supplementary(has_materials: bool) -> RubricScore:
    """Rule-based: score supplementary resources from metadata boolean."""
    if has_materials:
        return RubricScore(score=4.0, reasoning="Resource includes supplementary materials.", basis="verified")
    return RubricScore(score=NEUTRAL_SCORE, reasoning="No supplementary materials declared in metadata.", basis="unavailable")


def _score_modularity(resource_type: str) -> RubricScore:
    """Rule-based: infer modularity from resource type."""
    rt = resource_type.lower().strip()
    if rt == "textbook":
        return RubricScore(
            score=4.0,
            reasoning="Textbook format typically supports modular chapter-level adoption.",
            basis="inferred",
        )
    if rt == "syllabus":
        return RubricScore(
            score=3.0,
            reasoning="Syllabus format is course-specific; adaptability depends on institutional context.",
            basis="inferred",
        )
    return RubricScore(score=NEUTRAL_SCORE, reasoning=f"Resource type '{resource_type}' -- modularity unclear.", basis="unavailable")


def _parse_llm_rubric_score(data: Any) -> RubricScore:
    """Parse a rubric score dict from LLM output into a RubricScore with basis='inferred'."""
    if not isinstance(data, dict):
        return RubricScore(score=NEUTRAL_SCORE, reasoning="Insufficient data to evaluate.", basis="unavailable")

    raw_score = data.get("score", NEUTRAL_SCORE)
    try:
        score = float(raw_score)
        score = max(1.0, min(5.0, score))
    except (TypeError, ValueError):
        score = NEUTRAL_SCORE

    reasoning = str(data.get("reasoning", ""))
    return RubricScore(score=score, reasoning=reasoning, basis="inferred")


def build_rubric_evaluation(
    context_resource: Dict,
    llm_recommendation: Dict,
) -> RubricEvaluation:
    """Combine rule-based checks with LLM-provided scores into a full rubric.

    Rule-based categories (override LLM):
      - licensing_clarity
      - accessibility_compliance
      - supplementary_resources
      - modularity_and_adaptability

    LLM-evaluated categories:
      - relevance_and_comprehensiveness
      - interactivity_and_engagement
      - pedagogical_soundness
    """
    llm_rubric = llm_recommendation.get("rubric_evaluation", {})
    if not isinstance(llm_rubric, dict):
        llm_rubric = {}

    return RubricEvaluation(
        relevance_and_comprehensiveness=_parse_llm_rubric_score(
            llm_rubric.get("relevance_and_comprehensiveness")
        ),
        interactivity_and_engagement=_parse_llm_rubric_score(
            llm_rubric.get("interactivity_and_engagement")
        ),
        pedagogical_soundness=_parse_llm_rubric_score(
            llm_rubric.get("pedagogical_soundness")
        ),
        licensing_clarity=_score_licensing_clarity(
            context_resource.get("license", "")
        ),
        accessibility_compliance=_score_accessibility(
            context_resource.get("has_accessibility_info", False)
        ),
        modularity_and_adaptability=_score_modularity(
            context_resource.get("resource_type", "")
        ),
        supplementary_resources=_score_supplementary(
            context_resource.get("has_supplementary_materials", False)
        ),
    )
