# Data Cleanup TODO (Non-Urgent)

These items are non-urgent because the affected records are already hidden from the dashboard via API filters.

---

## Companies

### Delete companies with no location data
- **Table:** `core.companies_missing_location`
- **Count:** ~55,000 companies
- **Criteria:** `discovery_location IS NULL AND salesnav_location IS NULL`
- **Why non-urgent:** API requires `company_country` - these leads don't show up anyway
- **SQL (run in small batches):**
```sql
DELETE FROM core.companies
WHERE id IN (
    SELECT id
    FROM core.companies_missing_location
    WHERE discovery_location IS NULL
      AND salesnav_location IS NULL
    LIMIT 100
);
```

---

## People

### Backfill person_tenure with new start dates
- **Table:** `core.person_job_start_dates` has 4,858 people not in `core.person_tenure`
- **Action:** Insert these into person_tenure
- **Why created:** Apollo InstantData "new in role" + SalesNav + person_profile start dates

---

## Reference Tables to Clean

### companies_missing_cleaned_name
- Created for Clay enrichment
- Can delete after enrichment complete

### people_missing_country
- Created for reviewing people without country
- Can delete after backfill complete

---

## Notes

- API required fields: `company_name`, `company_country`, `person_country`, `matched_job_function`, `matched_seniority`
- Records missing any of these are automatically hidden from dashboard
- Focus enrichment efforts on filling these gaps to increase visible lead count
