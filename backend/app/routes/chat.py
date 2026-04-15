import logging

from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse
from app.services.llm import get_completion

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        result = await get_completion(
            prompt=request.prompt,
            course=request.course,
            source_filter=request.source_filter,
        )
        return ChatResponse(response=result["response"])
    except Exception as exc:
        logger.exception("Unexpected error in chat route")
        return ChatResponse(
            response="Something went wrong while processing your request. Please try again."
        )
