-- Email waterfall jobs tracking table
CREATE TABLE IF NOT EXISTS raw.email_waterfall_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL DEFAULT 'pending',
    total_records INTEGER NOT NULL,
    sent_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    clay_webhook_url TEXT NOT NULL,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_email_waterfall_jobs_status ON raw.email_waterfall_jobs(status);
CREATE INDEX idx_email_waterfall_jobs_created_at ON raw.email_waterfall_jobs(created_at);


