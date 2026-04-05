import logging
from typing import Any

from fastapi import APIRouter

log = logging.getLogger(__name__)

router = APIRouter(prefix="/destination", tags=["destination"])


@router.post("/mock")
def mock_destination(payload: list[dict[str, Any]]) -> dict[str, Any]:
    """Local mock receiver: logs size and returns 200."""
    log.info("[destination/mock] received %s items", len(payload))
    return {"ok": True, "received": len(payload)}
