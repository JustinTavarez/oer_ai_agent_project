from fastapi import APIRouter

from app.models.schemas import HealthResponse
from app.services.llm import check_lm_studio

router = APIRouter()


@router.get("/")
async def read_root():
    return {"message": "Backend is running"}


@router.get("/health", response_model=HealthResponse)
async def health():
    lm_ok = await check_lm_studio()
    return HealthResponse(
        status="ok",
        lm_studio="connected" if lm_ok else "disconnected",
    )
