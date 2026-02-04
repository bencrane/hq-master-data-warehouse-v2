-- LinkedIn Job Video Extraction Tables
-- Raw + Extracted protocol for video-based job posting extraction

-- Raw Table: stores video metadata and OpenAI response
CREATE TABLE raw.linkedin_job_search_videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Search context
    search_query TEXT,
    search_date DATE,
    linkedin_search_url TEXT,

    -- Video metadata
    video_filename TEXT,
    video_size_bytes BIGINT,
    video_duration_seconds FLOAT,
    frames_extracted INTEGER,

    -- AI response
    openai_model TEXT,
    openai_response JSONB,
    tokens_used INTEGER,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_linkedin_job_search_videos_search_query
    ON raw.linkedin_job_search_videos(search_query);
CREATE INDEX idx_linkedin_job_search_videos_created_at
    ON raw.linkedin_job_search_videos(created_at DESC);

-- Extracted Table: individual job postings extracted from video
CREATE TABLE extracted.linkedin_job_postings_video (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_video_id UUID REFERENCES raw.linkedin_job_search_videos(id),

    -- Search context (denormalized)
    search_query TEXT,
    search_date DATE,

    -- Job posting fields
    job_title TEXT NOT NULL,
    company_name TEXT NOT NULL,
    company_logo_description TEXT,
    location TEXT,
    work_type TEXT,  -- Remote, Hybrid, On-site
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency TEXT DEFAULT 'USD',
    salary_period TEXT,  -- yr, mo, hr

    -- LinkedIn metadata
    is_promoted BOOLEAN DEFAULT FALSE,
    is_easy_apply BOOLEAN DEFAULT FALSE,
    is_actively_reviewing BOOLEAN DEFAULT FALSE,

    -- Extraction metadata
    confidence FLOAT,
    frame_source INTEGER,  -- which frame this was extracted from

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_linkedin_job_postings_video_raw_id
    ON extracted.linkedin_job_postings_video(raw_video_id);
CREATE INDEX idx_linkedin_job_postings_video_company
    ON extracted.linkedin_job_postings_video(company_name);
CREATE INDEX idx_linkedin_job_postings_video_title
    ON extracted.linkedin_job_postings_video(job_title);
CREATE INDEX idx_linkedin_job_postings_video_search_query
    ON extracted.linkedin_job_postings_video(search_query);
