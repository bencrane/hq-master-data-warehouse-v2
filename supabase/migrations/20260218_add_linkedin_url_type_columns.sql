-- Add linkedin_url_type column to person-related tables
-- Matches existing pattern in core.people
-- Values: 'real' (default) or 'salesnav' (hashed SalesNav URLs)

-- core.person_work_history
ALTER TABLE core.person_work_history
ADD COLUMN IF NOT EXISTS linkedin_url_type TEXT DEFAULT 'real';

-- core.person_past_employer
ALTER TABLE core.person_past_employer
ADD COLUMN IF NOT EXISTS linkedin_url_type TEXT DEFAULT 'real';

-- core.person_job_start_dates
ALTER TABLE core.person_job_start_dates
ADD COLUMN IF NOT EXISTS linkedin_url_type TEXT DEFAULT 'real';
