import { task, logger } from "@trigger.dev/sdk/v3";
import Parallel from "parallel-web";
import { GTM_BRIEF_CONFIG } from "./config/gtm-brief";

const HQ_API_URL = process.env.HQ_API_URL!;

// Each run processes exactly 1 lead. Lead data + prompt passed in payload.
// This allows safe parallel execution — no race conditions on DB reads.

interface GtmBriefPayload {
  lead: Record<string, string | null>;
  prompt_template: string;
  processor: string;
}

export const gtmBriefEnrichment = task({
  id: "gtm-brief-enrichment",
  maxDuration: GTM_BRIEF_CONFIG.maxDuration,
  queue: {
    concurrencyLimit: 5,
  },
  retry: {
    maxAttempts: 2,
  },
  run: async (payload: GtmBriefPayload) => {
    const { lead, prompt_template, processor } = payload;

    logger.info(`Processing: ${lead.lead_full_name} (${lead.lead_linkedin_url})`);

    // 1. Substitute {{placeholders}} in the prompt template
    let prompt = prompt_template;
    for (const [viewCol, templateVar] of Object.entries(GTM_BRIEF_CONFIG.variableMap)) {
      prompt = prompt.replaceAll(`{{${templateVar}}}`, String(lead[viewCol] ?? ""));
    }

    const parallel = new Parallel({
      apiKey: process.env.PARALLEL_API_KEY!,
      timeout: 1_500_000,
    });

    // 2. Call Parallel — create task run
    let taskRun;
    try {
      taskRun = await parallel.taskRun.create({
        input: prompt,
        processor: processor ?? GTM_BRIEF_CONFIG.processor,
      });
      logger.info(`Task created — run_id: ${taskRun.run_id}`);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      logger.error(`Failed to create task: ${errorMsg}`);

      await storeResult({
        person_linkedin_url: lead.lead_linkedin_url ?? "",
        origin_company_domain: lead.origin_company_domain ?? "",
        lead_full_name: lead.lead_full_name ?? "",
        lead_current_company_domain: lead.lead_current_company_domain,
        lead_past_company_domain: lead.lead_past_company_domain,
        run_id: "",
        raw_payload: {},
        success: false,
        error_message: errorMsg,
      });

      return { lead: lead.lead_full_name, success: false, error: errorMsg };
    }

    // 3. Wait for result (SDK blocks until complete)
    let runResult;
    try {
      runResult = await parallel.taskRun.result(taskRun.run_id, {
        timeout: 1_500_000,
      });
      logger.info(`Result received for ${lead.lead_full_name}`);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      logger.error(`Failed to get result: ${errorMsg}`);

      await storeResult({
        person_linkedin_url: lead.lead_linkedin_url ?? "",
        origin_company_domain: lead.origin_company_domain ?? "",
        lead_full_name: lead.lead_full_name ?? "",
        lead_current_company_domain: lead.lead_current_company_domain,
        lead_past_company_domain: lead.lead_past_company_domain,
        run_id: taskRun.run_id,
        raw_payload: {},
        success: false,
        error_message: errorMsg,
      });

      return { lead: lead.lead_full_name, success: false, error: errorMsg };
    }

    // 4. Store result via FastAPI
    const output = runResult?.output ?? runResult;

    await storeResult({
      person_linkedin_url: lead.lead_linkedin_url ?? "",
      origin_company_domain: lead.origin_company_domain ?? "",
      lead_full_name: lead.lead_full_name ?? "",
      lead_current_company_domain: lead.lead_current_company_domain,
      lead_past_company_domain: lead.lead_past_company_domain,
      run_id: taskRun.run_id,
      raw_payload: runResult,
      output,
      success: true,
    });

    return {
      lead: lead.lead_full_name,
      run_id: taskRun.run_id,
      success: true,
    };
  },
});

async function storeResult(data: {
  person_linkedin_url: string;
  origin_company_domain: string;
  lead_full_name: string;
  lead_current_company_domain?: string | null;
  lead_past_company_domain?: string | null;
  run_id: string;
  raw_payload: unknown;
  output?: unknown;
  success: boolean;
  error_message?: string;
}) {
  const res = await fetch(`${HQ_API_URL}/parallel-native/gtm-brief/result`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    logger.error(`Failed to store result: ${res.status} ${await res.text()}`);
  }
}
