# Frontend Architecture Principles

This document defines non-negotiable rules for building the HQ Master Data frontend. Follow these precisely to ensure visual consistency and proper API integration.

---

## Principle 0: MCP Tool Usage (MANDATORY)

**Before writing any code, use MCP tools in this order:**

### For every non-trivial task:
1. **sequential-thinking** - Reason through the problem before coding
2. **exa** - Research best practices, patterns, similar implementations

### For component implementation:
1. **shadcn** - Search the registry FIRST. If a component exists, use it.
2. **context7** - Look up Next.js/React/Tailwind documentation
3. **tailwind** - Reference utility classes before inventing custom CSS

### For debugging:
1. **next-devtools** - Inspect runtime state, component tree

**Do NOT skip the research step.** If building a data table with filters, first use exa to find "shadcn data table filter example" or "nextjs admin dashboard table". Look at how others solved it. Then implement.

### shadcn is the component system. Use it exhaustively:
- `npx shadcn@latest add [component]` to add components
- Check https://ui.shadcn.com/docs/components for the full list
- Every standard UI element (button, input, select, table, card, dialog, sheet, skeleton, etc.) comes from shadcn
- Do NOT create custom components for things shadcn already provides

### Required shadcn components for this project:
```bash
npx shadcn@latest add button input select table card skeleton
npx shadcn@latest add dialog sheet dropdown-menu separator
npx shadcn@latest add badge scroll-area navigation-menu
npx shadcn@latest add command popover calendar
```

### Example exa queries to run before implementing:
| Task | exa Query |
|------|-----------|
| Building the leads table | "shadcn data table with pagination and filters example" |
| Building the filter sidebar | "shadcn sidebar filter panel nextjs" |
| Implementing search | "shadcn combobox search filter react" |
| Multi-select dropdown | "shadcn multi-select dropdown example" |
| Date range picker | "shadcn date range picker calendar" |
| Empty state design | "modern empty state design saas dashboard" |
| Loading skeleton | "shadcn skeleton table loading state" |

**Run these queries. Study the results. Then implement.**

---

## Principle 1: Layout Grid Structure

**The app uses a fixed sidebar + fluid main content layout.**

```
+------------------+----------------------------------------+
|     SIDEBAR      |            MAIN CONTENT                |
|     (280px)      |            (fluid)                     |
|                  |                                        |
|  - Navigation    |  +----------------------------------+  |
|  - Filters       |  |  Page Header                     |  |
|                  |  +----------------------------------+  |
|                  |  |  Content Area                    |  |
|                  |  |  (table, cards, etc.)            |  |
|                  |  +----------------------------------+  |
+------------------+----------------------------------------+
```

### Rules:
- Sidebar width: exactly `280px` (or `w-[280px]` in Tailwind)
- Sidebar is fixed position, does not scroll with content
- Main content starts at `left: 280px` and fills remaining width
- Both sidebar and main content have the **same top padding** so elements align horizontally

---

## Principle 2: Spacing System

**Use only these spacing values. No arbitrary numbers.**

| Token | Value | Use Case |
|-------|-------|----------|
| `space-xs` | 4px / `p-1` | Inline icon gaps |
| `space-sm` | 8px / `p-2` | Between related elements |
| `space-md` | 16px / `p-4` | Section padding, card padding |
| `space-lg` | 24px / `p-6` | Page margins, major section gaps |
| `space-xl` | 32px / `p-8` | Page header top padding |

### Critical alignment rule:
```
Sidebar top padding = Main content top padding = 32px (p-8)
```

This ensures the first element in the sidebar (navigation item) and the first element in main content (page header) are on the same horizontal line.

### Example - CORRECT:
```tsx
<aside className="w-[280px] fixed h-screen p-8">
  {/* First item aligns with main content header */}
</aside>
<main className="ml-[280px] p-8">
  {/* Header aligns with sidebar first item */}
</main>
```

### Example - WRONG:
```tsx
<aside className="w-[280px] p-4">  {/* Different padding */}
<main className="ml-[280px] p-6">   {/* Misaligned! */}
```

---

## Principle 3: Component Hierarchy

**Use shadcn/ui components. Do not create custom components for standard UI patterns.**

| UI Element | shadcn Component | Notes |
|------------|------------------|-------|
| Dropdowns/Selects | `<Select>` | For filter dropdowns |
| Data tables | `<Table>` + `<DataTable>` | For leads list |
| Text inputs | `<Input>` | For search, text filters |
| Buttons | `<Button>` | Use variants: default, outline, ghost |
| Cards | `<Card>` | For lead detail panels |
| Sidebar nav | `<NavigationMenu>` or custom | Keep consistent item height |
| Loading states | `<Skeleton>` | Always show during API calls |
| Empty states | Custom but consistent | Center in content area |

### Component spacing rules:
- Filter dropdowns: `space-sm` (8px) gap between label and input
- Filter groups: `space-md` (16px) gap between different filters
- Table rows: use shadcn default, do not override
- Card padding: `space-md` (16px) internal padding

---

## Principle 4: Filter UI Maps to API

**Every filter in the UI must correspond to an API parameter. No orphan UI elements.**

### Core filters (available on all lead views):

| UI Filter | API Parameter | Type | Endpoint |
|-----------|---------------|------|----------|
| Job Function | `job_function` | multi-select | `/api/filters/job-functions` |
| Seniority | `seniority` | multi-select | `/api/filters/seniorities` |
| Industry | `industry` | multi-select | `/api/filters/industries` |
| Company Size | `employee_range` | multi-select | `/api/filters/employee-ranges` |
| Person City | `person_city` | text input | - |
| Person State | `person_state` | text input | - |
| Person Country | `person_country` | dropdown | `/api/filters/countries` |
| Company City | `company_city` | text input | - |
| Company State | `company_state` | text input | - |
| Company Country | `company_country` | dropdown | `/api/filters/countries` |
| Company Domain | `company_domain` | text input | - |
| Company Name | `company_name` | text input | - |
| Job Title | `job_title` | text input | - |
| Full Name | `full_name` | text input | - |
| Job Start Date (from) | `job_start_date_gte` | date picker | - |
| Job Start Date (to) | `job_start_date_lte` | date picker | - |

### Special endpoint filters:

| View | Endpoint | Special Parameters |
|------|----------|-------------------|
| New in Role | `/api/leads/new-in-role` | `started_within_days` (default: 90) |
| Recently Promoted | `/api/leads/recently-promoted` | `promoted_within_days` (default: 180) |
| At VC Portfolio | `/api/leads/at-vc-portfolio` | `vc_name` (optional) |
| By Past Employer | `/api/leads/by-past-employer` | `domains` (required, comma-separated) |
| By Company Customers | `/api/leads/by-company-customers` | `company_domain` (required) |

### Filter state management:
- Store filter state in URL query params (enables sharing, back button)
- Use `nuqs` or similar for type-safe URL state
- Default pagination: `limit=50`, `offset=0`

---

## Principle 5: Data Table Structure

**The leads table displays these columns (matching API response):**

| Column | Field | Width | Sortable |
|--------|-------|-------|----------|
| Name | `full_name` | 200px | No |
| Title | `matched_cleaned_job_title` | 200px | No |
| Company | `company_name` | 180px | No |
| Location | `person_city`, `person_state` | 150px | No |
| Function | `matched_job_function` | 120px | No |
| Seniority | `matched_seniority` | 100px | No |
| Started | `job_start_date` | 100px | No |

### Table rules:
- Fixed header, scrollable body
- Row click opens detail panel (slide-over or modal)
- Show loading skeleton during fetch
- Show empty state when no results
- Pagination at bottom: "Showing 1-50 of 3,825"

---

## Principle 6: Visual Consistency Checklist

Before any PR, verify:

- [ ] Sidebar and main content top padding match (32px)
- [ ] All spacing uses defined tokens (no arbitrary values like `p-[13px]`)
- [ ] All dropdowns use shadcn `<Select>`
- [ ] All inputs use shadcn `<Input>`
- [ ] Loading states use `<Skeleton>`
- [ ] Empty states are centered in content area
- [ ] Filter labels are 12px/`text-xs` muted color
- [ ] Section headers are 14px/`text-sm` font-medium
- [ ] Page titles are 24px/`text-2xl` font-semibold

---

## Principle 7: API Integration Pattern

**All API calls follow this pattern:**

```tsx
// hooks/useLeads.ts
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then(r => r.json());

export function useLeads(filters: LeadFilters) {
  const params = new URLSearchParams();

  if (filters.job_function) params.set('job_function', filters.job_function.join(','));
  if (filters.seniority) params.set('seniority', filters.seniority.join(','));
  // ... other filters
  params.set('limit', String(filters.limit || 50));
  params.set('offset', String(filters.offset || 0));

  const { data, error, isLoading } = useSWR(
    `${API_BASE}/api/leads?${params.toString()}`,
    fetcher
  );

  return {
    leads: data?.data || [],
    total: data?.meta?.total || 0,
    isLoading,
    error,
  };
}
```

### API base URL:
```
Production: https://hq-master-data-api-production.up.railway.app
```

### Response shape (all list endpoints):
```json
{
  "data": [...],
  "meta": {
    "total": 12345,
    "limit": 50,
    "offset": 0
  }
}
```

---

## Principle 8: No Workarounds

**If something doesn't fit the pattern, stop and fix the pattern.**

Signs of a workaround:
- Arbitrary pixel values (`ml-[13px]`)
- Inline styles
- `!important` overrides
- Different spacing in sidebar vs main content
- Filter that doesn't map to API parameter
- Custom component when shadcn has equivalent

Correct response:
1. Stop
2. Identify which principle is being violated
3. Fix at the system level (spacing token, component, etc.)
4. Then continue

---

## File Structure

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout with sidebar
│   ├── page.tsx            # Redirects to /leads
│   └── leads/
│       ├── page.tsx        # All leads view
│       ├── new-in-role/
│       ├── recently-promoted/
│       ├── at-vc-portfolio/
│       ├── by-past-employer/
│       └── by-company-customers/
├── components/
│   ├── ui/                 # shadcn components
│   ├── sidebar.tsx         # App sidebar
│   ├── leads-table.tsx     # Reusable leads table
│   ├── leads-filters.tsx   # Filter panel
│   └── pagination.tsx      # Pagination controls
├── hooks/
│   ├── useLeads.ts         # SWR hook for leads
│   └── useFilters.ts       # SWR hook for filter options
├── lib/
│   └── api.ts              # API client config
└── FRONTEND_PRINCIPLES.md  # This file
```

---

## Quick Reference: The Alignment Rule

The #1 source of janky UI is misaligned elements. Memorize this:

```
SIDEBAR TOP PADDING = MAIN CONTENT TOP PADDING
SIDEBAR ITEM HEIGHT = CONSISTENT (e.g., 40px)
FILTER LABEL SPACING = CONSISTENT (8px below label)
FILTER GROUP SPACING = CONSISTENT (16px between groups)
```

If something looks "off," check these values first.

---

## Getting Started: First Task

**Before building any features, complete this setup:**

### Step 1: Research (use exa)
```
"nextjs 14 app router shadcn sidebar layout example 2024"
"shadcn admin dashboard template github"
```
Study 2-3 examples. Note their spacing, layout structure, component usage.

### Step 2: Initialize shadcn
```bash
npx shadcn@latest init
# Choose: New York style, Zinc color, CSS variables: yes
```

### Step 3: Add required components
```bash
npx shadcn@latest add button input select table card skeleton \
  dialog sheet dropdown-menu separator badge scroll-area \
  navigation-menu command popover calendar
```

### Step 4: Build layout shell
Create the sidebar + main content layout FIRST. Get the spacing right. Verify alignment before adding any features.

```tsx
// app/layout.tsx - the foundation everything else builds on
export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <div className="flex min-h-screen">
          <Sidebar className="w-[280px] fixed h-screen border-r p-8" />
          <main className="ml-[280px] flex-1 p-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
```

### Step 5: Verify alignment
Open the app. The first element in the sidebar and the first element in main content should be on the same horizontal line. If not, fix before proceeding.

---

## Reference: API Endpoints

| View | Endpoint | Required Params |
|------|----------|-----------------|
| All Leads | `GET /api/leads` | None (filters optional) |
| New in Role | `GET /api/leads/new-in-role` | `started_within_days` |
| Recently Promoted | `GET /api/leads/recently-promoted` | `promoted_within_days` |
| At VC Portfolio | `GET /api/leads/at-vc-portfolio` | `vc_name` (optional) |
| By Past Employer | `GET /api/leads/by-past-employer` | `domains` (required) |
| By Company Customers | `GET /api/leads/by-company-customers` | `company_domain` (required) |
| Filter Options | `GET /api/filters/{type}` | None |

API Base: `https://hq-master-data-api-production.up.railway.app`

---

## API Types: Auto-Generated from OpenAPI

**Do NOT manually write API types. They are auto-generated.**

The API exposes an OpenAPI spec at `/openapi.json`. TypeScript types are generated from this spec.

### Files:
- `frontend/api/openapi.json` - OpenAPI spec (source of truth)
- `frontend/api/types.ts` - Auto-generated TypeScript types

### To regenerate types after API changes:
```bash
curl -s "https://hq-master-data-api-production.up.railway.app/openapi.json" > api/openapi.json
npx openapi-typescript api/openapi.json -o api/types.ts
```

### Usage in frontend code:
```tsx
import type { components, operations } from '@/api/types';

// Use the Lead type
type Lead = components['schemas']['Lead'];

// Use response types
type LeadsResponse = components['schemas']['LeadsResponse'];

// Use operation parameters
type GetLeadsParams = operations['get_leads_api_leads_get']['parameters']['query'];
```

### Why this approach:
- Types are always accurate (generated from actual API)
- No documentation drift
- Frontend and backend share the same contract
- Changes to API automatically surface as TypeScript errors
