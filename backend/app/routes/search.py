import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException

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

    try:
        raw_results = await search(
            query=request.query,
            top_k=request.top_k,
            course_code=request.course_code,
            source=request.source,
        )

        results = [
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
            for r in raw_results
        ]

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

    except EmbeddingError:
        message = (
            "Embedding service unavailable. "
            "Please ensure LM Studio is running."
        )
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
    )

    return SearchResponse(
        results=results,
        grounded_response=grounded,
        message=message,
    )
