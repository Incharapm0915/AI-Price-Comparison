"""Sentence-transformer embeddings for Stage 4 (semantic) matching.

The model is loaded lazily on first use — importing this module (or even
constructing `EmbeddingService`) must stay cheap so the rest of the app
doesn't pay torch's import/load cost just to boot.
"""
from __future__ import annotations

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


def build_embedding_text(
    brand: str | None,
    model: str | None,
    canonical_name: str | None,
    specifications: dict | None,
    max_spec_fields: int = 8,
) -> str:
    """Combines brand + model + canonical name + key specs into one string
    to embed — per the brief's Stage 4 design."""
    parts = [p for p in [brand, model, canonical_name] if p]
    if specifications:
        spec_bits = [f"{k}: {v}" for k, v in list(specifications.items())[:max_spec_fields]]
        if spec_bits:
            parts.append(", ".join(spec_bits))
    return " | ".join(parts) if parts else ""


class EmbeddingService:
    """Lazy-loaded singleton around a sentence-transformers model."""

    _instance: "EmbeddingService | None" = None

    def __init__(self, model_name: str | None = None) -> None:
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # deferred: heavy import

            logger.info("Loading embedding model %s (first call only)...", self.model_name)
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, text: str) -> list[float]:
        if not text or not text.strip():
            return []
        vector = self.model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    def encode_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # sentence-transformers happily encodes empty strings (just an
        # uninformative vector); the caller only skips embedding-based
        # comparison entirely when there's no text at all to work with.
        vectors = self.model.encode(list(texts), normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    @classmethod
    def get_instance(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
