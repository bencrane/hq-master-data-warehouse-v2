// GTM Brief Enrichment Configuration
// Prompt template lives in reference.parallel_enrichment_registry (slug below).
// This file defines the enrichment slug, processor, and how view columns map to template variables.

export const GTM_BRIEF_CONFIG = {
  enrichmentSlug: "alumni_person_gtm_brief_unstructured_output",
  processor: "pro" as const,
  maxDuration: 600, // 10 minutes — pro processor can take a few minutes

  // Maps view column names to template {{placeholder}} names
  // These are identical in this case, but the mapping makes it explicit
  variableMap: {
    origin_company_name: "origin_company_name",
    origin_company_domain: "origin_company_domain",
    origin_company_description: "origin_company_description",
    lead_full_name: "lead_full_name",
    lead_linkedin_url: "lead_linkedin_url",
    lead_current_job_title: "lead_current_job_title",
    lead_current_company_name: "lead_current_company_name",
    lead_current_company_domain: "lead_current_company_domain",
    lead_current_company_description: "lead_current_company_description",
    lead_past_company_name: "lead_past_company_name",
    lead_past_company_domain: "lead_past_company_domain",
    lead_past_company_description: "lead_past_company_description",
    lead_past_company_job_title: "lead_past_company_job_title",
  },
} as const;

export type AlumniGtmLead = {
  origin_company_name: string;
  origin_company_domain: string;
  origin_company_linkedin_url: string | null;
  origin_company_description: string | null;
  lead_full_name: string;
  lead_linkedin_url: string;
  lead_current_job_title: string | null;
  lead_current_company_name: string | null;
  lead_current_company_domain: string | null;
  lead_current_company_description: string | null;
  lead_past_company_name: string;
  lead_past_company_domain: string;
  lead_past_company_description: string | null;
  lead_past_company_job_title: string | null;
  has_gtm_brief: boolean;
};
