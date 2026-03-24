import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.models.schemas import (
    GroundedResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchResultMetadata,
)
from app.services.embeddings import EmbeddingError
from app.services.logger import log_search_request
from app.services.lmstudio import generate_grounded_response
from app.services.retrieval import search

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search_resources(request: SearchRequest):
    message = ""
    results: List[SearchResult] = []
    grounded: Optional[GroundedResponse] = None
    route_skipped = 0

    try:
        logger.info("Search started | query=%r top_k=%d", request.query, request.top_k)

        raw_results = await search(
            query=request.query,
            top_k=request.top_k,
            course_code=request.course_code,
            source=request.source,
        )

        logger.info("Retrieval returned %d normalised results", len(raw_results))

        for idx, r in enumerate(raw_results):
            try:
                results.append(
                    SearchResult(
                        id=r["id"],
                        content=r["content"],
                        title=r["title"],
                        source=r["source"],
                        course_code=r["course_code"],
                        license=r["license"],
                        url=r["url"],
                        chunk_index=r["chunk_index"],
                        score=r["score"],
                        metadata=SearchResultMetadata(**r.get("metadata", {})),
                    )
                )
            except (ValidationError, KeyError, TypeError) as exc:
                route_skipped += 1
                logger.warning(
                    "Skipped result %d during model validation: %s", idx, exc,
                )

        if route_skipped:
            logger.warning(
                "Route-level validation skipped %d results", route_skipped,
            )

        if not results:
            message = "No matching resources found for the given query and filters."
        elif request.grounded:
            try:
                llm_result = await generate_grounded_response(
                    query=request.query,
                    chunks=raw_results,
                )
                grounded = GroundedResponse(
                    summary=llm_result.get("summary", ""),
                    recommendations=llm_result.get("recommendations", []),
                )
            except Exception as exc:
                logger.warning("Grounded response failed: %s", exc)
                message = (
                    "Retrieved results successfully, but LLM grounding failed. "
                    "Raw results are still available."
                )

        logger.info("Returning %d valid results", len(results))

    except EmbeddingError:
        log_search_request(
            query=request.query,
            course_code=request.course_code,
            source=request.source,
            top_k=request.top_k,
            result_count=0,
            grounded=request.grounded,
            message="Embedding service unavailable",
        )
        raise HTTPException(
            status_code=503,
            detail="Embedding service unavailable. Please ensure LM Studio is running.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        log_search_request(
            query=request.query,
            course_code=request.course_code,
            source=request.source,
            top_k=request.top_k,
            result_count=0,
            grounded=request.grounded,
            message=f"Internal error: {exc}",
        )
        raise HTTPException(status_code=500, detail="Internal search error.")

    log_search_request(
        query=request.query,
        course_code=request.course_code,
        source=request.source,
        top_k=request.top_k,
        result_count=len(results),
        grounded=request.grounded,
        message=message,
        skipped_hits=route_skipped,
    )

    return SearchResponse(
        results=results,
        grounded_response=grounded,
        message=message,
    )
