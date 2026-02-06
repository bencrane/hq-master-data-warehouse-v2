-- Add workflow_source to core.company_meta_ads
ALTER TABLE core.company_meta_ads
ADD COLUMN IF NOT EXISTS workflow_source TEXT;

-- Update existing records to indicate legacy source
UPDATE core.company_meta_ads
SET workflow_source = 'legacy'
WHERE workflow_source IS NULL;

-- Add unique constraint on ad_id for upsert support
CREATE UNIQUE INDEX IF NOT EXISTS idx_extracted_company_meta_ads_ad_id_unique
ON extracted.company_meta_ads(ad_id)
WHERE ad_id IS NOT NULL;
