# Find similar companies (preview)

`POST` `https://api.companyenrich.com/companies/similar/preview`

**Cost:** FREE - No credits deducted

**Requirements:** Requires Scale plans

> **Notice:** Returns top 25 results only

Preview search for similar companies based on given criteria. You can search by domain, industry, employees, revenue, founded year, and more. This endpoint returns the top 25 similar companies for free, perfect for previewing results before running a full similar search.

## Body Params

| Parameter | Type | Description |
|-----------|------|-------------|
| `domains` | array of strings | The domains to find similar companies for. Up to 10 domains are allowed. Length between 1 and 10 |
| `similarityWeight` | double | The similarity weight to apply to the results. Must be between -1 and 1. 0 is default. Larger values will prioritize more similar companies, smaller values will prioritize more established companies |
| `exclude` | object \| null | Exclusion filters to apply on the companies. If a company matches any of the filters here, it will be excluded from the results |
| `query` | string \| null | The search query to apply on the company name and domain |
| `foundedYear` | object \| null | Founded year min and max values to filter by |
| `fundingAmount` | object \| null | The funding amount range to filter by |
| `fundingYear` | object \| null | The range of funding years |
| `categoryOperator` | enum | The operator to apply on the category filters. Defaults to And. Allowed: `And`, `Or`, `null` |
| `keywordsOperator` | enum | The operator to apply on the keywords filters. Defaults to And. Allowed: `And`, `Or`, `null` |
| `technologiesOperator` | enum | The operator to apply on the technologies filters. Defaults to And. Allowed: `And`, `Or`, `null` |
| `require` | array \| null | The features that must exist for the company |
| `regions` | array of strings \| null | The region IDs to filter by |
| `countries` | array of strings \| null | The 2 letter country codes to filter by |
| `states` | array of int32s \| null | The state IDs to filter by |
| `cities` | array of int32s \| null | The city IDs to filter by |
| `type` | array \| null | The list of company types to filter by |
| `category` | array \| null | The list of company categories to filter by |
| `employees` | array \| null | The list of employee counts to filter by |
| `revenue` | array \| null | The list of revenue ranges to filter by |
| `naicsCode` | array of int32s \| null | The NAICS codes to filter by. Can be 2 to 6 digit codes. In case of a 2-5 digit code, all 6 digit codes under it will be included |
| `keywords` | array of strings \| null | The keywords to filter by |
| `technologies` | array of strings \| null | The technologies to filter by |
| `fundingRounds` | array \| null | The funding rounds to filter by |

## Responses

### 200 OK

#### Response Body

| Field | Type | Description |
|-------|------|-------------|
| `items` | array of objects | The list of similar companies |
| `items[].id` | uuid | The unique identifier of the company |
| `items[].name` | string | The name of the company |
| `items[].domain` | string | The primary domain name of the company |
| `items[].website` | string | The website URL of the company |
| `items[].industry` | string | The main industry of the company |
| `items[].description` | string | The description of the company |
| `items[].keywords` | array of strings | The search keywords of the company |
| `items[].logo_url` | string | The logo URL of the company |
| `items[].updated_at` | date-time | The last updated timestamp of the company |
| `metadata` | object | Metadata about the results |
| `metadata.scores` | object | Similarity scores for each company |
| `page` | int32 | The current page number |
| `totalPages` | int32 | The total number of pages |
| `totalItems` | int32 | The total number of items |

### 401 Unauthorized

| Field | Type | Description |
|-------|------|-------------|
| `type` | string \| null | Error type |
| `title` | string \| null | Error title |
| `status` | int32 \| null | HTTP status code |
| `detail` | string \| null | Error details |
| `instance` | string \| null | Error instance |

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
     --url https://api.companyenrich.com/companies/similar/preview \
     --header 'Authorization: Bearer <YOURTOKEN>' \
     --header 'accept: application/json' \
     --header 'content-type: application/json' \
     --data '{
       "domains": ["stripe.com"],
       "similarityWeight": 0.5
     }'
```

## Example Response

```json
{
  "items": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "string",
      "domain": "string",
      "website": "string",
      "industry": "string",
      "description": "string",
      "keywords": [
        "string"
      ],
      "logo_url": "string",
      "updated_at": "2026-01-25T08:57:01.037Z"
    }
  ],
  "metadata": {
    "scores": {
      "additionalProp": 0
    }
  },
  "page": 0,
  "totalPages": 0,
  "totalItems": 0
}
```