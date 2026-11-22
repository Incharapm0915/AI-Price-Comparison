"""GET /api/retailers — which retailers this deployment can search, and
whether it's currently running mock or live collection."""
from fastapi import APIRouter

from app.collectors.collector_factory import SUPPORTED_RETAILERS
from app.config import get_settings

router = APIRouter()


@router.get("")
def list_retailers() -> dict:
    settings = get_settings()
    return {
        "success": True,
        "data": [
            {"retailer": r, "mode": "mock" if settings.mock_mode else "live", "enabled": True}
            for r in SUPPORTED_RETAILERS
        ],
    }
