"""Aggregates all versioned API routers into a single `api_router`."""
from fastapi import APIRouter

from app.api import alerts, comparison, prices, products, recommendations, retailers, reviews, search

api_router = APIRouter()
api_router.include_router(retailers.router, prefix="/retailers", tags=["retailers"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(comparison.router, prefix="/products", tags=["comparison"])
api_router.include_router(reviews.router, prefix="/products", tags=["reviews"])
api_router.include_router(prices.router, prefix="/products", tags=["prices"])
api_router.include_router(recommendations.router, prefix="/products", tags=["recommendations"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
