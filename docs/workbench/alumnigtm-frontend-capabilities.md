# AlumniGTM Frontend — Available Data & UI Capabilities

## Endpoint
`POST /v1/alumni-gtm/leads` with `{ "origin_company_domain": "nostra.ai" }`

Returns only **qualified leads** (company gtm_fit=true AND person icp_fit=true).

---

## Per-Lead Data

### Person
- Full name, first/last, LinkedIn URL, headline, location, picture URL
- Current job title, matched seniority & job function

### Current Company (where the lead works now)
- Name, domain, LinkedIn URL
- Firmographics: industry, employee count, size range, founded year, country/city/state, description

### Prior Company (the origin's customer they used to work at)
- Name, domain, role held, start/end dates
- GTM fit flag + reason
- Firmographics (same fields as current company, when available)

---

## Ads Intelligence (Adyntel)

### Meta Ads (up to 5 latest per company)
Each ad includes: `ad_id`, `platform`, `start_date`, `end_date`, `status`, `page_name`, `ad_creative_body`, `ad_creative_link_title`, `ad_creative_link_description`, `landing_page_url`, `image_url`, `video_url`

**What the frontend can do:**
- Show the latest ad creative (image or video) as a thumbnail/preview
- Display headline + body copy
- Link out to the landing page
- Show `meta_ads_count` as total historical volume
- Derive **ad recency** from the most recent `start_date` (e.g., "Last ad: 3 days ago")
- Derive **active ad count** by filtering `status = 'active'`
- Derive **ad lifespan** from `start_date` → `end_date` per ad
- Derive **ad velocity** by grouping ads by month using `start_date`
- Show platform breakdown (Facebook vs Instagram vs Threads)

### Google Ads (up to 5 latest per company)
Each ad includes: `creative_id`, `format`, `start_date`, `last_seen`, `advertiser_name`, `original_url`, `variant_content`

**What the frontend can do:**
- Show `format` (Text / Image / Video) as a badge
- Link to the Google Ads Transparency page via `original_url`
- Render `variant_content` (HTML/image embed for display ads)
- Show `google_ads_count` as total historical volume
- Derive **recency** from latest `last_seen`
- Derive **longevity** from `start_date` → `last_seen` (how long the ad ran)

### Combined Ads Signals
- **Total ad count** (`meta_ads_count + google_ads_count`) — proxy for ad spend commitment
- **Cross-platform presence** — running on both Meta + Google = serious advertiser
- **Recency indicator** — "Active advertiser" vs "Hasn't run ads in 6 months"

---

## Storeleads / E-commerce Data

- `platform` — Shopify, Magento, WooCommerce, etc.
- `estimated_sales` (monthly) + `estimated_sales_yearly` — revenue signal
- `estimated_visits` + `estimated_page_views` — traffic volume
- `product_count` — catalog size
- `rank` + `platform_rank` — overall and within-platform ranking
- `rank_percentile` + `platform_rank_percentile` — normalized rankings
- `trustpilot_avg_rating` + `trustpilot_review_count` — customer sentiment
- `categories` — what they sell
- `country_code` / `city` / `state` — store HQ location
- `technologies` — full tech stack (e.g., Klaviyo, Google Analytics, Shopify Plus)

**What the frontend can do:**
- Show an e-commerce platform badge (Shopify logo, etc.)
- Display estimated revenue range
- Show traffic stats as a signal of company size/activity
- Display Trustpilot rating with star visualization
- Show tech stack as tags/chips
- Filter or sort leads by revenue, traffic, or rank

---

## Summary / Prior Companies

The response includes `prior_companies_summary` — a ranked list of the origin's customers with lead counts per customer. This enables:
- A sidebar filter: "Show leads from Forever 21" / "Show leads from Birdies"
- A summary card: "16 customer companies, 88 qualified leads"

---

## Suggested UI Components

| Component | Data Source |
|---|---|
| Lead table row | person name, title, current company, prior company |
| Company detail card | firmographics, storeleads, ads |
| Ad preview carousel | meta_ads / google_ads (image, headline, body) |
| Revenue/traffic badges | storeleads estimated_sales_yearly, estimated_visits |
| Tech stack chips | storeleads technologies |
| Trustpilot stars | storeleads trustpilot_avg_rating |
| Prior company filter | prior_companies_summary |
| Ad activity indicator | meta_ads_count + google_ads_count + recency |
