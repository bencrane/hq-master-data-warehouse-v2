"""
Parallel AI Native Endpoints.

FastAPI endpoints for Parallel AI enrichment - writes directly to database.
Only includes NEW endpoints not already in Modal.
"""

import os
import json
import asyncio
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from db import get_pool

router = APIRouter(prefix="/parallel-native", tags=["parallel-native"])

PARALLEL_API_KEY = os.getenv("PARALLEL_API_KEY")
PARALLEL_TASK_API_URL = "https://api.parallel.ai/v1/tasks/runs"


# =============================================================================
# Request Models
# =============================================================================

class HqLocationRequest(BaseModel):
    domain: str
    company_name: str
    company_linkedin_url: Optional[str] = None
    workflow_source: str = "parallel-native/hq-location/ingest/db-direct"


class IndustryRequest(BaseModel):
    domain: str
    company_name: str
    company_linkedin_url: Optional[str] = None
    workflow_source: str = "parallel-native/industry/ingest/db-direct"


class CompetitorsRequest(BaseModel):
    domain: str
    company_name: str
    company_linkedin_url: Optional[str] = None
    workflow_source: str = "parallel-native/competitors/ingest/db-direct"


# =============================================================================
# Helper Function
# =============================================================================

async def call_parallel_ai(input_data: dict, task_spec: dict, timeout_seconds: int = 60) -> dict:
    """
    Submit task to Parallel AI and poll for completion.
    Returns the output content or raises an exception.
    """
    if not PARALLEL_API_KEY:
        raise HTTPException(status_code=500, detail="PARALLEL_API_KEY not configured")

    headers = {
        "x-api-key": PARALLEL_API_KEY,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30) as client:
        # Submit task - input must be JSON string, processor must be "base"
        submit_response = await client.post(
            PARALLEL_TASK_API_URL,
            headers=headers,
            json={
                "input": json.dumps(input_data),
                "processor": "base",
                "task_spec": task_spec
            }
        )

        if submit_response.status_code not in (200, 202):
            raise HTTPException(
                status_code=502,
                detail=f"Parallel API submit failed: {submit_response.status_code} - {submit_response.text}"
            )

        task_result = submit_response.json()
        run_id = task_result.get("run_id")

        if not run_id:
            raise HTTPException(status_code=502, detail="No run_id returned from Parallel API")

        # Poll for completion
        result_url = f"{PARALLEL_TASK_API_URL}/{run_id}"
        max_attempts = timeout_seconds // 2
        poll_interval = 2

        for _ in range(max_attempts):
            await asyncio.sleep(poll_interval)

            poll_response = await client.get(result_url, headers=headers)

            if poll_response.status_code != 200:
                continue

            poll_result = poll_response.json()
            status = poll_result.get("run", {}).get("status") or poll_result.get("status")

            if status == "completed":
                return poll_result.get("output", {}).get("content", {})
            elif status == "failed":
                raise HTTPException(status_code=502, detail="Parallel AI task failed")

        raise HTTPException(status_code=504, detail="Parallel AI task timed out")


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/hq-location/ingest/db-direct")
async def infer_hq_location(request: HqLocationRequest):
    """
    Infer company HQ location using Parallel AI.
    Writes to core.company_parallel_locations.
    """
    input_data = {
        "domain": request.domain,
        "company_name": request.company_name,
    }
    if request.company_linkedin_url:
        input_data["company_linkedin_url"] = request.company_linkedin_url

    task_spec = {
        "output_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "properties": {
                    "hq_city": {
                        "type": "string",
                        "description": "City where company HQ is located"
                    },
                    "hq_state": {
                        "type": "string",
                        "description": "State/province where company HQ is located"
                    },
                    "hq_country": {
                        "type": "string",
                        "description": "Country where company HQ is located"
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"]
                    }
                },
                "required": ["hq_country", "confidence"]
            }
        },
        "input_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "company_name": {"type": "string"},
                    "company_linkedin_url": {"type": "string"}
                }
            }
        }
    }

    output = await call_parallel_ai(input_data, task_spec)

    hq_city = output.get("hq_city")
    hq_state = output.get("hq_state")
    hq_country = output.get("hq_country")
    confidence = output.get("confidence")

    pool = get_pool()
    await pool.execute("""
        INSERT INTO core.company_parallel_locations
            (domain, hq_city, hq_state, hq_country, confidence, source, workflow_source, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
        ON CONFLICT (domain) DO UPDATE SET
            hq_city = EXCLUDED.hq_city,
            hq_state = EXCLUDED.hq_state,
            hq_country = EXCLUDED.hq_country,
            confidence = EXCLUDED.confidence,
            source = EXCLUDED.source,
            workflow_source = EXCLUDED.workflow_source,
            updated_at = NOW()
    """, request.domain, hq_city, hq_state, hq_country, confidence, "parallel-task-api", request.workflow_source)

    return {
        "success": True,
        "domain": request.domain,
        "hq_city": hq_city,
        "hq_state": hq_state,
        "hq_country": hq_country,
        "confidence": confidence
    }


@router.post("/industry/ingest/db-direct")
async def infer_industry(request: IndustryRequest):
    """
    Infer company industry using Parallel AI.
    Writes to core.company_parallel_industries.
    """
    input_data = {
        "domain": request.domain,
        "company_name": request.company_name,
    }
    if request.company_linkedin_url:
        input_data["company_linkedin_url"] = request.company_linkedin_url

    task_spec = {
        "output_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "properties": {
                    "industry": {
                        "type": "string",
                        "description": "Primary industry the company operates in"
                    },
                    "sub_industry": {
                        "type": "string",
                        "description": "More specific sub-industry or vertical"
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"]
                    }
                },
                "required": ["industry", "confidence"]
            }
        },
        "input_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "company_name": {"type": "string"},
                    "company_linkedin_url": {"type": "string"}
                }
            }
        }
    }

    output = await call_parallel_ai(input_data, task_spec)

    industry = output.get("industry")
    sub_industry = output.get("sub_industry")
    confidence = output.get("confidence")

    pool = get_pool()
    await pool.execute("""
        INSERT INTO core.company_parallel_industries
            (domain, industry, sub_industry, confidence, source, workflow_source, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, NOW())
        ON CONFLICT (domain) DO UPDATE SET
            industry = EXCLUDED.industry,
            sub_industry = EXCLUDED.sub_industry,
            confidence = EXCLUDED.confidence,
            source = EXCLUDED.source,
            workflow_source = EXCLUDED.workflow_source,
            updated_at = NOW()
    """, request.domain, industry, sub_industry, confidence, "parallel-task-api", request.workflow_source)

    return {
        "success": True,
        "domain": request.domain,
        "industry": industry,
        "sub_industry": sub_industry,
        "confidence": confidence
    }


@router.post("/competitors/ingest/db-direct")
async def infer_competitors(request: CompetitorsRequest):
    """
    Infer company competitors using Parallel AI.
    Writes to core.company_parallel_competitors.
    """
    input_data = {
        "domain": request.domain,
        "company_name": request.company_name,
    }
    if request.company_linkedin_url:
        input_data["company_linkedin_url"] = request.company_linkedin_url

    task_spec = {
        "output_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "properties": {
                    "competitors": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "domain": {"type": "string"},
                                "reason": {"type": "string"}
                            }
                        },
                        "description": "List of competitor companies"
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"]
                    }
                },
                "required": ["competitors", "confidence"]
            }
        },
        "input_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "company_name": {"type": "string"},
                    "company_linkedin_url": {"type": "string"}
                }
            }
        }
    }

    output = await call_parallel_ai(input_data, task_spec)

    competitors = output.get("competitors", [])
    confidence = output.get("confidence")

    pool = get_pool()

    # Store as JSONB
    competitors_json = json.dumps(competitors)

    await pool.execute("""
        INSERT INTO core.company_parallel_competitors
            (domain, competitors, confidence, source, workflow_source, updated_at)
        VALUES ($1, $2::jsonb, $3, $4, $5, NOW())
        ON CONFLICT (domain) DO UPDATE SET
            competitors = EXCLUDED.competitors,
            confidence = EXCLUDED.confidence,
            source = EXCLUDED.source,
            workflow_source = EXCLUDED.workflow_source,
            updated_at = NOW()
    """, request.domain, competitors_json, confidence, "parallel-task-api", request.workflow_source)

    return {
        "success": True,
        "domain": request.domain,
        "competitors": competitors,
        "confidence": confidence
    }
