-- Migration: Add endpoint mapping columns to workflow registry
-- Created: 2026-02-02
-- Purpose: Track Modal function name, Modal endpoint URL, and API wrapper endpoint URL

ALTER TABLE reference.enrichment_workflow_registry
ADD COLUMN IF NOT EXISTS modal_function_name TEXT;

ALTER TABLE reference.enrichment_workflow_registry
ADD COLUMN IF NOT EXISTS modal_endpoint_url TEXT;

ALTER TABLE reference.enrichment_workflow_registry
ADD COLUMN IF NOT EXISTS api_endpoint_url TEXT;

-- Add comments
COMMENT ON COLUMN reference.enrichment_workflow_registry.modal_function_name IS 'Python function name in Modal (e.g., ingest_clay_find_companies)';
COMMENT ON COLUMN reference.enrichment_workflow_registry.modal_endpoint_url IS 'Full Modal endpoint URL';
COMMENT ON COLUMN reference.enrichment_workflow_registry.api_endpoint_url IS 'API wrapper endpoint at api.revenueinfra.com';
