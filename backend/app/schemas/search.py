"""Request/response shapes for POST /api/search."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.product import SearchResultGroup


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    retailers: list[str] | None = None
    max_results_per_retailer: int | None = None


class SearchResponse(BaseModel):
    query: str
    groups: list[SearchResultGroup]
    retailers_searched: list[str]
    retailers_failed: list[str]
