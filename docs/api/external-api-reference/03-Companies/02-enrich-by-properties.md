# Enrich by properties

`POST` `https://api.companyenrich.com/companies/enrich`

**Cost:** 1 credit per call

Enriches a company using its properties.

You need to provide at least one of the following properties:

- Domain
- Name
- LinkedinUrl
- TwitterUrl
- FacebookUrl
- InstagramUrl

Best match is used to determine the company in case of ambiguity.

## Body Params

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string \| null | The name of the company to enrich |
| `linkedinUrl` | uri \| null | The LinkedIn URL of the company to enrich |
| `twitterUrl` | uri \| null | The Twitter URL of the company to enrich |
| `facebookUrl` | uri \| null | The Facebook URL of the company to enrich |
| `instagramUrl` | uri \| null | The Instagram URL of the company to enrich |
| `youTubeUrl` | uri \| null | The YouTube URL of the company to enrich |

## Responses

### 200 OK

#### Response Body

| Field | Type | Description |
|-------|------|-------------|
| `id` | uuid | **Required.** The unique identifier of the company |
| `name` | string \| null | The name of the company |
| `domain` | string \| null | The primary domain name of the company |
| `website` | uri \| null | The website URL of the company |
| `type` | enum | The type of the company |
| `industry` | string \| null | The main industry of the company |
| `industries` | array of strings \| null | The industries associated with the company |
| `categories` | array \| null | The categories of the company from most to least specific |
| `employees` | enum | The range of number of employees of the company |
| `revenue` | enum | The range of annual revenue of the company in USD |
| `description` | string \| null | The description of the company |
| `keywords` | array of strings \| null | The search keywords of the company |
| `technologies` | array of strings \| null | The technologies associated with the company |
| `subsidiaries` | array of strings \| null | The subsidiaries associated with the company |
| `founded_year` | int32 \| null | The year the company was founded |
| `naics_codes` | array of strings \| null | The NAICS codes associated with the company |
| `location` | object \| null | The location information of the company |
| `location.country` | object \| null | The origin country information of the company |
| `location.state` | object \| null | The state information of the company |
| `location.city` | object \| null | The city information of the company |
| `location.address` | string \| null | The address of the company |
| `location.postal_code` | string \| null | The postal code of the company |
| `location.phone` | string \| null | The phone number of the company |
| `financial` | object \| null | The financial information of the company |
| `financial.stock_symbol` | string \| null | The stock symbol |
| `financial.stock_exchange` | string \| null | The stock exchange |
| `financial.total_funding` | int64 \| null | The total funding amount |
| `financial.funding_stage` | string \| null | The funding stage |
| `financial.funding_date` | date-time \| null | The funding date |
| `financial.funding` | array of objects \| null | The funding rounds |
| `socials` | object | The social URLs of the company |
| `socials.linkedin_url` | uri \| null | The LinkedIn URL of the company |
| `socials.linkedin_id` | string \| null | The LinkedIn ID of the company |
| `socials.twitter_url` | uri \| null | The Twitter URL of the company |
| `socials.facebook_url` | uri \| null | The Facebook URL of the company |
| `socials.instagram_url` | uri \| null | The Instagram URL of the company |
| `socials.angellist_url` | uri \| null | The AngelList URL of the company |
| `socials.crunchbase_url` | uri \| null | The Crunchbase URL of the company |
| `socials.youtube_url` | uri \| null | The YouTube URL of the company |
| `socials.g2_url` | uri \| null | The G2 URL of the company |
| `page_rank` | float \| null | The page rank of the company |
| `logo_url` | string \| null | The logo URL of the company |
| `seo_description` | string \| null | The SEO description of the company |
| `updated_at` | date-time | The last updated timestamp of the company |

### Error Responses

| Status | Description |
|--------|-------------|
| 400 | Bad Request |
| 401 | Unauthorized |
| 402 | Payment Required |
| 404 | Not Found |
| 422 | Unprocessable Entity |
| 429 | Too Many Requests |

## Example Request

```bash
curl --request POST \
     --url https://api.companyenrich.com/companies/enrich \
     --header 'Authorization: Bearer <YOURTOKEN>' \
     --header 'accept: application/json' \
     --header 'content-type: application/json' \
     --data '{
       "name": "Acme Inc",
       "linkedinUrl": "https://linkedin.com/company/acme"
     }'
```

## Example Response

```json
{
  "id": "uuid",
  "name": "string",
  "domain": "string",
  "website": "string",
  "type": "string",
  "industry": "string",
  "industries": ["string"],
  "categories": [],
  "employees": "string",
  "revenue": "string",
  "description": "string",
  "keywords": ["string"],
  "technologies": ["string"],
  "subsidiaries": ["string"],
  "founded_year": 0,
  "naics_codes": ["string"],
  "location": {
    "country": {
      "name": "string",
      "latitude": 0,
      "longitude": 0
    },
    "state": {
      "id": 0,
      "name": "string",
      "code": "string",
      "latitude": 0,
      "longitude": 0
    },
    "city": {
      "id": 0,
      "name": "string",
      "latitude": 0,
      "longitude": 0
    },
    "address": "string",
    "postal_code": "string",
    "phone": "string"
  },
  "financial": {
    "stock_symbol": "string",
    "stock_exchange": "string",
    "total_funding": 0,
    "funding_stage": "string",
    "funding_date": "2026-01-25T08:57:01.037Z",
    "funding": [
      {
        "date": "2026-01-25T08:57:01.037Z",
        "amount": "string",
        "type": "string",
        "url": "string",
        "from": "string"
      }
    ]
  },
  "socials": {
    "linkedin_url": "string",
    "linkedin_id": "string",
    "twitter_url": "string",
    "facebook_url": "string",
    "instagram_url": "string",
    "angellist_url": "string",
    "crunchbase_url": "string",
    "youtube_url": "string",
    "g2_url": "string"
  },
  "page_rank": 0,
  "logo_url": "string",
  "seo_description": "string",
  "updated_at": "2026-01-25T08:57:01.037Z"
}
