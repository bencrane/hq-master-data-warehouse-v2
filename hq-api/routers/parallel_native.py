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


class PersonContactRequest(BaseModel):
    full_name: str
    company: str
    company_domain: Optional[str] = None


class CaseStudyExtractRequest(BaseModel):
    case_study_url: str
    origin_company_domain: Optional[str] = None


# =============================================================================
# Helper Function
# =============================================================================

async def call_parallel_ai(input_data: dict, task_spec: dict, timeout_seconds: int = 60, processor: str = "base") -> dict:
    """
    Submit task to Parallel AI and poll for completion.
    Returns the output content or raises an exception.

    processor options: "lite", "base", "pro"
    """
    if not PARALLEL_API_KEY:
        raise HTTPException(status_code=500, detail="PARALLEL_API_KEY not configured")

    headers = {
        "x-api-key": PARALLEL_API_KEY,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30) as client:
        # Submit task - input must be JSON string
        submit_response = await client.post(
            PARALLEL_TASK_API_URL,
            headers=headers,
            json={
                "input": json.dumps(input_data),
                "processor": processor,
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


async def call_parallel_ai_v2(input_data, task_spec: dict, timeout_seconds: int = 60, processor: str = "base") -> dict:
    """
    Submit task to Parallel AI.
    V2: Input is passed directly (string or dict), not json.dumps().
    """
    if not PARALLEL_API_KEY:
        raise HTTPException(status_code=500, detail="PARALLEL_API_KEY not configured")

    headers = {
        "x-api-key": PARALLEL_API_KEY,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30) as client:
        submit_response = await client.post(
            PARALLEL_TASK_API_URL,
            headers=headers,
            json={
                "input": input_data,
                "processor": processor,
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


@router.post("/person-contact/enrich")
async def enrich_person_contact(request: PersonContactRequest):
    """
    Find contact info for a person using Parallel AI.
    Returns email, LinkedIn URL, and company website.
    """
    input_data = {
        "full_name": request.full_name,
        "company": request.company,
    }
    if request.company_domain:
        input_data["company_website"] = request.company_domain

    task_spec = {
        "input_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "properties": {
                    "full_name": {
                        "type": "string",
                        "description": "Full name of the person"
                    },
                    "company": {
                        "type": "string",
                        "description": "Company where the person works"
                    },
                    "company_website": {
                        "type": "string",
                        "description": "Company website URL"
                    }
                }
            }
        },
        "output_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Work email address"
                    },
                    "linkedin_url": {
                        "type": "string",
                        "description": "LinkedIn profile URL"
                    },
                    "company_website": {
                        "type": "string",
                        "description": "Official website of the company"
                    }
                },
                "required": ["email", "linkedin_url"]
            }
        }
    }

    output = await call_parallel_ai(input_data, task_spec)

    return {
        "success": True,
        "full_name": request.full_name,
        "company": request.company,
        "email": output.get("email"),
        "linkedin_url": output.get("linkedin_url"),
        "company_website": output.get("company_website")
    }


@router.post("/case-study/extract")
async def extract_case_study(request: CaseStudyExtractRequest):
    """
    Extract structured details from a case study URL using Parallel AI.
    Returns featured company name, domain, and quotes/testimonials.
    """
    input_data = {
        "case_study_url": request.case_study_url
    }

    task_spec = {
        "input_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "properties": {
                    "case_study_url": {
                        "type": "string",
                        "description": "The URL of the case study to extract details from."
                    }
                },
                "required": ["case_study_url"]
            }
        },
        "output_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "featured_company_name": {
                        "type": "string",
                        "description": "The full name of the company that is featured as a customer in the case study. If the company name is not explicitly stated, return null."
                    },
                    "featured_company_domain": {
                        "type": "string",
                        "description": "The primary website domain of the company featured as a customer in the case study (e.g., 'example.com'). If the domain is not explicitly stated or cannot be reliably inferred, return null."
                    },
                    "quotes_and_testimonials": {
                        "type": "array",
                        "description": "A list of all quotes or testimonials from the case study, each including the quote text, the full name of the person quoted, and their job title.",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "quote_text": {
                                    "type": "string",
                                    "description": "The full text of the quote or testimonial, highlighting the customer's positive experience or the value received."
                                },
                                "person_quoted_full_name": {
                                    "type": "string",
                                    "description": "The full name of the individual who provided this quote or testimonial. If no person is identified, return null."
                                },
                                "person_quoted_job_title": {
                                    "type": "string",
                                    "description": "The job title of the individual who provided this quote or testimonial. If the job title is not available, return null."
                                }
                            },
                            "required": ["quote_text", "person_quoted_full_name", "person_quoted_job_title"]
                        }
                    }
                },
                "required": ["featured_company_name", "featured_company_domain", "quotes_and_testimonials"]
            }
        }
    }

    output = await call_parallel_ai(input_data, task_spec, processor="lite")

    return {
        "success": True,
        "case_study_url": request.case_study_url,
        "origin_company_domain": request.origin_company_domain,
        "featured_company_name": output.get("featured_company_name"),
        "featured_company_domain": output.get("featured_company_domain"),
        "quotes_and_testimonials": output.get("quotes_and_testimonials", [])
    }


@router.post("/case-study/extract-pro")
async def extract_case_study_pro(request: CaseStudyExtractRequest):
    """
    Extract structured details from a case study URL using Parallel AI (Pro processor).
    Returns featured company name, domain, and quotes/testimonials.
    """
    input_data = {
        "case_study_url": request.case_study_url
    }

    task_spec = {
        "input_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "properties": {
                    "case_study_url": {
                        "type": "string",
                        "description": "The URL of the case study to extract details from."
                    }
                },
                "required": ["case_study_url"]
            }
        },
        "output_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "featured_company_name": {
                        "type": "string",
                        "description": "The full name of the company that is featured as a customer in the case study. If the company name is not explicitly stated, return null."
                    },
                    "featured_company_domain": {
                        "type": "string",
                        "description": "The primary website domain of the company featured as a customer in the case study (e.g., 'example.com'). If the domain is not explicitly stated or cannot be reliably inferred, return null."
                    },
                    "quotes_and_testimonials": {
                        "type": "array",
                        "description": "A list of all quotes or testimonials from the case study, each including the quote text, the full name of the person quoted, and their job title.",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "quote_text": {
                                    "type": "string",
                                    "description": "The full text of the quote or testimonial, highlighting the customer's positive experience or the value received."
                                },
                                "person_quoted_full_name": {
                                    "type": "string",
                                    "description": "The full name of the individual who provided this quote or testimonial. If no person is identified, return null."
                                },
                                "person_quoted_job_title": {
                                    "type": "string",
                                    "description": "The job title of the individual who provided this quote or testimonial. If the job title is not available, return null."
                                }
                            },
                            "required": ["quote_text", "person_quoted_full_name", "person_quoted_job_title"]
                        }
                    }
                },
                "required": ["featured_company_name", "featured_company_domain", "quotes_and_testimonials"]
            }
        }
    }

    output = await call_parallel_ai(input_data, task_spec, processor="pro")

    return {
        "success": True,
        "case_study_url": request.case_study_url,
        "origin_company_domain": request.origin_company_domain,
        "featured_company_name": output.get("featured_company_name"),
        "featured_company_domain": output.get("featured_company_domain"),
        "quotes_and_testimonials": output.get("quotes_and_testimonials", [])
    }


@router.post("/case-study/extract-v2")
async def extract_case_study_v2(request: CaseStudyExtractRequest):
    """
    Extract structured details from a case study URL using Parallel AI.
    V2: Matches Parallel UI task spec exactly.
    """
    input_data = {
        "case_study_url": request.case_study_url
    }

    task_spec = {
        "input_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "properties": {
                    "case_study_url": {
                        "type": "string",
                        "description": "The URL of the case study to extract details from."
                    }
                },
                "required": ["case_study_url"]
            }
        },
        "output_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "customer_company_name": {
                        "type": "string",
                        "description": "The full, official name of the company featured as a customer in the case study. If the company name is not explicitly stated or cannot be confidently identified, return null."
                    },
                    "customer_company_domain": {
                        "type": "string",
                        "description": "The primary website domain (e.g., 'example.com') of the company featured as a customer in the case study. If the domain is not explicitly stated or cannot be confidently identified, return null."
                    },
                    "publishing_company_name": {
                        "type": "string",
                        "description": "The full, official name of the company publishing or authoring the case study. If the publishing company name is not explicitly stated or cannot be confidently identified, return null."
                    },
                    "champions": {
                        "type": "array",
                        "description": "A list of all individuals featured as champions or spokespersons in the case study who provide testimonials or quotations.",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "champion_full_name": {
                                    "type": "string",
                                    "description": "The full name of the individual featured as a champion or spokesperson in the case study."
                                },
                                "champion_job_title": {
                                    "type": "string",
                                    "description": "The job title of the individual featured as a champion in the case study. If the job title is not explicitly stated or cannot be confidently identified, return null."
                                },
                                "champion_testimonials_or_quotations": {
                                    "type": "string",
                                    "description": "All direct testimonials or quotations attributed to this champion in the case study, concatenated into a single string. If multiple testimonials/quotations exist, separate them with a newline character."
                                }
                            },
                            "required": ["champion_full_name", "champion_job_title", "champion_testimonials_or_quotations"]
                        }
                    }
                },
                "required": ["customer_company_name", "customer_company_domain", "publishing_company_name", "champions"]
            }
        }
    }

    output = await call_parallel_ai_v2(input_data, task_spec, timeout_seconds=120, processor="lite")

    return {
        "success": True,
        "case_study_url": request.case_study_url,
        "origin_company_domain": request.origin_company_domain,
        "customer_company_name": output.get("customer_company_name"),
        "customer_company_domain": output.get("customer_company_domain"),
        "publishing_company_name": output.get("publishing_company_name"),
        "champions": output.get("champions", [])
    }
