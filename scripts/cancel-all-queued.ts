import { runs, configure } from "@trigger.dev/sdk/v3";

configure({ secretKey: process.env.TRIGGER_SECRET_KEY });

async function main() {
  let cancelled = 0;
  let hasMore = true;

  while (hasMore) {
    const list = await runs.list({
      taskIdentifier: "gtm-brief-enrichment",
      status: ["QUEUED"],
      limit: 100,
    });

    if (list.data.length === 0) {
      hasMore = false;
      break;
    }

    for (const run of list.data) {
      await runs.cancel(run.id);
      cancelled++;
    }
    console.log(`Cancelled ${cancelled} so far...`);
  }

  console.log(`Done. Total cancelled: ${cancelled}`);
}

main().catch(console.error);
