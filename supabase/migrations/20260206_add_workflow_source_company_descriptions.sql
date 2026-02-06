-- Add workflow_source to core.company_descriptions
ALTER TABLE core.company_descriptions
ADD COLUMN IF NOT EXISTS workflow_source TEXT;

-- Update existing records to indicate legacy source
UPDATE core.company_descriptions
SET workflow_source = COALESCE(source, 'legacy')
WHERE workflow_source IS NULL;
