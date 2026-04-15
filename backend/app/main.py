import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import chat, health, search
from app.services.chroma_client import get_chroma_client, get_collection
from app.services.embeddings import close_client as close_embeddings_client
from app.services.llm import close_client as close_llm_client
from app.services.lmstudio import close_client as close_lmstudio_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    abs_chroma = os.path.abspath(settings.chroma_path)
    collection = get_collection()
    doc_count = collection.count()
    logger.warning(
        "ChromaDB | path=%s | collection=%s | documents=%d",
        abs_chroma, collection.name, doc_count,
    )
    if doc_count == 0:
        logger.warning(
            "ChromaDB collection is EMPTY. Run: python -m scripts.seed_chroma"
        )
    yield
    await close_llm_client()
    await close_embeddings_client()
    await close_lmstudio_client()


app = FastAPI(title="OER AI Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(search.router)
