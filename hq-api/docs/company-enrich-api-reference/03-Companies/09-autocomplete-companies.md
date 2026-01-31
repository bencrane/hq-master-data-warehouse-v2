# Autocomplete companies

`GET` `https://api.companyenrich.com/companies/autocomplete`

**Cost:** FREE - No credits deducted

Returns a list of companies matching the given partial domain name. This is useful for autocompleting domain names in your application. Up to 10 companies are returned per request.

## Query Params

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | The query to autocomplete |

## Responses

### 200 OK

#### Response Body

Returns an array of company objects.

| Field | Type | Description |
|-------|------|-------------|
| `domain` | string | The domain name of the company |
| `name` | string | The name of the company |
| `logoUrl` | string | The logo URL of the company |

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
curl --request GET \
     --url 'https://api.companyenrich.com/companies/autocomplete?query=strip' \
     --header 'Authorization: Bearer <YOURTOKEN>' \
     --header 'accept: application/json'
```

## Example Response

```json
[
  {
    "domain": "string",
    "name": "string",
    "logoUrl": "string"
  }
]
```