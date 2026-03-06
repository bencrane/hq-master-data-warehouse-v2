import { task, logger } from "@trigger.dev/sdk/v3";
import Parallel from "parallel-web";
import { GTM_BRIEF_CONFIG } from "./config/gtm-brief";

const HQ_API_URL = process.env.HQ_API_URL!; // e.g. https://your-railway-app.up.railway.app

export const gtmBriefEnrichment = task({
  id: "gtm-brief-enrichment",
  maxDuration: GTM_BRIEF_CONFIG.maxDuration,
  retry: {
    maxAttempts: 2,
  },
  run: async (payload: { origin_company_domain: string; limit?: number }) => {
    const limit = payload.limit ?? 1;

    // 1. Fetch leads + prompt template from FastAPI
    const leadsRes = await fetch(
      `${HQ_API_URL}/parallel-native/gtm-brief/leads?origin_company_domain=${encodeURIComponent(payload.origin_company_domain)}&limit=${limit}`
    );

    if (!leadsRes.ok) {
      throw new Error(`Failed to fetch leads: ${leadsRes.status} ${await leadsRes.text()}`);
    }

    const { leads, prompt_template, processor } = await leadsRes.json();

    if (!leads || leads.length === 0) {
      logger.info("No unprocessed leads found");
      return { processed: 0 };
    }

    logger.info(`Found ${leads.length} lead(s) to process`);

    const promptText: string = prompt_template.prompt;
    if (!promptText) {
      throw new Error("prompt_template.prompt is missing from registry");
    }

    const parallel = new Parallel({
      apiKey: process.env.PARALLEL_API_KEY!,
      timeout: 1_500_000, // 25 min HTTP timeout — result endpoint blocks until task completes
    });

    const results = [];

    for (const lead of leads) {
      logger.info(`Processing: ${lead.lead_full_name} (${lead.lead_linkedin_url})`);

      // 2. Substitute {{placeholders}} in the prompt template
      let prompt = promptText;
      for (const [viewCol, templateVar] of Object.entries(GTM_BRIEF_CONFIG.variableMap)) {
        const value = lead[viewCol];
        prompt = prompt.replaceAll(`{{${templateVar}}}`, String(value ?? ""));
      }

      // 3. Call Parallel — create task run
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
          person_linkedin_url: lead.lead_linkedin_url,
          origin_company_domain: lead.origin_company_domain,
          lead_full_name: lead.lead_full_name,
          lead_current_company_domain: lead.lead_current_company_domain,
          lead_past_company_domain: lead.lead_past_company_domain,
          run_id: "",
          raw_payload: {},
          success: false,
          error_message: errorMsg,
        });

        results.push({ lead: lead.lead_full_name, success: false, error: errorMsg });
        continue;
      }

      // 4. Wait for result (SDK handles polling internally)
      let runResult;
      try {
        runResult = await parallel.taskRun.result(taskRun.run_id, {
          timeout: 1_500_000, // 25 minutes in ms — pro processor deep research
        });
        logger.info(`Result received for ${lead.lead_full_name}`);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : String(err);
        logger.error(`Failed to get result: ${errorMsg}`);

        await storeResult({
          person_linkedin_url: lead.lead_linkedin_url,
          origin_company_domain: lead.origin_company_domain,
          lead_full_name: lead.lead_full_name,
          lead_current_company_domain: lead.lead_current_company_domain,
          lead_past_company_domain: lead.lead_past_company_domain,
          run_id: taskRun.run_id,
          raw_payload: {},
          success: false,
          error_message: errorMsg,
        });

        results.push({ lead: lead.lead_full_name, success: false, error: errorMsg });
        continue;
      }

      // 5. Store result via FastAPI
      const output = runResult?.output ?? runResult;

      await storeResult({
        person_linkedin_url: lead.lead_linkedin_url,
        origin_company_domain: lead.origin_company_domain,
        lead_full_name: lead.lead_full_name,
        lead_current_company_domain: lead.lead_current_company_domain,
        lead_past_company_domain: lead.lead_past_company_domain,
        run_id: taskRun.run_id,
        raw_payload: runResult,
        output,
        success: true,
      });

      results.push({
        lead: lead.lead_full_name,
        run_id: taskRun.run_id,
        success: true,
      });
    }

    logger.info(`Processed ${results.length} lead(s)`);
    return { processed: results.length, results };
  },
});

async function storeResult(data: {
  person_linkedin_url: string;
  origin_company_domain: string;
  lead_full_name: string;
  lead_current_company_domain?: string;
  lead_past_company_domain?: string;
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
