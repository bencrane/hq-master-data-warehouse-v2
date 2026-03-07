import { tasks, configure } from "@trigger.dev/sdk/v3";

const TRIGGER_SECRET_KEY = process.env.TRIGGER_SECRET_KEY;
const HQ_API_URL = process.env.HQ_API_URL;

if (!TRIGGER_SECRET_KEY || !HQ_API_URL) {
  console.error("Missing TRIGGER_SECRET_KEY or HQ_API_URL");
  process.exit(1);
}

configure({ secretKey: TRIGGER_SECRET_KEY });

const ORIGIN_DOMAIN = process.argv[2] || "nostra.ai";
const LIMIT = parseInt(process.argv[3] || "100", 10);

async function main() {
  // 1. Fetch all unprocessed leads + prompt template from FastAPI
  const url = `${HQ_API_URL}/parallel-native/gtm-brief/leads?origin_company_domain=${encodeURIComponent(ORIGIN_DOMAIN)}&limit=${LIMIT}`;
  console.log(`Fetching leads from: ${url}`);

  const res = await fetch(url);
  if (!res.ok) {
    console.error(`Failed to fetch leads: ${res.status} ${await res.text()}`);
    process.exit(1);
  }

  const { leads, prompt_template, processor, count } = await res.json();
  console.log(`Found ${count} unprocessed leads for ${ORIGIN_DOMAIN}`);

  if (!leads || leads.length === 0) {
    console.log("No leads to process");
    return;
  }

  const promptText = prompt_template.prompt;
  if (!promptText) {
    console.error("prompt_template.prompt is missing");
    process.exit(1);
  }

  // 2. Build batch items — each run gets its own lead data
  const items = leads.map((lead: Record<string, string | null>) => ({
    payload: {
      lead,
      prompt_template: promptText,
      processor: processor ?? "pro",
    },
  }));

  // 3. Batch trigger
  console.log(`Batch triggering ${items.length} runs (concurrency=5)...`);
  const batch = await tasks.batchTrigger("gtm-brief-enrichment", items);
  console.log(`Batch triggered! ID: ${batch.id}`);
  console.log(`${items.length} runs queued — 5 will run in parallel.`);
  console.log(`Estimated time: ~${Math.ceil(items.length / 5) * 5} minutes`);
}

main().catch(console.error);
