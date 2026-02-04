"""
Read Router - API wrappers for reading data via Modal serverless functions.
This router provides consistent API endpoints for reading/checking data presence.

Naming convention:
    /read/{entity}/{source}/{action}
"""

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/read", tags=["read"])

# Modal base URL
MODAL_BASE_URL = "https://bencrane--hq-master-data-ingest"

# =============================================================================
# Request/Response Models
# =============================================================================

class ExistenceCheckRequest(BaseModel):
    domain: str
    schema_name: str
    table_name: str

class ExistenceCheckResponse(BaseModel):
    success: bool
    exists: bool
    domain: str
    schema_name: str
    table_name: str
    error: Optional[str] = None

# =============================================================================
# Endpoints
# =============================================================================

@router.post(
    "/companies/db/check-existence",
    response_model=ExistenceCheckResponse,
    summary="Check if a company exists in a specific database table",
    description="Wrapper for Modal function: read_db_check_existence"
)
async def read_db_check_existence(request: ExistenceCheckRequest) -> ExistenceCheckResponse:
    """
    Check if a company domain exists in a specific schema and table.
    
    Modal function: read_db_check_existence
    Modal URL: https://bencrane--hq-master-data-ingest-read-db-check-existence.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-read-db-check-existence.modal.run"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return ExistenceCheckResponse(**response.json())
        except httpx.HTTPStatusError as e:
            # Pass through error details from Modal if available
            try:
                error_detail = e.response.json()
            except:
                error_detail = e.response.text
                
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {error_detail}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )
