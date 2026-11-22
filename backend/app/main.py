"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import get_settings
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the embedding model now, not on the first user request — its
    # first load involves HuggingFace network round-trips that can easily
    # exceed a client's request timeout if paid inline on a real search.
    from app.matching.embeddings import EmbeddingService

    try:
        EmbeddingService.get_instance().model  # noqa: B018 (property access triggers the load)
        logger.info("Embedding model warmed at startup.")
    except Exception:
        logger.exception("Embedding model failed to warm at startup; will retry lazily on first use.")
    yield


app = FastAPI(
    title="AI-Powered Price Comparison API",
    description="Compares the same product across Amazon, Flipkart, and other retailers.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {
        "status": "ok",
        "environment": settings.environment,
        "mock_mode": settings.mock_mode,
    }
