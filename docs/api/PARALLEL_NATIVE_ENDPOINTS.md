# Parallel Native Endpoints

All endpoints use Parallel AI Task API and write directly to the database.

**Base URL:** `https://api.revenueinfra.com/run`

**Parallel AI Task API:** `https://api.parallel.ai/v1/tasks/runs`

---

## 1. Description

**Endpoint:** `POST /companies/parallel-native/description/infer/db-direct`

**Payload:**
```json
{
  "domain": "ramp.com",
  "company_name": "Ramp",
  "company_linkedin_url": "linkedin.com/company/ramp",
  "ttl_days": null
}
```

**Full request sent to Parallel AI:**
```json
{
  "input": {
    "domain": "ramp.com",
    "company_name": "Ramp",
    "company_linkedin_url": "linkedin.com/company/ramp"
  },
  "processor": "core",
  "task_spec": {
    "output_schema": {
      "type": "object",
      "properties": {
        "description": {
          "type": "string",
          "description": "A 2-3 sentence description of what the company does, who they serve, and their primary value proposition."
        },
        "tagline": {
          "type": "string",
          "description": "A short one-line tagline or slogan for the company."
        }
      },
      "required": ["description"]
    },
    "input_schema": {
      "type": "object",
      "properties": {
        "domain": {"type": "string", "description": "Company website domain"},
        "company_name": {"type": "string", "description": "Company name"},
        "company_linkedin_url": {"type": "string", "description": "Company LinkedIn URL"}
      }
    }
  }
}
```

**Writes to:** `core.company_descriptions`

---

## 2. Revenue

**Endpoint:** `POST /companies/parallel-native/revenue/infer/db-direct`

**Payload:**
```json
{
  "domain": "ramp.com",
  "company_name": "Ramp",
  "company_linkedin_url": "linkedin.com/company/ramp"
}
```

**Full request sent to Parallel AI:**
```json
{
  "input": {
    "domain": "ramp.com",
    "company_name": "Ramp",
    "company_linkedin_url": "linkedin.com/company/ramp"
  },
  "processor": "core",
  "task_spec": {
    "output_schema": {
      "type": "object",
      "properties": {
        "annual_revenue_usd": {
          "type": "integer",
          "description": "Estimated annual revenue in USD (e.g., 50000000 for $50M)"
        },
        "revenue_range": {
          "type": "string",
          "description": "Revenue range if exact not available (e.g., '$10M - $50M')"
        },
        "confidence": {
          "type": "string",
          "enum": ["high", "medium", "low"],
          "description": "Confidence level in the estimate"
        }
      },
      "required": ["confidence"]
    },
    "input_schema": {
      "type": "object",
      "properties": {
        "domain": {"type": "string", "description": "Company website domain"},
        "company_name": {"type": "string", "description": "Company name"},
        "company_linkedin_url": {"type": "string", "description": "Company LinkedIn URL"}
      }
    }
  }
}
```

**Writes to:** `core.company_revenue`

---

## 3. Funding

**Endpoint:** `POST /companies/parallel-native/funding/infer/db-direct`

**Payload:**
```json
{
  "domain": "ramp.com",
  "company_name": "Ramp",
  "company_linkedin_url": "linkedin.com/company/ramp"
}
```

**Full request sent to Parallel AI:**
```json
{
  "input": {
    "domain": "ramp.com",
    "company_name": "Ramp",
    "company_linkedin_url": "linkedin.com/company/ramp"
  },
  "processor": "core",
  "task_spec": {
    "output_schema": {
      "type": "object",
      "properties": {
        "total_funding_usd": {
          "type": "integer",
          "description": "Total funding raised in USD (e.g., 150000000 for $150M)"
        },
        "funding_range": {
          "type": "string",
          "description": "Funding range if exact not available (e.g., '$100M - $250M')"
        },
        "confidence": {
          "type": "string",
          "enum": ["high", "medium", "low"],
          "description": "Confidence level in the estimate"
        }
      },
      "required": ["confidence"]
    },
    "input_schema": {
      "type": "object",
      "properties": {
        "domain": {"type": "string", "description": "Company website domain"},
        "company_name": {"type": "string", "description": "Company name"},
        "company_linkedin_url": {"type": "string", "description": "Company LinkedIn URL"}
      }
    }
  }
}
```

**Writes to:** `core.company_funding`

---

## 4. Last Funding Date

**Endpoint:** `POST /companies/parallel-native/last-funding-date/infer/db-direct`

**Payload:**
```json
{
  "domain": "ramp.com",
  "company_name": "Ramp",
  "company_linkedin_url": "linkedin.com/company/ramp"
}
```

**Full request sent to Parallel AI:**
```json
{
  "input": {
    "domain": "ramp.com",
    "company_name": "Ramp",
    "company_linkedin_url": "linkedin.com/company/ramp"
  },
  "processor": "core",
  "task_spec": {
    "output_schema": {
      "type": "object",
      "properties": {
        "last_funding_date": {
          "type": "string",
          "description": "Date of most recent funding round in YYYY-MM-DD format"
        },
        "funding_type": {
          "type": "string",
          "description": "Type of most recent funding (e.g., 'Series B', 'Seed')"
        },
        "confidence": {
          "type": "string",
          "enum": ["high", "medium", "low"],
          "description": "Confidence level in the estimate"
        }
      },
      "required": ["confidence"]
    },
    "input_schema": {
      "type": "object",
      "properties": {
        "domain": {"type": "string", "description": "Company website domain"},
        "company_name": {"type": "string", "description": "Company name"},
        "company_linkedin_url": {"type": "string", "description": "Company LinkedIn URL"}
      }
    }
  }
}
```

**Writes to:** `core.company_last_funding_date`

---

## 5. Employees

**Endpoint:** `POST /companies/parallel-native/employees/infer/db-direct`

**Payload:**
```json
{
  "domain": "ramp.com",
  "company_name": "Ramp",
  "company_linkedin_url": "linkedin.com/company/ramp"
}
```

**Full request sent to Parallel AI:**
```json
{
  "input": {
    "domain": "ramp.com",
    "company_name": "Ramp",
    "company_linkedin_url": "linkedin.com/company/ramp"
  },
  "processor": "core",
  "task_spec": {
    "output_schema": {
      "type": "object",
      "properties": {
        "employee_count": {
          "type": "integer",
          "description": "Estimated number of employees (e.g., 500)"
        },
        "employee_range": {
          "type": "string",
          "description": "Employee range (e.g., '501-1000', '1001-5000')"
        },
        "confidence": {
          "type": "string",
          "enum": ["high", "medium", "low"],
          "description": "Confidence level in the estimate"
        }
      },
      "required": ["confidence"]
    },
    "input_schema": {
      "type": "object",
      "properties": {
        "domain": {"type": "string", "description": "Company website domain"},
        "company_name": {"type": "string", "description": "Company name"},
        "company_linkedin_url": {"type": "string", "description": "Company LinkedIn URL"}
      }
    }
  }
}
```

**Writes to:** `core.company_employees`

---

## 6. G2 URL

**Endpoint:** `POST /companies/parallel-native/g2-url/infer/db-direct`

**Payload:**
```json
{
  "domain": "ramp.com",
  "company_name": "Ramp"
}
```

**Writes to:** `core.company_g2_url`

---

## 7. Case Study Extract (v2)

**Endpoint:** `POST /parallel-native/case-study/extract-v2`

**Payload:**
```json
{
  "case_study_url": "https://example.com/case-study",
  "origin_company_domain": "vendor.com"
}
```

**Returns:** Customer company name, domain, champions, testimonials

---

## Notes

- The `description` fields in output_schema act as the "prompt" - they tell Parallel AI what to return
- All endpoints check for existing data before calling Parallel AI (to save API costs)
- Endpoints poll for task completion (async)
- `company_linkedin_url` is optional but improves accuracy
- `processor: "core"` uses Parallel's standard enrichment processor
