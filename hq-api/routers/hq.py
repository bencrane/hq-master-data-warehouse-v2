from fastapi import APIRouter
from db import get_pool

router = APIRouter(prefix="/api/hq", tags=["hq"])


@router.post("/clients")
async def get_clients(payload: dict = {}):
    """
    Get all HQ clients for dropdown selection.

    Returns all clients with their details.
    """
    pool = get_pool()

    rows = await pool.fetch("""
        SELECT id, name, domain, status, service, created_at, updated_at
        FROM hq.clients
        ORDER BY name
    """)

    return {
        "data": [dict(r) for r in rows],
        "meta": {"total": len(rows)}
    }
