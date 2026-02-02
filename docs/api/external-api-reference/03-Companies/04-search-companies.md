# Search companies

`POST` `https://api.companyenrich.com/companies/search`

**Cost:** 1 credit per company returned. 1 credit minimum if no results are found.

> **Notice:** Up to 10,000 results can be returned from this endpoint (page * pageSize cannot exceed 10,000). If you need more results, please use the scroll endpoint.

Searches companies based on given criteria. You can search by name, domain, industry, employees, revenue, founded year, and more. At most 100 companies are returned per request. If you need more results, please use the pagination parameters.

## Body Params

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int32 | The page number to return. Must be greater than 0 |
| `pageSize` | int32 | The number of results to return in each page. Must be between 1 and 100 |
| `lists` | array of uuids \| null | The list IDs to filter by |
| `semanticQuery` | string \| null | The semantic search query to find companies with. More natural language version of the standard query |
| `semanticWeight` | double \| null | The semantic weight to apply to the results. Must be between 0 and 1. 0.7 is default. Larger values will prioritize semantic similarity, smaller values will prioritize traditional search factors |
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
| `items` | array of objects | **Required.** The items in the list |
| `items[].id` | uuid | **Required.** The unique identifier of the company |
| `items[].name` | string \| null | The name of the company |
| `items[].domain` | string \| null | The primary domain name of the company |
| `items[].website` | uri \| null | The website URL of the company |
| `items[].type` | enum | The type of the company |
| `items[].industry` | string \| null | The main industry of the company |
| `items[].industries` | array of strings \| null | The industries associated with the company |
| `items[].categories` | array \| null | The categories of the company from most to least specific |
| `items[].employees` | enum | The range of number of employees of the company |
| `items[].revenue` | enum | The range of annual revenue of the company in USD |
| `items[].description` | string \| null | The description of the company |
| `items[].keywords` | array of strings \| null | The search keywords of the company |
| `items[].technologies` | array of strings \| null | The technologies associated with the company |
| `items[].subsidiaries` | array of strings \| null | The subsidiaries associated with the company |
| `items[].founded_year` | int32 \| null | The year the company was founded |
| `items[].naics_codes` | array of strings \| null | The NAICS codes associated with the company |
| `items[].location` | object \| null | The location information of the company |
| `items[].financial` | object \| null | The financial information of the company |
| `items[].socials` | object | The social URLs of the company |
| `items[].page_rank` | float \| null | The page rank of the company |
| `items[].logo_url` | string \| null | The logo URL of the company |
| `items[].seo_description` | string \| null | The SEO description of the company |
| `items[].updated_at` | date-time | The last updated timestamp of the company |
| `page` | int32 | The current page number. 1-indexed |
| `totalPages` | int32 | The total number of pages |
| `totalItems` | int32 | The total number of items in the list |

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
     --url https://api.companyenrich.com/companies/search \
     --header 'Authorization: Bearer <YOURTOKEN>' \
     --header 'accept: application/json' \
     --header 'content-type: application/json' \
     --data '{
       "page": 1,
       "pageSize": 10,
       "query": "software",
       "employees": ["11-50", "51-200"],
       "countries": ["US"]
     }'
```

## Example Response

```json
{
  "items": [
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
  ],
  "page": 1,
  "totalPages": 10,
  "totalItems": 100
}
