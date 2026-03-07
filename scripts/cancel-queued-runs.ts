import { runs, configure } from "@trigger.dev/sdk/v3";

configure({ secretKey: process.env.TRIGGER_SECRET_KEY });

async function main() {
  const list = await runs.list({ taskIdentifier: "gtm-brief-enrichment", status: ["QUEUED"], limit: 100 });
  console.log(`Found ${list.data.length} queued runs to cancel`);

  for (const run of list.data) {
    await runs.cancel(run.id);
  }
  console.log("All queued runs cancelled");
}

main().catch(console.error);
