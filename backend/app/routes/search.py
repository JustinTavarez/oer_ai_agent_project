import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
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
from app.services.rubric import build_rubric_evaluation, classify_license

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_fallback_resource(ctx: dict) -> EvaluatedResource:
    """Build an EvaluatedResource from a context-pack entry without LLM data."""
    license_info = classify_license(ctx.get("license", ""))
    return EvaluatedResource(
        resource_id=ctx["resource_id"],
        title=ctx.get("title", ""),
        description=ctx.get("content", "")[:300],
        source=ctx.get("source", ""),
        url=ctx.get("url", ""),
        course_code=ctx.get("course_code", ""),
        relevance=RelevanceInfo(score=ctx.get("score", 0.0), reasoning="Based on vector similarity."),
        license=license_info,
        integration_tips=[],
        rubric_evaluation=build_rubric_evaluation(ctx, {}),
        warnings=["Showing retrieval-based results."],
    )


def _build_evaluated_resource(ctx: dict, llm_rec: dict) -> EvaluatedResource:
    """Build an EvaluatedResource by merging context metadata with LLM evaluation."""
    license_info = classify_license(ctx.get("license", ""))
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
        relevance = RelevanceInfo(score=ctx.get("score", 0.0), reasoning="Based on vector similarity.")

    tips = llm_rec.get("integration_tips", [])
    if not isinstance(tips, list):
        tips = [str(tips)] if tips else []

    warnings = llm_rec.get("warnings", [])
    if not isinstance(warnings, list):
        warnings = [str(warnings)] if warnings else []

    return EvaluatedResource(
        resource_id=ctx["resource_id"],
        title=ctx.get("title", ""),
        description=str(llm_rec.get("description", ctx.get("content", "")[:300])),
        source=ctx.get("source", ""),
        url=ctx.get("url", ""),
        course_code=ctx.get("course_code", ""),
        relevance=relevance,
        license=license_info,
        integration_tips=[str(t) for t in tips],
        rubric_evaluation=build_rubric_evaluation(ctx, llm_rec),
        warnings=[str(w) for w in warnings],
    )


@router.post("/search", response_model=EvaluatedSearchResponse)
async def search_resources(request: SearchRequest):
    log_id = str(uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    warnings: list[str] = []
    errors: list[str] = []

    try:
        logger.info("Search started | log_id=%s query=%r top_k=%d", log_id, request.query, request.top_k)

        raw_results = await search(
            query=request.query,
            top_k=request.top_k,
            course_code=request.course_code,
            source=request.source,
        )
        retrieved_doc_count = len(raw_results)
        logger.info("Retrieval returned %d normalised results", retrieved_doc_count)

        if not raw_results:
            warnings.append("No matching resources found for the given query and filters.")
            log_search_request(
                query=request.query, course_code=request.course_code,
                source=request.source, top_k=request.top_k,
                result_count=0, grounded=request.grounded,
                log_id=log_id, retrieved_doc_count=0, final_result_count=0,
                warnings=warnings, errors=errors,
            )
            return EvaluatedSearchResponse(
                query=request.query, timestamp=timestamp, log_id=log_id,
                warnings=warnings, errors=errors,
            )

        context_pack = build_context_pack(raw_results, course_code=request.course_code)

        if not request.grounded:
            evaluated = [_build_fallback_resource(ctx) for ctx in context_pack]
            log_search_request(
                query=request.query, course_code=request.course_code,
                source=request.source, top_k=request.top_k,
                result_count=len(evaluated), grounded=False,
                log_id=log_id, retrieved_doc_count=retrieved_doc_count,
                final_result_count=len(evaluated), warnings=warnings, errors=errors,
            )
            return EvaluatedSearchResponse(
                query=request.query, timestamp=timestamp, log_id=log_id,
                summary="Results returned without LLM evaluation.",
                results=evaluated, warnings=warnings, errors=errors,
            )

        llm_resp = await generate_evaluated_response(
            query=request.query,
            raw_results=raw_results,
            course_code=request.course_code,
        )
        warnings.extend(llm_resp.get("warnings", []))

        if llm_resp.get("fallback_used"):
            evaluated = [_build_fallback_resource(ctx) for ctx in context_pack]
            if llm_resp.get("parse_failures", 0) > 0:
                errors.append("Could not process full evaluation for these results.")
        else:
            llm_recs = llm_resp.get("recommendations", [])
            ctx_by_id = {c["resource_id"]: c for c in context_pack}
            evaluated = []

            for rec in llm_recs:
                rid = rec.get("resource_id", "")
                ctx = ctx_by_id.get(rid)
                if ctx:
                    evaluated.append(_build_evaluated_resource(ctx, rec))
                else:
                    logger.warning("LLM recommended unknown resource_id=%r, skipping.", rid)

            covered_ids = {r.resource_id for r in evaluated}
            for ctx in context_pack:
                if ctx["resource_id"] not in covered_ids:
                    evaluated.append(_build_fallback_resource(ctx))
                    warnings.append(f"Resource '{ctx['title']}' was not evaluated by the LLM.")

        log_search_request(
            query=request.query, course_code=request.course_code,
            source=request.source, top_k=request.top_k,
            result_count=len(evaluated), grounded=True,
            log_id=log_id, retrieved_doc_count=retrieved_doc_count,
            final_result_count=len(evaluated), warnings=warnings, errors=errors,
            llm_success=llm_resp.get("llm_success", False),
            llm_duration_ms=llm_resp.get("llm_duration_ms", 0),
            llm_parse_failures=llm_resp.get("parse_failures", 0),
            fallback_used=llm_resp.get("fallback_used", False),
        )

        summary = llm_resp.get("summary", "")
        if not summary or not summary.strip():
            summary = "Resources were found for your query. See the results below."

        return EvaluatedSearchResponse(
            query=request.query, timestamp=timestamp, log_id=log_id,
            summary=summary,
            results=evaluated, warnings=warnings, errors=errors,
        )

    except EmbeddingError:
        errors.append("Embedding service unavailable.")
        log_search_request(
            query=request.query, course_code=request.course_code,
            source=request.source, top_k=request.top_k,
            result_count=0, grounded=request.grounded,
            message="Embedding service unavailable",
            log_id=log_id, retrieved_doc_count=0, final_result_count=0,
            warnings=warnings, errors=errors,
        )
        raise HTTPException(
            status_code=503,
            detail="Embedding service unavailable. Please ensure LM Studio is running.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error in search route")
        errors.append(f"Internal error: {exc}")
        log_search_request(
            query=request.query, course_code=request.course_code,
            source=request.source, top_k=request.top_k,
            result_count=0, grounded=request.grounded,
            message=f"Internal error: {exc}",
            log_id=log_id, retrieved_doc_count=0, final_result_count=0,
            warnings=warnings, errors=errors,
        )
        raise HTTPException(status_code=500, detail="Internal search error.")
