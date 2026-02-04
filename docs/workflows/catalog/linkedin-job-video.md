# LinkedIn Job Video Extraction

Extracts job postings from video recordings of LinkedIn job search results using GPT-4o vision.

## Endpoint

```
POST https://bencrane--hq-master-data-ingest-ingest-linkedin-job-video.modal.run
```

## Request

**Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `video` | File | Yes | Video file (MP4, MOV, WebM) |
| `search_query` | string | No | LinkedIn search query used |
| `search_date` | string | No | Date of search (YYYY-MM-DD) |
| `linkedin_search_url` | string | No | Full LinkedIn search URL |

### Example with curl

```bash
curl -X POST https://bencrane--hq-master-data-ingest-ingest-linkedin-job-video.modal.run \
  -F "video=@linkedin_search.mp4" \
  -F "search_query=gtm engineer" \
  -F "search_date=2026-02-03" \
  -F "linkedin_search_url=https://linkedin.com/jobs/search/?keywords=gtm%20engineer"
```

## Response

```json
{
  "success": true,
  "raw_video_id": "uuid",
  "video_filename": "linkedin_search.mp4",
  "video_duration_seconds": 45.2,
  "frames_extracted": 22,
  "jobs_extracted": 15,
  "tokens_used": 12500
}
```

## Database Tables

### Raw Table: `raw.linkedin_job_search_videos`

Stores video metadata and OpenAI response.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `search_query` | TEXT | LinkedIn search query |
| `search_date` | DATE | Date of search |
| `linkedin_search_url` | TEXT | Full search URL |
| `video_filename` | TEXT | Original filename |
| `video_size_bytes` | BIGINT | File size |
| `video_duration_seconds` | FLOAT | Video duration |
| `frames_extracted` | INTEGER | Number of frames sent to GPT-4o |
| `openai_model` | TEXT | Model used (gpt-4o) |
| `openai_response` | JSONB | Full API response |
| `tokens_used` | INTEGER | Total tokens consumed |
| `created_at` | TIMESTAMPTZ | When processed |

### Extracted Table: `extracted.linkedin_job_postings_video`

Individual job postings extracted from video.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `raw_video_id` | UUID | Reference to raw video |
| `search_query` | TEXT | Search query (denormalized) |
| `search_date` | DATE | Search date (denormalized) |
| `job_title` | TEXT | Job title |
| `company_name` | TEXT | Company name |
| `company_logo_description` | TEXT | Logo description if visible |
| `location` | TEXT | Job location |
| `work_type` | TEXT | Remote, Hybrid, On-site |
| `salary_min` | INTEGER | Minimum salary |
| `salary_max` | INTEGER | Maximum salary |
| `salary_currency` | TEXT | Currency (default USD) |
| `salary_period` | TEXT | yr, mo, hr |
| `is_promoted` | BOOLEAN | Has Promoted badge |
| `is_easy_apply` | BOOLEAN | Has Easy Apply badge |
| `is_actively_reviewing` | BOOLEAN | Actively reviewing badge |
| `confidence` | FLOAT | AI confidence (0-1) |
| `frame_source` | INTEGER | Which frame job was extracted from |
| `created_at` | TIMESTAMPTZ | When extracted |

## How It Works

1. **Video Upload** - User uploads MP4/MOV/WebM of LinkedIn job search
2. **Frame Extraction** - OpenCV extracts frames every 2 seconds (max 30 frames)
3. **GPT-4o Vision** - Frames sent to GPT-4o with structured extraction prompt
4. **Deduplication** - Same job appearing in multiple frames is deduplicated
5. **Storage** - Raw response and extracted jobs stored in database

## Processing Details

- **Frame Interval**: 2 seconds
- **Max Frames**: 30
- **Max Resolution**: 1280px width (maintains aspect ratio)
- **Timeout**: 5 minutes
- **Model**: GPT-4o (vision)

## Extracted Fields

The AI extracts these fields from each visible job posting:
- Job title
- Company name
- Location
- Work type (Remote/Hybrid/On-site)
- Salary range and period
- Badges (Promoted, Easy Apply, Actively Reviewing)
- Extraction confidence score

## Cost Considerations

GPT-4o vision charges per image. Each frame is an image.
- 30 frames at high detail ≈ $0.30-0.50 per video
- Tokens also charged for response

## Files

- Ingest: `modal-functions/src/ingest/linkedin_job_video.py`
- Extraction: `modal-functions/src/extraction/linkedin_job_video.py`
- Migration: `supabase/migrations/20260204_linkedin_job_video_tables.sql`

## Verification Queries

```sql
-- Check raw record
SELECT
    id,
    search_query,
    video_filename,
    video_duration_seconds,
    frames_extracted,
    tokens_used,
    created_at
FROM raw.linkedin_job_search_videos
ORDER BY created_at DESC
LIMIT 1;

-- Check extracted jobs
SELECT
    job_title,
    company_name,
    location,
    work_type,
    salary_min,
    salary_max,
    is_easy_apply,
    confidence
FROM extracted.linkedin_job_postings_video
WHERE raw_video_id = '[id from above]';

-- Jobs by company
SELECT
    company_name,
    COUNT(*) as job_count
FROM extracted.linkedin_job_postings_video
GROUP BY company_name
ORDER BY job_count DESC;
```
