"""
LinkedIn Job Video Extraction Logic

Handles video frame extraction and OpenAI GPT-4o vision processing.
"""

import base64
import json
import re
from typing import Optional


EXTRACTION_PROMPT = """You are analyzing screenshots from a LinkedIn job search results page.
Extract ALL visible job postings into a JSON array.

For each job posting, extract:
- job_title: The job title
- company_name: The company name
- company_logo_description: Brief description of company logo if visible
- location: Location if visible (city, state, country)
- work_type: "Remote", "Hybrid", "On-site", or null if not shown
- salary_min: Minimum salary as integer (null if not shown)
- salary_max: Maximum salary as integer (null if not shown)
- salary_period: "yr", "mo", or "hr" (null if not shown)
- is_promoted: true if shows "Promoted" badge
- is_easy_apply: true if shows "Easy Apply" badge
- is_actively_reviewing: true if shows "Actively reviewing" or similar badge
- confidence: Your confidence in this extraction from 0.0 to 1.0

Return ONLY valid JSON array. No markdown, no explanation, no code blocks.
Example: [{"job_title": "Software Engineer", "company_name": "Acme Corp", "location": "San Francisco, CA", "work_type": "Remote", "salary_min": 150000, "salary_max": 200000, "salary_period": "yr", "is_promoted": false, "is_easy_apply": true, "is_actively_reviewing": false, "confidence": 0.95}]

If you see the same job posting in multiple frames, only include it once with the highest confidence extraction."""


def extract_frames_from_video(video_bytes: bytes, interval_seconds: float = 2.0, max_frames: int = 30) -> list[tuple[int, bytes]]:
    """
    Extract frames from video at specified intervals.

    Args:
        video_bytes: Raw video file bytes
        interval_seconds: Extract frame every N seconds
        max_frames: Maximum number of frames to extract

    Returns:
        List of (frame_number, jpeg_bytes) tuples
    """
    import cv2
    import numpy as np
    import tempfile
    import os

    # Write video to temp file (OpenCV needs file path)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(video_bytes)
        temp_path = f.name

    try:
        cap = cv2.VideoCapture(temp_path)
        if not cap.isOpened():
            raise ValueError("Could not open video file")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0

        # Calculate frame interval
        frame_interval = int(fps * interval_seconds) if fps > 0 else 60

        frames = []
        frame_num = 0

        while len(frames) < max_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()

            if not ret:
                break

            # Resize to max 1280px width while maintaining aspect ratio
            height, width = frame.shape[:2]
            if width > 1280:
                scale = 1280 / width
                new_width = 1280
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height))

            # Encode as JPEG
            _, jpeg_bytes = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frames.append((frame_num, jpeg_bytes.tobytes()))

            frame_num += frame_interval

        cap.release()
        return frames, duration

    finally:
        os.unlink(temp_path)


def encode_frame_for_openai(jpeg_bytes: bytes) -> dict:
    """Encode frame as base64 for OpenAI vision API."""
    base64_image = base64.b64encode(jpeg_bytes).decode("utf-8")
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{base64_image}",
            "detail": "high"
        }
    }


def extract_jobs_with_openai(frames: list[tuple[int, bytes]], openai_client) -> tuple[list[dict], dict]:
    """
    Send frames to OpenAI GPT-4o and extract job postings.

    Args:
        frames: List of (frame_number, jpeg_bytes) tuples
        openai_client: OpenAI client instance

    Returns:
        Tuple of (extracted_jobs, raw_response)
    """
    # Build message content with all frames
    content = [
        {"type": "text", "text": EXTRACTION_PROMPT}
    ]

    frame_mapping = {}
    for i, (frame_num, jpeg_bytes) in enumerate(frames):
        content.append(encode_frame_for_openai(jpeg_bytes))
        frame_mapping[i] = frame_num

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": content
            }
        ],
        max_tokens=4096,
    )

    raw_response = {
        "id": response.id,
        "model": response.model,
        "content": response.choices[0].message.content,
        "finish_reason": response.choices[0].finish_reason,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
    }

    # Parse JSON from response
    response_text = response.choices[0].message.content.strip()

    # Try to extract JSON array from response
    jobs = parse_jobs_from_response(response_text)

    return jobs, raw_response


def parse_jobs_from_response(response_text: str) -> list[dict]:
    """Parse job postings from OpenAI response text."""
    # Remove markdown code blocks if present
    response_text = re.sub(r"^```(?:json)?\s*", "", response_text)
    response_text = re.sub(r"\s*```$", "", response_text)
    response_text = response_text.strip()

    try:
        jobs = json.loads(response_text)
        if isinstance(jobs, list):
            return jobs
        return []
    except json.JSONDecodeError:
        # Try to find JSON array in response
        match = re.search(r"\[[\s\S]*\]", response_text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return []


def deduplicate_jobs(jobs: list[dict]) -> list[dict]:
    """
    Deduplicate jobs by (company_name, job_title).
    Keep the one with highest confidence.
    """
    seen = {}

    for job in jobs:
        company = (job.get("company_name") or "").lower().strip()
        title = (job.get("job_title") or "").lower().strip()
        key = (company, title)

        if not company or not title:
            continue

        confidence = job.get("confidence", 0.5)

        if key not in seen or confidence > seen[key].get("confidence", 0):
            seen[key] = job

    return list(seen.values())
