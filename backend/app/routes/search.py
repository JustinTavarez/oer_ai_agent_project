import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter

from app.config import settings
from app.models.schemas import (
    DebugInfo,
    EvaluatedResource,
    EvaluatedSearchResponse,
    LicenseInfo,
    RelevanceInfo,
    SearchRequest,
)
from app.services.embeddings import EmbeddingError
from app.services.logger import log_search_request
from app.services.lmstudio import build_context_pack, generate_evaluated_response
from app.services.retrieval import search
from app.services.rubric import (
    build_rubric_evaluation,
    classify_license,
    compute_weighted_score,
    generate_integration_tips,
    trim_to_sentence,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Response-level cache (sits above retrieval + LLM)
# ---------------------------------------------------------------------------
_search_cache: Dict[tuple, tuple] = {}
_SEARCH_CACHE_TTL_S = 600
_SEARCH_CACHE_MAX = 64


def clear_search_cache() -> None:
    """Clear the response-level cache (used in tests)."""
    _search_cache.clear()


def _search_cache_key(req: SearchRequest) -> tuple:
    return (
        req.query.strip().lower(),
        (req.course_code or "").strip().lower(),
        (req.source or "").strip().lower(),
        req.top_k,
        req.grounded,
        settings.cache_version,
    )


def _search_cache_get(key: tuple) -> Optional[EvaluatedSearchResponse]:
    entry = _search_cache.get(key)
    if entry is None:
        return None
    result, expiry = entry
    if time.monotonic() > expiry:
        _search_cache.pop(key, None)
        return None
    return result


def _search_cache_put(key: tuple, result: EvaluatedSearchResponse) -> None:
    if len(_search_cache) >= _SEARCH_CACHE_MAX:
        now = time.monotonic()
        expired = [k for k, (_, exp) in _search_cache.items() if now > exp]
        for k in expired:
            _search_cache.pop(k, None)
        if len(_search_cache) >= _SEARCH_CACHE_MAX:
            _search_cache.pop(next(iter(_search_cache)), None)
    _search_cache[key] = (result, time.monotonic() + _SEARCH_CACHE_TTL_S)


# ---------------------------------------------------------------------------
# Resource builders
# ---------------------------------------------------------------------------

def _ensure_description(ctx: dict, llm_desc: str = "") -> str:
    """Guarantee a non-empty description."""
    if llm_desc and llm_desc.strip():
        return llm_desc.strip()
    content = ctx.get("content", "")
    if content:
        return trim_to_sentence(content, 200)
    return ctx.get("title", "") or "No description available."


def _ensure_tips(tips: list, ctx: dict) -> list[str]:
    """Guarantee at least one integration tip."""
    clean = [str(t) for t in tips if t]
    if clean:
        return clean
    return generate_integration_tips(
        ctx.get("resource_type", ""), ctx.get("course_code", "")
    )


def _ensure_license_details(info: LicenseInfo) -> LicenseInfo:
    """Guarantee license.details is never empty."""
    if info.details and info.details.strip():
        return info
    return LicenseInfo(status=info.status, details="No license information available.")


def _build_fallback_resource(ctx: dict) -> EvaluatedResource:
    """Build an EvaluatedResource from a context-pack entry without LLM data."""
    license_info = _ensure_license_details(classify_license(ctx.get("license", "")))
    return EvaluatedResource(
        resource_id=ctx["resource_id"],
        title=ctx.get("title", ""),
        description=_ensure_description(ctx),
        source=ctx.get("source", ""),
        url=ctx.get("url", ""),
        course_code=ctx.get("course_code", ""),
        relevance=RelevanceInfo(
            score=ctx.get("score", 0.0),
            reasoning="Matched based on content similarity to your query.",
        ),
        license=license_info,
        integration_tips=generate_integration_tips(
            ctx.get("resource_type", ""), ctx.get("course_code", ""),
        ),
        rubric_evaluation=build_rubric_evaluation(ctx, {}),
    )


def _build_evaluated_resource(ctx: dict, llm_rec: dict) -> EvaluatedResource:
    """Build an EvaluatedResource by merging context metadata with LLM evaluation."""
    license_info = _ensure_license_details(classify_license(ctx.get("license", "")))
    llm_license = llm_rec.get("license", {})
    if isinstance(llm_license, dict) and llm_license.get("details"):
        license_info = LicenseInfo(
            status=license_info.status,
            details=llm_license.get("details", license_info.details),
        )

    llm_relevance = llm_rec.get("relevance", {})
    if isinstance(llm_relevance, dict):
        rel_score = llm_relevance.get("score", ctx.get("score", 0.0))
        try:
            rel_score = max(0.0, min(1.0, float(rel_score)))
        except (TypeError, ValueError):
            rel_score = ctx.get("score", 0.0)
        relevance = RelevanceInfo(
            score=rel_score,
            reasoning=str(llm_relevance.get("reasoning", "")),
        )
    else:
        relevance = RelevanceInfo(
            score=ctx.get("score", 0.0),
            reasoning="Matched based on content similarity to your query.",
        )

    tips = llm_rec.get("integration_tips", [])
    if not isinstance(tips, list):
        tips = [str(tips)] if tips else []

    return EvaluatedResource(
        resource_id=ctx["resource_id"],
        title=ctx.get("title", ""),
        description=_ensure_description(ctx, str(llm_rec.get("description", ""))),
        source=ctx.get("source", ""),
        url=ctx.get("url", ""),
        course_code=ctx.get("course_code", ""),
        relevance=relevance,
        license=license_info,
        integration_tips=_ensure_tips(tips, ctx),
        rubric_evaluation=build_rubric_evaluation(ctx, llm_rec),
    )


def _sort_results(
    evaluated: list[EvaluatedResource], llm_succeeded: bool,
) -> list[EvaluatedResource]:
    """Sort results: weighted rubric score in full-eval mode, relevance in fallback."""
    if llm_succeeded:
        return sorted(
            evaluated,
            key=lambda r: compute_weighted_score(r.rubric_evaluation),
            reverse=True,
        )
    return sorted(evaluated, key=lambda r: r.relevance.score, reverse=True)


# ---------------------------------------------------------------------------
# Main search endpoint
# ---------------------------------------------------------------------------

def _make_response(
    query: str,
    timestamp: str,
    log_id: str,
    summary: str = "",
    results: Optional[list[EvaluatedResource]] = None,
    warnings: Optional[list[str]] = None,
    errors: Optional[list[str]] = None,
    debug_info: Optional[DebugInfo] = None,
) -> EvaluatedSearchResponse:
    """Build a consistent EvaluatedSearchResponse."""
    return EvaluatedSearchResponse(
        query=query,
        timestamp=timestamp,
        log_id=log_id,
        summary=summary,
        results=results or [],
        warnings=warnings or [],
        errors=errors or [],
        debug=debug_info,
    )


@router.post("/search", response_model=EvaluatedSearchResponse)
async def search_resources(request: SearchRequest):
    log_id = str(uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    warnings: list[str] = []
    errors: list[str] = []
    t_start = time.monotonic()
    retrieval_duration_ms = 0
    llm_duration_ms = 0
    cache_hit = False
    evaluation_mode = "rule_based"
    llm_success = False
    fallback_used = False
    response_status = "success"

    try:
        logger.info("Search started | log_id=%s query=%r top_k=%d", log_id, request.query, request.top_k)

        # ---- Response-level cache check ----
        cache_key = _search_cache_key(request)
        cached = _search_cache_get(cache_key)
        if cached is not None:
            cache_hit = True
            total_ms = int((time.monotonic() - t_start) * 1000)
            logger.info("Response cache hit | log_id=%s total_ms=%d", log_id, total_ms)
            log_search_request(
                query=request.query, course_code=request.course_code,
                source=request.source, top_k=request.top_k,
                result_count=len(cached.results), grounded=request.grounded,
                log_id=log_id, retrieved_doc_count=len(cached.results),
                final_result_count=len(cached.results),
                cache_hit=True, total_duration_ms=total_ms,
                evaluation_mode="cached", response_status="success",
            )
            if request.debug:
                cached = cached.model_copy(update={
                    "debug": DebugInfo(
                        cache_hit=True, total_duration_ms=total_ms,
                        evaluation_mode="cached",
                        cache_version=settings.cache_version,
                    ),
                })
            return cached

        # ---- Retrieval ----
        t_retrieval = time.monotonic()
        raw_results = await search(
            query=request.query,
            top_k=request.top_k,
            course_code=request.course_code,
            source=request.source,
        )
        retrieval_duration_ms = int((time.monotonic() - t_retrieval) * 1000)
        retrieved_doc_count = len(raw_results)
        logger.info("Retrieval returned %d results in %dms", retrieved_doc_count, retrieval_duration_ms)

        if not raw_results:
            warnings.append("No matching resources found for the given query and filters.")
            total_ms = int((time.monotonic() - t_start) * 1000)
            log_search_request(
                query=request.query, course_code=request.course_code,
                source=request.source, top_k=request.top_k,
                result_count=0, grounded=request.grounded,
                log_id=log_id, retrieved_doc_count=0, final_result_count=0,
                warnings=warnings, errors=errors,
                retrieval_duration_ms=retrieval_duration_ms,
                total_duration_ms=total_ms, evaluation_mode="rule_based",
                response_status="success",
            )
            resp = _make_response(
                request.query, timestamp, log_id, warnings=warnings, errors=errors,
                debug_info=DebugInfo(
                    retrieval_duration_ms=retrieval_duration_ms,
                    total_duration_ms=total_ms,
                    evaluation_mode="rule_based",
                    cache_version=settings.cache_version,
                ) if request.debug else None,
            )
            return resp

        context_pack = build_context_pack(raw_results, course_code=request.course_code)

        # ---- Non-grounded (rule-based only) ----
        if not request.grounded:
            evaluation_mode = "rule_based"
            fallback_used = True
            evaluated = [_build_fallback_resource(ctx) for ctx in context_pack]
            evaluated = _sort_results(evaluated, llm_succeeded=False)
            total_ms = int((time.monotonic() - t_start) * 1000)

            log_search_request(
                query=request.query, course_code=request.course_code,
                source=request.source, top_k=request.top_k,
                result_count=len(evaluated), grounded=False,
                log_id=log_id, retrieved_doc_count=retrieved_doc_count,
                final_result_count=len(evaluated), warnings=warnings, errors=errors,
                retrieval_duration_ms=retrieval_duration_ms,
                total_duration_ms=total_ms, evaluation_mode=evaluation_mode,
                response_status="success", fallback_used=True,
            )
            resp = _make_response(
                request.query, timestamp, log_id,
                summary="Here are the most relevant open educational resources for your query.",
                results=evaluated, warnings=warnings, errors=errors,
                debug_info=DebugInfo(
                    retrieval_duration_ms=retrieval_duration_ms,
                    total_duration_ms=total_ms,
                    evaluation_mode=evaluation_mode,
                    fallback_used=True,
                    cache_version=settings.cache_version,
                ) if request.debug else None,
            )
            _search_cache_put(cache_key, resp.model_copy(update={"debug": None}))
            return resp

        # ---- Grounded (LLM evaluation) ----
        llm_resp = await generate_evaluated_response(
            query=request.query,
            raw_results=raw_results,
            course_code=request.course_code,
        )
        llm_duration_ms = llm_resp.get("llm_duration_ms", 0)
        llm_success = llm_resp.get("llm_success", False)
        fallback_used = llm_resp.get("fallback_used", False)

        if fallback_used:
            evaluation_mode = "rule_based"
            if llm_resp.get("parse_failures", 0) > 0:
                logger.warning("LLM parse failures for log_id=%s", log_id)
            evaluated = [_build_fallback_resource(ctx) for ctx in context_pack]
            evaluated = _sort_results(evaluated, llm_succeeded=False)
        else:
            evaluation_mode = "full"
            llm_recs = llm_resp.get("recommendations", [])
            ctx_by_id = {c["resource_id"]: c for c in context_pack}
            evaluated = []

            for rec in llm_recs:
                rid = rec.get("resource_id", "")
                if not rid:
                    logger.warning("LLM recommendation missing resource_id, skipping.")
                    continue
                ctx = ctx_by_id.get(rid)
                if ctx:
                    evaluated.append(_build_evaluated_resource(ctx, rec))
                else:
                    logger.warning("LLM recommended unknown resource_id=%r, skipping.", rid)

            covered_ids = {r.resource_id for r in evaluated}
            for ctx in context_pack:
                if ctx["resource_id"] not in covered_ids:
                    evaluated.append(_build_fallback_resource(ctx))

            if evaluated and not all(r.resource_id in covered_ids for r in evaluated):
                evaluation_mode = "partial"

            evaluated = _sort_results(evaluated, llm_succeeded=True)

        total_ms = int((time.monotonic() - t_start) * 1000)

        log_search_request(
            query=request.query, course_code=request.course_code,
            source=request.source, top_k=request.top_k,
            result_count=len(evaluated), grounded=True,
            log_id=log_id, retrieved_doc_count=retrieved_doc_count,
            final_result_count=len(evaluated), warnings=warnings, errors=errors,
            llm_success=llm_success, llm_duration_ms=llm_duration_ms,
            llm_parse_failures=llm_resp.get("parse_failures", 0),
            fallback_used=fallback_used,
            retrieval_duration_ms=retrieval_duration_ms,
            total_duration_ms=total_ms, evaluation_mode=evaluation_mode,
            response_status="success",
        )

        summary = llm_resp.get("summary", "")
        if not summary or not summary.strip():
            summary = "Resources were found for your query. See the results below."

        resp = _make_response(
            request.query, timestamp, log_id,
            summary=summary, results=evaluated,
            warnings=warnings, errors=errors,
            debug_info=DebugInfo(
                llm_used=True, fallback_used=fallback_used,
                evaluation_mode=evaluation_mode,
                retrieval_duration_ms=retrieval_duration_ms,
                llm_duration_ms=llm_duration_ms,
                total_duration_ms=total_ms,
                cache_version=settings.cache_version,
            ) if request.debug else None,
        )
        _search_cache_put(cache_key, resp.model_copy(update={"debug": None}))
        return resp

    except EmbeddingError:
        response_status = "error"
        total_ms = int((time.monotonic() - t_start) * 1000)
        logger.error("Embedding service unavailable | log_id=%s", log_id)
        errors.append("The search service is temporarily unavailable. Please try again shortly.")
        log_search_request(
            query=request.query, course_code=request.course_code,
            source=request.source, top_k=request.top_k,
            result_count=0, grounded=request.grounded,
            message="Embedding service unavailable",
            log_id=log_id, retrieved_doc_count=0, final_result_count=0,
            warnings=warnings, errors=errors,
            retrieval_duration_ms=retrieval_duration_ms,
            total_duration_ms=total_ms,
            response_status="error",
        )
        return _make_response(
            request.query, timestamp, log_id,
            errors=errors, warnings=warnings,
            debug_info=DebugInfo(
                total_duration_ms=total_ms, evaluation_mode="error",
                cache_version=settings.cache_version,
            ) if request.debug else None,
        )

    except Exception as exc:
        response_status = "error"
        total_ms = int((time.monotonic() - t_start) * 1000)
        logger.exception("Unexpected error in search route")
        errors.append("An unexpected error occurred. Please try again.")
        log_search_request(
            query=request.query, course_code=request.course_code,
            source=request.source, top_k=request.top_k,
            result_count=0, grounded=request.grounded,
            message=f"Internal error: {exc}",
            log_id=log_id, retrieved_doc_count=0, final_result_count=0,
            warnings=warnings, errors=errors,
            retrieval_duration_ms=retrieval_duration_ms,
            total_duration_ms=total_ms,
            response_status="error",
        )
        return _make_response(
            request.query, timestamp, log_id,
            errors=errors, warnings=warnings,
            debug_info=DebugInfo(
                total_duration_ms=total_ms, evaluation_mode="error",
                cache_version=settings.cache_version,
            ) if request.debug else None,
        )
