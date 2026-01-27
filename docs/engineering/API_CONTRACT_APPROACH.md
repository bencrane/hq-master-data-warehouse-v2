# API Contract Approach: The Stripe Method

This document explains how professional engineering teams (Stripe, GitHub, Twilio) handle API contracts between backend and frontend, and how we implement this approach in this project.

---

## The Problem with Manual Documentation

Most teams do this:

1. Backend developer writes an endpoint
2. Backend developer writes documentation in a markdown file or wiki
3. Frontend developer reads the docs and writes TypeScript types by hand
4. API changes, docs don't get updated
5. Frontend types drift from reality
6. Bugs, confusion, wasted time

**This is amateur hour.**

The documentation becomes a lie. The types become a lie. Nobody trusts anything, so everyone reads the source code anyway.

---

## The Stripe Approach

Stripe is famous for having the best API documentation in the industry. Here's how they actually do it:

### 1. OpenAPI Specification is the Source of Truth

The API is defined in a machine-readable schema file (OpenAPI 3.x, formerly Swagger). This is not documentation - it IS the API contract.

```yaml
# This is not prose. This is a specification.
paths:
  /v1/customers:
    get:
      summary: List all customers
      parameters:
        - name: limit
          in: query
          schema:
            type: integer
            maximum: 100
      responses:
        200:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CustomerList'
```

### 2. Documentation is Generated, Not Written

Stripe's beautiful API docs at stripe.com/docs/api are **generated from the OpenAPI spec**. Humans don't write the parameter tables or response examples - machines do.

Benefits:
- Docs can never drift from reality
- Every endpoint is documented automatically
- Examples are generated from actual schemas

### 3. Client SDKs are Generated, Not Written

Stripe's Python, Ruby, Node, Go, and Java SDKs are **generated from the OpenAPI spec**. The TypeScript types in `stripe-node` are not hand-written - they're produced by a code generator.

```bash
# Stripe's internal process (simplified)
openapi-generator generate -i stripe-api.yaml -g typescript-node -o stripe-node/
```

Benefits:
- Type safety guaranteed
- All languages stay in sync
- New endpoints automatically appear in all SDKs

### 4. Contract-First Development

At Stripe, the workflow is:

1. **Design the API contract** (OpenAPI spec) - reviewed by frontend, backend, and API design team
2. **Generate types and mocks** - frontend can start building immediately
3. **Implement backend** - must conform to the spec
4. **Implement frontend** - uses generated types
5. **CI validates** - tests ensure implementation matches spec

Frontend and backend work **in parallel** against the contract, not against each other.

---

## How We Implement This

### Our Stack

| Component | Tool |
|-----------|------|
| API Framework | FastAPI (auto-generates OpenAPI) |
| OpenAPI Spec | `/openapi.json` endpoint |
| Type Generator | `openapi-typescript` |
| Frontend Types | `frontend/api/types.ts` |

### The Files

```
frontend/
├── api/
│   ├── openapi.json    # Downloaded from API (source of truth)
│   └── types.ts        # Auto-generated TypeScript types
```

### The Workflow

**When building frontend features:**
```tsx
// Import types - never write them by hand
import type { components, operations } from '@/api/types';

type Lead = components['schemas']['Lead'];
type LeadsResponse = components['schemas']['LeadsResponse'];

// TypeScript now knows the exact shape of API responses
const response: LeadsResponse = await fetch('/api/leads').then(r => r.json());
response.data.forEach(lead => {
  console.log(lead.full_name);  // TypeScript knows this exists
  console.log(lead.foo);         // TypeScript ERROR: 'foo' doesn't exist
});
```

**When the API changes:**
```bash
# Regenerate types (run from frontend/)
curl -s "https://hq-master-data-api-production.up.railway.app/openapi.json" > api/openapi.json
npx openapi-typescript api/openapi.json -o api/types.ts

# Now TypeScript will show errors wherever code doesn't match the new API
```

**When adding a new endpoint:**
1. Add the endpoint to FastAPI (backend)
2. Deploy
3. Regenerate types
4. Frontend gets the new types automatically

---

## What This Means for Frontend Development

### DO:
- Import types from `@/api/types`
- Regenerate types when you see API mismatches
- Trust the types - they're generated from the actual API

### DO NOT:
- Write API types by hand
- Create interfaces that duplicate what's in `types.ts`
- Ignore TypeScript errors about API responses

### Example: Building a Leads Hook

```tsx
// hooks/useLeads.ts
import useSWR from 'swr';
import type { components } from '@/api/types';

type Lead = components['schemas']['Lead'];
type LeadsResponse = components['schemas']['LeadsResponse'];

const API_BASE = 'https://hq-master-data-api-production.up.railway.app';

export function useLeads(params: {
  job_function?: string;
  seniority?: string;
  limit?: number;
  offset?: number;
}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) searchParams.set(key, String(value));
  });

  const { data, error, isLoading } = useSWR<LeadsResponse>(
    `${API_BASE}/api/leads?${searchParams}`,
    (url) => fetch(url).then(r => r.json())
  );

  return {
    leads: data?.data ?? [],
    total: data?.meta?.total ?? 0,
    isLoading,
    error,
  };
}
```

The `LeadsResponse` type is generated. It knows exactly what `data` and `meta` contain. If the API changes, regenerating types will cause TypeScript errors that tell you exactly what to fix.

---

## Why This Matters

### Without this approach:
- "Is this field nullable?" - check the backend code
- "Did they add a new field?" - check the backend code
- "Why is this undefined?" - the docs lied, check the backend code

### With this approach:
- "Is this field nullable?" - hover over it in VS Code, the type tells you
- "Did they add a new field?" - regenerate types, it appears automatically
- "Why is this undefined?" - TypeScript would have caught this at compile time

---

## Commands Reference

```bash
# Fetch latest OpenAPI spec
curl -s "https://hq-master-data-api-production.up.railway.app/openapi.json" > frontend/api/openapi.json

# Generate TypeScript types
cd frontend && npx openapi-typescript api/openapi.json -o api/types.ts

# One-liner to update everything
curl -s "https://hq-master-data-api-production.up.railway.app/openapi.json" > frontend/api/openapi.json && npx openapi-typescript frontend/api/openapi.json -o frontend/api/types.ts
```

---

## Further Reading

- [Stripe API Design](https://stripe.com/docs/api) - study the structure
- [OpenAPI Specification](https://spec.openapis.org/oas/latest.html)
- [openapi-typescript](https://github.com/drwpow/openapi-typescript) - the generator we use
- [FastAPI Auto-docs](https://fastapi.tiangolo.com/features/#automatic-docs) - how our backend generates the spec
