# Count similar companies

`POST` `https://api.companyenrich.com/companies/similar/count`

**Cost:** FREE - No credits deducted

Returns the total count of similar companies matching the given search criteria without retrieving the actual results.

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

Returns the count of matching similar companies.

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
     --url https://api.companyenrich.com/companies/similar/count \
     --header 'Authorization: Bearer <YOURTOKEN>' \
     --header 'accept: application/json' \
     --header 'content-type: application/json' \
     --data '{
       "domains": ["stripe.com"],
       "similarityWeight": 0.5,
       "countries": ["US"]
     }'
```

## Example Response

```json
{
  "count": 567
}
```