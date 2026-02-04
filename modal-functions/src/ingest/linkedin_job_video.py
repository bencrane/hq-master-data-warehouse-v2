"""
LinkedIn Job Video Ingest Endpoint

Accepts video file upload of LinkedIn job search results.
Extracts frames, sends to GPT-4o, parses job postings.
Stores raw response and extracted jobs following raw -> extracted protocol.
"""

import os
import modal
from fastapi import UploadFile, File, Form
from typing import Optional
from config import app, image


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
        modal.Secret.from_name("openai-secret"),
    ],
    timeout=300,  # 5 min for video processing
)
@modal.fastapi_endpoint(method="POST")
async def ingest_linkedin_job_video(
    video: UploadFile = File(...),
    search_query: Optional[str] = Form(None),
    search_date: Optional[str] = Form(None),
    linkedin_search_url: Optional[str] = Form(None),
) -> dict:
    """
    Ingest LinkedIn job search video.

    1. Extract frames from video
    2. Send to GPT-4o for job extraction
    3. Store raw response + extracted jobs

    Args:
        video: Video file (MP4, MOV, WebM)
        search_query: The LinkedIn search query used
        search_date: Date of the search (YYYY-MM-DD)
        linkedin_search_url: Full LinkedIn search URL

    Returns:
        Success response with raw_video_id and job count
    """
    from supabase import create_client
    from openai import OpenAI
    from extraction.linkedin_job_video import (
        extract_frames_from_video,
        extract_jobs_with_openai,
        deduplicate_jobs,
    )

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    openai_api_key = os.environ["OPENAI_API_KEY"]
    openai_client = OpenAI(api_key=openai_api_key)

    try:
        # Read video file
        video_bytes = await video.read()
        video_filename = video.filename
        video_size_bytes = len(video_bytes)

        # Extract frames from video
        frames, video_duration = extract_frames_from_video(
            video_bytes,
            interval_seconds=2.0,
            max_frames=30,
        )

        if not frames:
            return {
                "success": False,
                "error": "Could not extract frames from video",
            }

        # Send to OpenAI for extraction
        jobs, raw_response = extract_jobs_with_openai(frames, openai_client)

        # Deduplicate jobs
        jobs = deduplicate_jobs(jobs)

        # 1. Store raw record
        raw_insert = (
            supabase.schema("raw")
            .from_("linkedin_job_search_videos")
            .insert({
                "search_query": search_query,
                "search_date": search_date,
                "linkedin_search_url": linkedin_search_url,
                "video_filename": video_filename,
                "video_size_bytes": video_size_bytes,
                "video_duration_seconds": video_duration,
                "frames_extracted": len(frames),
                "openai_model": raw_response.get("model", "gpt-4o"),
                "openai_response": raw_response,
                "tokens_used": raw_response.get("usage", {}).get("total_tokens"),
            })
            .execute()
        )
        raw_video_id = raw_insert.data[0]["id"]

        # 2. Store extracted jobs
        jobs_inserted = 0
        for job in jobs:
            job_title = job.get("job_title")
            company_name = job.get("company_name")

            # Skip jobs without required fields
            if not job_title or not company_name:
                continue

            supabase.schema("extracted").from_("linkedin_job_postings_video").insert({
                "raw_video_id": raw_video_id,
                "search_query": search_query,
                "search_date": search_date,
                "job_title": job_title,
                "company_name": company_name,
                "company_logo_description": job.get("company_logo_description"),
                "location": job.get("location"),
                "work_type": job.get("work_type"),
                "salary_min": job.get("salary_min"),
                "salary_max": job.get("salary_max"),
                "salary_currency": job.get("salary_currency", "USD"),
                "salary_period": job.get("salary_period"),
                "is_promoted": job.get("is_promoted", False),
                "is_easy_apply": job.get("is_easy_apply", False),
                "is_actively_reviewing": job.get("is_actively_reviewing", False),
                "confidence": job.get("confidence"),
                "frame_source": job.get("frame_source"),
            }).execute()

            jobs_inserted += 1

        return {
            "success": True,
            "raw_video_id": str(raw_video_id),
            "video_filename": video_filename,
            "video_duration_seconds": video_duration,
            "frames_extracted": len(frames),
            "jobs_extracted": jobs_inserted,
            "tokens_used": raw_response.get("usage", {}).get("total_tokens"),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "video_filename": video.filename if video else "unknown",
        }
