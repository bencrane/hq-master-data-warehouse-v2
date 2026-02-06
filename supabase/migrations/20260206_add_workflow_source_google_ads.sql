-- Add workflow_source to core.company_google_ads
ALTER TABLE core.company_google_ads
ADD COLUMN IF NOT EXISTS workflow_source TEXT;

-- Update existing records to indicate legacy source
UPDATE core.company_google_ads
SET workflow_source = 'legacy'
WHERE workflow_source IS NULL;

-- Add unique constraint on creative_id for upsert support
CREATE UNIQUE INDEX IF NOT EXISTS idx_extracted_company_google_ads_creative_id_unique
ON extracted.company_google_ads(creative_id)
WHERE creative_id IS NOT NULL;
