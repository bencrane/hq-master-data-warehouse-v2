#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
API_BASE_URL="${API_BASE_URL:-https://api.revenueinfra.com}"

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required"
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required"
  exit 1
fi
if ! command -v psql >/dev/null 2>&1; then
  echo "psql is required"
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo ".env not found at ${ENV_FILE}"
  exit 1
fi

DATABASE_URL="$(python3 - <<PY
from pathlib import Path
env = Path("${ENV_FILE}").read_text().splitlines()
for line in env:
    if line.startswith("DATABASE_URL="):
        print(line.split("=", 1)[1].strip())
        break
PY
)"

if [[ -z "${DATABASE_URL}" ]]; then
  echo "DATABASE_URL missing in .env"
  exit 1
fi

INGEST_API_KEY="${INGEST_API_KEY:-${1:-}}"
if [[ -z "${INGEST_API_KEY}" ]]; then
  echo "Provide INGEST_API_KEY as env var or first arg."
  echo "Example: INGEST_API_KEY=... bash scripts/smoke_brightdata_ingest.sh"
  exit 1
fi

STAMP="$(date +%Y%m%d%H%M%S)"
RAND_SUFFIX="$(python3 - <<'PY'
import random, string
print("".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6)))
PY
)"
TEST_ID="qa_${STAMP}_${RAND_SUFFIX}"
INDEED_JOBID="qa_indeed_${TEST_ID}"
LINKEDIN_JOBID="qa_linkedin_${TEST_ID}"
UPDATED_TITLE="Accountant II (Upsert Check)"

echo "Running BrightData smoke test with TEST_ID=${TEST_ID}"

INDEED_PAYLOAD="$(jq -cn --arg jobid "${INDEED_JOBID}" '{
  records: [{
    jobid: $jobid,
    company_name: "QA Smoke Inc",
    job_title: "Accountant",
    description_text: "Smoke test description",
    description: "Smoke test description",
    benefits: ["Health insurance"],
    job_type: "Full-time",
    location: "Austin, TX",
    job_location: "Austin, TX",
    country: "US",
    region: "TX",
    date_posted: "30+ days ago",
    date_posted_parsed: null,
    url: ("https://www.indeed.com/viewjob?jk=" + $jobid),
    domain: "https://www.indeed.com",
    is_expired: false,
    discovery_input: null
  }],
  metadata: {snapshot_id: ("smoke-" + $jobid), source_file: "smoke-indeed.json"}
}')"

LINKEDIN_PAYLOAD="$(jq -cn --arg jobid "${LINKEDIN_JOBID}" '{
  records: [{
    job_posting_id: $jobid,
    url: ("https://www.linkedin.com/jobs/view/" + $jobid),
    job_title: "Accountant",
    company_name: "QA Smoke Inc",
    company_id: "17719",
    job_location: "Heredia, Costa Rica",
    job_summary: "Smoke summary",
    job_seniority_level: "Not Applicable",
    job_function: "Accounting/Auditing and Finance",
    job_employment_type: "Full-time",
    job_industries: "Software Development",
    job_base_pay_range: null,
    job_posted_time: "4 months ago",
    job_num_applicants: 25,
    discovery_input: {experience_level: null, job_type: null, remote: null, selective_search: null, time_range: null},
    apply_link: null,
    country_code: null,
    title_id: "40",
    company_logo: "https://media.licdn.com/dms/image/v2/smoke",
    job_posted_date: "2025-10-20T18:26:28.963Z",
    job_poster: {name: null, title: null, url: null},
    application_availability: false,
    job_description_formatted: "<section>smoke</section>",
    base_salary: {currency: null, max_amount: null, min_amount: null, payment_period: null},
    salary_standards: null,
    is_easy_apply: false
  }],
  metadata: {snapshot_id: ("smoke-" + $jobid), source_file: "smoke-linkedin.json"}
}')"

echo "Calling Indeed endpoint..."
INDEED_RESPONSE="$(curl -sS -X POST "${API_BASE_URL}/api/ingest/brightdata/indeed" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${INGEST_API_KEY}" \
  -d "${INDEED_PAYLOAD}")"
echo "${INDEED_RESPONSE}" | jq .

echo "Calling LinkedIn endpoint..."
LINKEDIN_RESPONSE="$(curl -sS -X POST "${API_BASE_URL}/api/ingest/brightdata/linkedin" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${INGEST_API_KEY}" \
  -d "${LINKEDIN_PAYLOAD}")"
echo "${LINKEDIN_RESPONSE}" | jq .

echo "Checking inserted rows..."
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
SELECT jobid, job_title, ingestion_batch_id, first_seen_at, ingested_at
FROM raw.brightdata_indeed_job_listings
WHERE jobid = '${INDEED_JOBID}';

SELECT job_posting_id, job_title, ingestion_batch_id, first_seen_at, ingested_at
FROM raw.brightdata_linkedin_job_listings
WHERE job_posting_id = '${LINKEDIN_JOBID}';
SQL

echo "Running Indeed upsert check (same jobid, new title)..."
INDEED_UPSERT_PAYLOAD="$(echo "${INDEED_PAYLOAD}" | jq --arg title "${UPDATED_TITLE}" '.records[0].job_title = $title')"
curl -sS -X POST "${API_BASE_URL}/api/ingest/brightdata/indeed" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${INGEST_API_KEY}" \
  -d "${INDEED_UPSERT_PAYLOAD}" >/dev/null

echo "Validating upsert timestamps..."
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
WITH row_data AS (
  SELECT first_seen_at, ingested_at, job_title
  FROM raw.brightdata_indeed_job_listings
  WHERE jobid = '${INDEED_JOBID}'
)
SELECT
  (job_title = '${UPDATED_TITLE}') AS title_updated,
  (ingested_at >= first_seen_at) AS timestamp_valid,
  first_seen_at,
  ingested_at
FROM row_data;
SQL

echo "Summary view check..."
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "SELECT * FROM raw.brightdata_job_listings_summary ORDER BY source;"

echo "Smoke test complete."
