# Batch enrich by domains

`POST` `https://api.companyenrich.com/companies/enrich/batch`

**Cost:** 1 credit per domain enriched

Enriches a list of companies using their domain names. Up to 50 domains can be provided in a single request.

We map each domain to a unique company so lookups via domain are fast and reliable. It is the preferred way to enrich a company.

Batching is recommended for larger lists of domains. It allows you to enrich multiple companies in a single request. Eliminating the need to make multiple requests to the API. Also the rate limiter would be able to handle more requests.

## Body Params

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `domains` | array of strings | Yes | A list of domains to enrich. Up to 50 domains can be provided in a single request. Length between 1 and 50. |

## Responses

### 200 OK

#### Response Body

Returns an array of company objects.

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
| `financial` | object \| null | The financial information of the company |
| `socials` | object | The social URLs of the company |
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
| 422 | Unprocessable Entity |
| 429 | Too Many Requests |

## Example Request

```bash
curl --request POST \
     --url https://api.companyenrich.com/companies/enrich/batch \
     --header 'Authorization: Bearer <YOURTOKEN>' \
     --header 'accept: application/json' \
     --header 'content-type: application/json' \
     --data '{
       "domains": ["example.com", "acme.com", "company.io"]
     }'
```

## Example Response

```json
[
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
]
