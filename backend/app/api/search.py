"""POST /api/search — collect, match, and persist results for a query."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.search import SearchRequest, SearchResponse
from app.services.search_service import run_search

router = APIRouter()


@router.post("", response_model=SearchResponse)
async def search(payload: SearchRequest, db: Session = Depends(get_db)) -> SearchResponse:
    return await run_search(
        db,
        query=payload.query,
        retailers=payload.retailers,
        max_results_per_retailer=payload.max_results_per_retailer,
    )
