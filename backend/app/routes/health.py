from fastapi import APIRouter

from .. import deps
from ..config import get_settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "demo_mode": get_settings().demo_mode}


@router.get("/usage")
async def usage():
    return await deps.get_fortyguard_client().fetch_api_key_usage()
