from fastapi import APIRouter, HTTPException

from app.models.schemas import ChatRequest, ChatResponse
from app.services.llm import get_completion

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
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {e}")
