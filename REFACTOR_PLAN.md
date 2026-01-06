# Monorepo Refactor Plan

## Target Architecture

```
hq-master-data-warehouse-v2/
├── apps/
│   ├── admin/         # Admin frontend (UI only, no direct Supabase queries)
│   ├── client/        # Client dashboard (UI only, no direct Supabase queries)
│   └── api/           # API-only Next.js app (all database queries live here)
├── packages/
│   └── shared/        # Shared types, constants, utilities
```

---

## Current State Analysis

### Files with Direct Supabase Queries

| File | Functions | Schema | Table |
|------|-----------|--------|-------|
| `frontend/app/actions/get-leads.ts` | `getLeads()` | `clients` | `target_client_leads` |
| `frontend/app/actions/get-target-clients.ts` | `getTargetClients()` | `reference` | `target_clients` |
| `frontend/app/actions/upload-target-clients.ts` | `uploadTargetClients()` | `reference` | `target_clients` |
| `frontend/app/actions/generate-icp.ts` | `generateICPForClients()` | N/A | External Modal endpoint |
| `frontend/lib/supabase.ts` | Client init | — | — |
| `client/app/page.tsx` | `getClients()` | `reference` | `target_clients` |
| `client/app/[slug]/page.tsx` | `getClientBySlug()`, `getLeadsForClient()` | `reference`, `clients` | `target_clients`, `target_client_leads` |
| `client/lib/supabase.ts` | Client init | — | — |

---

## 1. Stages

### Stage 1: Monorepo Scaffolding
**What changes:** Set up workspace structure, move nothing yet.

**Files created:**
```
/pnpm-workspace.yaml
/package.json (root workspace)
/turbo.json
/apps/.gitkeep
/packages/.gitkeep
/packages/shared/package.json
/packages/shared/tsconfig.json
/packages/shared/src/index.ts
```

**`pnpm-workspace.yaml`:**
```yaml
packages:
  - 'apps/*'
  - 'packages/*'
```

**`turbo.json`:**
```json
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": [".next/**", "dist/**"]
    },
    "dev": {
      "dependsOn": ["^build"],
      "cache": false,
      "persistent": true
    },
    "lint": {
      "dependsOn": ["^build"]
    },
    "typecheck": {
      "dependsOn": ["^build"]
    }
  }
}
```

> **Note:** The `"dependsOn": ["^build"]` ensures `@bullseye/shared` is built before any app that depends on it. This is critical since the shared package uses `src/` with TypeScript compilation.

**Success criteria:**
- `pnpm install` runs from root without errors
- Workspace packages are recognized: `pnpm ls -r` shows packages
- `turbo build` respects dependency order (shared builds first)

---

### Stage 2: Create Shared Package
**What changes:** Create `/packages/shared` with all shared types, constants, and utilities.

**Files created:**
```
/packages/shared/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts              # Re-exports everything
│   ├── types/
│   │   ├── index.ts
│   │   ├── target-client.ts
│   │   ├── lead.ts
│   │   ├── icp.ts
│   │   └── api-responses.ts
│   ├── constants/
│   │   └── index.ts
│   └── utils/
│       └── index.ts
```

**`packages/shared/package.json`:**
```json
{
  "name": "@bullseye/shared",
  "version": "0.0.1",
  "private": true,
  "main": "./dist/index.js",
  "module": "./dist/index.mjs",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "import": "./dist/index.mjs",
      "require": "./dist/index.js",
      "types": "./dist/index.d.ts"
    }
  },
  "scripts": {
    "build": "tsup src/index.ts --format cjs,esm --dts --clean",
    "dev": "tsup src/index.ts --format cjs,esm --dts --watch",
    "typecheck": "tsc --noEmit"
  },
  "devDependencies": {
    "tsup": "^8.0.0",
    "typescript": "^5"
  },
  "dependencies": {
    "clsx": "^2.1.1",
    "tailwind-merge": "^3.4.0"
  }
}
```

**`packages/shared/tsconfig.json`:**
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "declaration": true,
    "declarationMap": true,
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

**Files migrated:**
- `frontend/types/index.ts` → `packages/shared/src/types/target-client.ts`, `packages/shared/src/types/lead.ts`
- `frontend/lib/utils.ts` → `packages/shared/src/utils/index.ts`

**Success criteria:**
- `pnpm build --filter=@bullseye/shared` produces `dist/` with `.js`, `.mjs`, and `.d.ts` files
- Can import `@bullseye/shared` in a test file
- TypeScript compiles without errors
- Turborepo builds shared package before dependent apps

---

### Stage 3: Create API App
**What changes:** Create `/apps/api` with all API routes. No existing apps are modified yet.

**Files created:**
```
/apps/api/
├── package.json
├── tsconfig.json
├── next.config.ts
├── middleware.ts                 # CORS middleware
├── .env.local.example
├── app/
│   ├── layout.tsx            # Minimal, no UI
│   ├── api/
│   │   ├── health/
│   │   │   └── route.ts
│   │   ├── target-clients/
│   │   │   ├── route.ts          # GET all, POST create
│   │   │   └── [id]/
│   │   │       └── route.ts      # GET by ID
│   │   ├── target-clients/
│   │   │   └── by-slug/
│   │   │       └── [slug]/
│   │   │           └── route.ts  # GET by slug, supports ?include=leads,icp
│   │   ├── leads/
│   │   │   └── [clientId]/
│   │   │       └── route.ts      # GET leads for client, supports ?include_icp=true
│   │   ├── icp/
│   │   │   ├── route.ts          # POST generate ICP
│   │   │   └── [clientId]/
│   │   │       └── route.ts      # GET ICP for client
│   │   └── customer-companies/
│   │       └── [clientId]/
│   │           └── route.ts      # GET/POST customer companies
│   └── lib/
│       ├── supabase.ts           # Server-side Supabase client
│       └── cors.ts               # CORS helper utilities
```

**CORS Middleware (`middleware.ts`):**
```typescript
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const allowedOrigins = process.env.ALLOWED_ORIGINS?.split(',') || [];

export function middleware(request: NextRequest) {
  const origin = request.headers.get('origin') || '';
  const isAllowed = allowedOrigins.includes(origin) || origin.startsWith('http://localhost');

  // Handle preflight
  if (request.method === 'OPTIONS') {
    return new NextResponse(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': isAllowed ? origin : '',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Max-Age': '86400',
      },
    });
  }

  const response = NextResponse.next();
  if (isAllowed) {
    response.headers.set('Access-Control-Allow-Origin', origin);
  }
  return response;
}

export const config = {
  matcher: '/api/:path*',
};
```

**Success criteria:**
- `pnpm dev --filter=api` starts on port 3001
- `GET /api/health` returns `{ status: "ok" }`
- `GET /api/target-clients` returns data from Supabase
- All endpoints return correct data (tested via curl)
- CORS preflight (`OPTIONS`) returns 204 with correct headers
- Cross-origin requests from localhost:4500 succeed

---

### Stage 4: Move Admin App
**What changes:** Move `/frontend` to `/apps/admin`. Update imports but keep Supabase queries temporarily.

**Files moved:**
```
/frontend/* → /apps/admin/*
```

**Files modified:**
- `/apps/admin/package.json` — name changed to `@bullseye/admin`, add `@bullseye/shared` as dependency
- `/apps/admin/tsconfig.json` — update paths
- All imports of `@/types` → `@bullseye/shared`
- Delete `/apps/admin/types/index.ts`

**Success criteria:**
- `pnpm dev --filter=admin` starts on port 4500
- All pages render correctly
- No TypeScript errors

---

### Stage 5: Move Client App
**What changes:** Move `/client` to `/apps/client`. Update imports but keep Supabase queries temporarily.

**Files moved:**
```
/client/* → /apps/client/*
```

**Files modified:**
- `/apps/client/package.json` — name changed to `@bullseye/client`, add `@bullseye/shared` as dependency
- `/apps/client/tsconfig.json` — update paths

**Success criteria:**
- `pnpm dev --filter=client` starts on port 3000
- Homepage lists clients correctly
- `/[slug]` pages render correctly

---

### Stage 6: Refactor Admin to Use API
**What changes:** Replace all direct Supabase queries in admin with fetch calls to API.

**Files modified:**
```
/apps/admin/app/actions/get-leads.ts         → fetch to API
/apps/admin/app/actions/get-target-clients.ts → fetch to API
/apps/admin/app/actions/upload-target-clients.ts → fetch POST to API
/apps/admin/app/actions/generate-icp.ts      → fetch POST to API
```

**Files deleted:**
```
/apps/admin/lib/supabase.ts
```

**Files created:**
```
/apps/admin/lib/api.ts                       # API base URL, fetch helpers
```

**Success criteria:**
- Remove `@supabase/supabase-js` from admin's package.json
- All pages still work when API is running
- `pnpm build --filter=admin` succeeds without Supabase imports

---

### Stage 7: Refactor Client to Use API
**What changes:** Replace all direct Supabase queries in client with fetch calls to API.

**Files modified:**
```
/apps/client/app/page.tsx                    → fetch GET /api/target-clients
/apps/client/app/[slug]/page.tsx             → fetch GET /api/target-clients/by-slug/[slug]?include=leads,icp
```

> **Key optimization:** The `[slug]/page.tsx` previously made 2 sequential Supabase queries. Now it makes 1 API call using the batch endpoint, reducing latency.

**Files deleted:**
```
/apps/client/lib/supabase.ts
```

**Files created:**
```
/apps/client/lib/api.ts                      # API base URL, fetch helpers
```

**Success criteria:**
- Remove `@supabase/supabase-js` from client's package.json
- All pages still work when API is running
- `pnpm build --filter=client` succeeds without Supabase imports
- `/[slug]` page loads with single API call (verify in Network tab)

---

### Stage 8: Cleanup and Finalization
**What changes:** Remove old directories, update documentation, add deployment configs.

**Files deleted:**
```
/frontend/  (was moved)
/client/    (was moved)
```

**Files created:**
```
/apps/api/vercel.json
/apps/admin/vercel.json
/apps/client/vercel.json
/README.md (updated)
```

**Success criteria:**
- `pnpm build` from root builds all three apps
- All apps deploy successfully to Vercel
- No orphaned files in root

---

## 2. API Endpoints Specification

### Health Check
| Property | Value |
|----------|-------|
| **Route** | `GET /api/health` |
| **Input** | None |
| **Response** | `{ status: "ok", timestamp: string }` |
| **Tables** | None |

---

### Target Clients

#### List All Target Clients
| Property | Value |
|----------|-------|
| **Route** | `GET /api/target-clients` |
| **Input** | Query params: `?limit=number&offset=number` |
| **Response** | `{ data: TargetClient[], count: number }` |
| **Tables** | `reference.target_clients` |

#### Create Target Client(s)
| Property | Value |
|----------|-------|
| **Route** | `POST /api/target-clients` |
| **Input** | Body: `{ clients: TargetClientInput[] }` |
| **Response** | `{ success: boolean, inserted: number, errors: string[] }` |
| **Tables** | `reference.target_clients` (INSERT) |

#### Get Target Client by ID
| Property | Value |
|----------|-------|
| **Route** | `GET /api/target-clients/[id]` |
| **Input** | Path param: `id` (UUID) |
| **Response** | `{ data: TargetClient \| null }` |
| **Tables** | `reference.target_clients` |

#### Get Target Client by Slug
| Property | Value |
|----------|-------|
| **Route** | `GET /api/target-clients/by-slug/[slug]` |
| **Input** | Path param: `slug` (string) |
| **Response** | `{ data: TargetClient \| null }` |
| **Tables** | `reference.target_clients` |

#### Get Target Client by Slug (with includes) ⭐ Batch Endpoint
| Property | Value |
|----------|-------|
| **Route** | `GET /api/target-clients/by-slug/[slug]?include=leads,icp` |
| **Input** | Path param: `slug` (string), Query: `?include=leads,icp` (comma-separated) |
| **Response** | `{ data: TargetClient \| null, leads?: Lead[], icp?: ICPCriteria \| null }` |
| **Tables** | `reference.target_clients`, `clients.target_client_leads`, `extracted.target_client_icp` |

> **Use case:** Client dashboard (`/[slug]` page) can fetch client + leads + ICP in a single request, eliminating N+1 queries.

---

### Leads

#### Get Leads for Target Client
| Property | Value |
|----------|-------|
| **Route** | `GET /api/leads/[clientId]` |
| **Input** | Path param: `clientId` (UUID), Query: `?limit=number` |
| **Response** | `{ data: Lead[], count: number }` |
| **Tables** | `clients.target_client_leads` |

#### Get Leads with ICP ⭐ Batch Endpoint
| Property | Value |
|----------|-------|
| **Route** | `GET /api/leads/[clientId]?include_icp=true` |
| **Input** | Path param: `clientId` (UUID), Query: `?include_icp=true&limit=number` |
| **Response** | `{ data: Lead[], count: number, icp?: ICPCriteria \| null }` |
| **Tables** | `clients.target_client_leads`, `extracted.target_client_icp` |

> **Use case:** Admin bullseye view can display leads alongside ICP criteria for filtering/scoring context.

---

### ICP (Ideal Customer Profile)

#### Generate ICP for Clients
| Property | Value |
|----------|-------|
| **Route** | `POST /api/icp/generate` |
| **Input** | Body: `{ clients: { id: string, company_name: string, domain: string, company_linkedin_url?: string }[] }` |
| **Response** | `{ results: ICPResult[] }` |
| **Tables** | Calls Modal endpoint, then stores in `raw.icp_payloads` and `extracted.target_client_icp` |

#### Get ICP for Target Client
| Property | Value |
|----------|-------|
| **Route** | `GET /api/icp/[clientId]` |
| **Input** | Path param: `clientId` (UUID) |
| **Response** | `{ data: ICPCriteria \| null }` |
| **Tables** | `extracted.target_client_icp` |

---

### Customer Companies

#### Get Customer Companies for Target Client
| Property | Value |
|----------|-------|
| **Route** | `GET /api/customer-companies/[clientId]` |
| **Input** | Path param: `clientId` (UUID) |
| **Response** | `{ data: CustomerCompany[] }` |
| **Tables** | `reference.target_client_customer_companies` |

#### Add Customer Companies
| Property | Value |
|----------|-------|
| **Route** | `POST /api/customer-companies/[clientId]` |
| **Input** | Body: `{ companies: { customer_domain: string, customer_name?: string, source?: string }[] }` |
| **Response** | `{ success: boolean, inserted: number }` |
| **Tables** | `reference.target_client_customer_companies` (INSERT) |

---

## 3. Shared Types

### TargetClient
```typescript
// packages/shared/src/types/target-client.ts
export interface TargetClient {
  id: string;                           // UUID
  domain: string;
  company_name: string;
  company_linkedin_url: string | null;
  slug: string;
  created_at: string;                   // ISO timestamp
  updated_at: string;                   // ISO timestamp
}

export interface TargetClientInput {
  company_name: string;
  domain: string;
  company_linkedin_url?: string;
  slug?: string;                        // Auto-generated if omitted
}

// Used by: reference.target_clients, /api/target-clients/*
```

### Lead
```typescript
// packages/shared/src/types/lead.ts
export interface Lead {
  id: string;
  target_client_id: string;
  linkedin_url: string;
  person_full_name: string | null;
  person_title: string | null;
  person_location: string | null;
  company_name: string | null;
  company_domain: string | null;
  company_linkedin_url: string | null;
  company_industry: string | null;
  company_size: string | null;
  company_employee_count: number | null;
  company_country: string | null;
  is_worked_at_customer: boolean | null;
  worked_at_customer_company: string | null;
  worked_at_customer_company_name: string | null;
  projected_at: string | null;
  created_at: string;
}

// Used by: clients.target_client_leads, /api/leads/*
```

### ICPCriteria
```typescript
// packages/shared/src/types/icp.ts
export interface CompanyCriteria {
  industries: string[];
  employee_count_min: number | null;
  employee_count_max: number | null;
  size: string[];
  countries: string[];
  founded_min: number | null;
  founded_max: number | null;
}

export interface PersonCriteria {
  title_contains_any: string[];
  title_contains_all: string[];
}

export interface ICPCriteria {
  id: string;
  target_client_id: string;
  industries: string[] | null;
  employee_count_min: number | null;
  employee_count_max: number | null;
  size_buckets: string[] | null;
  countries: string[] | null;
  founded_min: number | null;
  founded_max: number | null;
  title_contains_any: string[] | null;
  title_contains_all: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface ICPResult {
  target_client_id: string;
  company_name: string;
  success: boolean;
  company_criteria?: CompanyCriteria;
  person_criteria?: PersonCriteria;
  error?: string;
}

// Used by: extracted.target_client_icp, /api/icp/*
```

### CustomerCompany
```typescript
// packages/shared/src/types/customer-company.ts
export interface CustomerCompany {
  id: string;
  target_client_id: string;
  customer_domain: string;
  customer_name: string | null;
  source: string | null;
  created_at: string;
}

export interface CustomerCompanyInput {
  customer_domain: string;
  customer_name?: string;
  source?: string;
}

// Used by: reference.target_client_customer_companies, /api/customer-companies/*
```

### API Response Types
```typescript
// packages/shared/src/types/api-responses.ts
export interface ApiResponse<T> {
  data: T;
  error?: string;
}

export interface ApiListResponse<T> {
  data: T[];
  count: number;
  error?: string;
}

export interface UploadResult {
  success: boolean;
  inserted: number;
  errors: string[];
}

// Batch response for /api/target-clients/by-slug/[slug]?include=leads,icp
export interface TargetClientWithIncludes {
  data: TargetClient | null;
  leads?: Lead[];
  icp?: ICPCriteria | null;
  error?: string;
}

// Batch response for /api/leads/[clientId]?include_icp=true
export interface LeadsWithICP {
  data: Lead[];
  count: number;
  icp?: ICPCriteria | null;
  error?: string;
}

// Used by: All API endpoints
```

### IndicatorType
```typescript
// packages/shared/src/types/indicator.ts
export type IndicatorType = "New in Role" | "Recently Funded" | "Worked at Customer" | "Custom";

// Used by: UI components in admin
```

---

## 4. Migration Mapping

### Frontend (Admin) Actions

| Current File | Current Function | New API Endpoint | New File Location |
|--------------|------------------|------------------|-------------------|
| `frontend/app/actions/get-target-clients.ts` | `getTargetClients()` | `GET /api/target-clients` | `apps/admin/app/actions/get-target-clients.ts` |
| `frontend/app/actions/get-leads.ts` | `getLeads(targetClientId?)` | `GET /api/leads/[clientId]` | `apps/admin/app/actions/get-leads.ts` |
| `frontend/app/actions/upload-target-clients.ts` | `uploadTargetClients(rows)` | `POST /api/target-clients` | `apps/admin/app/actions/upload-target-clients.ts` |
| `frontend/app/actions/generate-icp.ts` | `generateICPForClients(clients)` | `POST /api/icp/generate` | `apps/admin/app/actions/generate-icp.ts` |
| `frontend/lib/supabase.ts` | `supabase` client | N/A (deleted) | — |
| `frontend/types/index.ts` | `TargetClient`, `Lead` | N/A (moved) | `packages/shared/src/types/` |

### Client App

| Current File | Current Function | New API Endpoint | New File Location |
|--------------|------------------|------------------|-------------------|
| `client/app/page.tsx` | `getClients()` (inline) | `GET /api/target-clients` | `apps/client/app/page.tsx` (refactored) |
| `client/app/[slug]/page.tsx` | `getClientBySlug(slug)` | `GET /api/target-clients/by-slug/[slug]` | `apps/client/app/[slug]/page.tsx` (refactored) |
| `client/app/[slug]/page.tsx` | `getLeadsForClient(id)` | `GET /api/leads/[clientId]` | `apps/client/app/[slug]/page.tsx` (refactored) |
| `client/lib/supabase.ts` | `supabase` client | N/A (deleted) | — |

---

## 5. Environment Variables

### `/apps/api/.env.local`
```bash
# Supabase (only API app needs these)
NEXT_PUBLIC_SUPABASE_URL=https://ivcemmeywnlhykbuafwv.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service_role_key>       # Required for server-side mutations

# Modal (for ICP generation proxy)
MODAL_ENDPOINT=https://bencrane--hq-master-data-ingest-generate-target-client-icp.modal.run

# CORS (allowed origins)
ALLOWED_ORIGINS=https://admin.bullseyerevenue.com,https://app.bullseyerevenue.com,http://localhost:4500,http://localhost:3000
```

### `/apps/admin/.env.local`
```bash
# API URL (no Supabase vars needed)
NEXT_PUBLIC_API_URL=http://localhost:3001          # Dev
# NEXT_PUBLIC_API_URL=https://api.bullseyerevenue.com  # Prod
```

### `/apps/client/.env.local`
```bash
# API URL (no Supabase vars needed)
NEXT_PUBLIC_API_URL=http://localhost:3001          # Dev
# NEXT_PUBLIC_API_URL=https://api.bullseyerevenue.com  # Prod
```

---

## 6. Deployment Configuration

### `/apps/api` on Vercel
| Setting | Value |
|---------|-------|
| **Root Directory** | `apps/api` |
| **Build Command** | `cd ../.. && pnpm build --filter=api` |
| **Output Directory** | `.next` |
| **Install Command** | `cd ../.. && pnpm install` |
| **Domain** | `api.bullseyerevenue.com` |
| **Environment Variables** | `NEXT_PUBLIC_SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `MODAL_ENDPOINT`, `ALLOWED_ORIGINS` |

### `/apps/admin` on Vercel
| Setting | Value |
|---------|-------|
| **Root Directory** | `apps/admin` |
| **Build Command** | `cd ../.. && pnpm build --filter=admin` |
| **Output Directory** | `.next` |
| **Install Command** | `cd ../.. && pnpm install` |
| **Domain** | `admin.bullseyerevenue.com` |
| **Environment Variables** | `NEXT_PUBLIC_API_URL=https://api.bullseyerevenue.com` |

### `/apps/client` on Vercel
| Setting | Value |
|---------|-------|
| **Root Directory** | `apps/client` |
| **Build Command** | `cd ../.. && pnpm build --filter=client` |
| **Output Directory** | `.next` |
| **Install Command** | `cd ../.. && pnpm install` |
| **Domain** | `app.bullseyerevenue.com` (or `*.bullseyerevenue.com` for client slugs) |
| **Environment Variables** | `NEXT_PUBLIC_API_URL=https://api.bullseyerevenue.com` |

### Vercel Project Structure
Create **3 separate Vercel projects** linked to the same Git repo, each with different root directory settings.

---

## 7. Risks and Considerations

### Breaking Changes
1. **Server Actions → API calls**: Admin/client will have higher latency during SSR (additional network hop to API). Mitigate with proper caching headers.
2. **Environment variable changes**: Existing deployments will break until env vars are reconfigured.
3. **CORS**: API must explicitly allow admin/client origins. Missing CORS config = broken fetch calls.

### Development Workflow
1. **Must run 3 apps locally**: During development, need `api`, `admin`, and `client` all running. Use Turborepo's `turbo dev` to orchestrate.
2. **Hot reload across packages**: Changes to `@bullseye/shared` require rebuild. Configure Turborepo watch mode.
3. **Port conflicts**: Ensure each app uses unique ports (3000, 3001, 4500).

### Authentication (Future)
- Current codebase has no auth. If added later:
  - API should validate auth tokens
  - Admin/client should pass tokens in headers
  - Consider API keys for server-to-server calls

### Data Integrity
1. **Upload validation**: Move CSV validation logic to API (currently in admin upload page). API should be source of truth for validation.
2. **Slug generation**: Currently done client-side. Move to API to ensure consistency.

### Performance
1. **N+1 queries in client app**: ✅ Addressed via batch endpoints (`?include=leads,icp`). Stage 7 explicitly uses these.
2. **Caching strategy**: Add `Cache-Control` headers to API responses. Consider ISR for client dashboard pages.
3. **SSR latency**: Admin/client now have an extra network hop to API. Mitigate by deploying API and frontends in the same Vercel region.

### Type Safety
1. **API contract drift**: Shared types must stay in sync with API responses. Consider generating types from OpenAPI spec or Zod schemas.
2. **Runtime validation**: Add Zod validation in API routes to ensure request bodies match expected types.

### Rollback Plan
- Keep `/frontend` and `/client` directories until Stage 8 is verified in production
- Use feature flags or environment-based routing to gradually shift traffic
- Database schema unchanged — rollback only requires redeploying old apps

### Testing Strategy
1. **API**: Add integration tests hitting real endpoints (Vitest + Supertest)
2. **Admin/Client**: Add E2E tests with Playwright verifying pages render correctly when API is mocked
3. **Shared**: Unit tests for any utility functions

### Estimated Timeline
| Stage | Effort |
|-------|--------|
| Stage 1: Scaffolding | 1-2 hours |
| Stage 2: Shared Package | 2-3 hours |
| Stage 3: API App | 4-6 hours |
| Stage 4: Move Admin | 1-2 hours |
| Stage 5: Move Client | 1 hour |
| Stage 6: Refactor Admin | 3-4 hours |
| Stage 7: Refactor Client | 2-3 hours |
| Stage 8: Cleanup | 1-2 hours |
| **Total** | **15-23 hours** |

---

## Appendix: File Tree After Refactor

```
hq-master-data-warehouse-v2/
├── apps/
│   ├── admin/
│   │   ├── app/
│   │   │   ├── actions/
│   │   │   │   ├── generate-icp.ts
│   │   │   │   ├── get-leads.ts
│   │   │   │   ├── get-target-clients.ts
│   │   │   │   └── upload-target-clients.ts
│   │   │   ├── bullseye/
│   │   │   │   └── page.tsx
│   │   │   ├── target-clients/
│   │   │   │   ├── page.tsx
│   │   │   │   ├── target-clients-table.tsx
│   │   │   │   └── upload/
│   │   │   │       └── page.tsx
│   │   │   ├── globals.css
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx
│   │   ├── components/
│   │   │   ├── dashboard/
│   │   │   ├── layout/
│   │   │   └── ui/
│   │   ├── lib/
│   │   │   ├── api.ts              # NEW: API client
│   │   │   └── utils.ts            # Or import from shared
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── next.config.ts
│   │
│   ├── client/
│   │   ├── app/
│   │   │   ├── [slug]/
│   │   │   │   ├── page.tsx
│   │   │   │   └── not-found.tsx
│   │   │   ├── globals.css
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx
│   │   ├── lib/
│   │   │   └── api.ts              # NEW: API client
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── next.config.ts
│   │
│   └── api/
│       ├── app/
│       │   ├── api/
│       │   │   ├── health/
│       │   │   │   └── route.ts
│       │   │   ├── target-clients/
│       │   │   │   ├── route.ts
│       │   │   │   ├── [id]/
│       │   │   │   │   └── route.ts
│       │   │   │   └── by-slug/
│       │   │   │       └── [slug]/
│       │   │   │           └── route.ts
│       │   │   ├── leads/
│       │   │   │   └── [clientId]/
│       │   │   │       └── route.ts
│       │   │   ├── icp/
│       │   │   │   ├── route.ts
│       │   │   │   └── [clientId]/
│       │   │   │       └── route.ts
│       │   │   └── customer-companies/
│       │   │       └── [clientId]/
│       │   │           └── route.ts
│       │   └── layout.tsx
│       ├── lib/
│       │   └── supabase.ts
│       ├── package.json
│       ├── tsconfig.json
│       └── next.config.ts
│
├── packages/
│   └── shared/
│       ├── src/
│       │   ├── index.ts
│       │   ├── types/
│       │   │   ├── index.ts
│       │   │   ├── target-client.ts
│       │   │   ├── lead.ts
│       │   │   ├── icp.ts
│       │   │   ├── customer-company.ts
│       │   │   ├── api-responses.ts
│       │   │   └── indicator.ts
│       │   ├── constants/
│       │   │   └── index.ts
│       │   └── utils/
│       │       └── index.ts
│       ├── package.json
│       └── tsconfig.json
│
├── modal-mcp-server/           # Unchanged
│   └── ...
│
├── pnpm-workspace.yaml
├── turbo.json
├── package.json
└── REFACTOR_PLAN.md
```

