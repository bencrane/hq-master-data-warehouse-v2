-- Signal: Job Posting - Add recency filter columns
-- Stores the min/max days since job posting parameter from Clay signal settings

ALTER TABLE extracted.signal_job_posting
    ADD COLUMN IF NOT EXISTS min_days_since_job_posting INTEGER,
    ADD COLUMN IF NOT EXISTS max_days_since_job_posting INTEGER;

COMMENT ON COLUMN extracted.signal_job_posting.min_days_since_job_posting IS 'Minimum days since job posting (Clay filter setting)';
COMMENT ON COLUMN extracted.signal_job_posting.max_days_since_job_posting IS 'Maximum days since job posting (Clay filter setting)';
