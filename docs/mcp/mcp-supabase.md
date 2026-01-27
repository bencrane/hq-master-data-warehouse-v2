# Supabase MCP Server Documentation

This document provides a comprehensive guide to the Supabase MCP server (`@supabase/mcp-server-supabase`) currently configured in this environment.

## 1. Connection & Authentication

The Supabase MCP server connects to your Supabase projects using a personal access token and project IDs.

- **Authentication**: Uses a Supabase Personal Access Token (PAT) configured via the `SUPABASE_ACCESS_TOKEN` environment variable.
- **Project Context**: Most tools require a `project_id` argument to specify which Supabase project to interact with.

### Current Connection Status
- **Verified Project**: `Official HQ Master Data Warehouse`
- **Project ID**: `ivcemmeywnlhykbuafwv`
- **Region**: `us-east-2`
- **Status**: `ACTIVE_HEALTHY`
- **Postgres Version**: `17.6.1.025`

## 2. Available Tools

The following tools are exposed by the Supabase MCP server.

### Core Management
| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `get_project` | Get details for a Supabase project | `id` (Project ID) |
| `get_publishable_keys` | Get the API keys (anon/public and service_role) | `project_id` |
| `get_logs` | Fetch logs by service type (last 24h) | `project_id`, `service` (api, postgres, auth, etc.) |

### Database Operations
| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `list_tables` | List tables in specified schemas | `project_id`, `schemas` (default: ["public"]) |
| `execute_sql` | Execute raw SQL queries | `project_id`, `query` |
| `list_migrations` | List database migrations | `project_id` |
| `apply_migration` | Apply a migration to the database | `project_id`, `migration_up` (SQL), `migration_down` (SQL) |
| `list_extensions` | List installed Postgres extensions | `project_id` |
| `generate_typescript_types` | Generate TS types for the DB | `project_id`, `included_schemas` |

### Edge Functions
| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `list_edge_functions` | List all edge functions | `project_id` |
| `get_edge_function` | Get details of a specific function | `project_id`, `slug` |
| `deploy_edge_function` | Deploy/Create a new edge function | `project_id`, `name`, `entrypoint_path`, `verify_jwt`, `files` |

## 3. Example Usage

### Listing Tables
```json
{
  "server": "user-supabase",
  "toolName": "list_tables",
  "arguments": {
    "project_id": "ivcemmeywnlhykbuafwv",
    "schemas": ["public"]
  }
}
```

### Executing SQL
```json
{
  "server": "user-supabase",
  "toolName": "execute_sql",
  "arguments": {
    "project_id": "ivcemmeywnlhykbuafwv",
    "query": "SELECT count(*) FROM raw_salesnav_leads"
  }
}
```

### Deploying an Edge Function
```json
{
  "server": "user-supabase",
  "toolName": "deploy_edge_function",
  "arguments": {
    "project_id": "ivcemmeywnlhykbuafwv",
    "name": "my-function",
    "entrypoint_path": "index.ts",
    "verify_jwt": true,
    "files": [
      {
        "name": "index.ts",
        "content": "Deno.serve(async (req) => new Response('Hello!'))"
      }
    ]
  }
}
```

## 4. My Projects & Resources

### Active Project
**Official HQ Master Data Warehouse** (`ivcemmeywnlhykbuafwv`)

### Database Tables (Public Schema)
| Table Name | Rows (approx) | Description |
|------------|---------------|-------------|
| `raw_salesnav_leads` | ~2,373 | Raw leads data from Sales Navigator scrapes |
| `folders` | 9 | Folder organization |
| `workbooks` | 62 | Workbook/list organization |
| `salesnav_scrape_settings` | 13 | Configuration for Sales Nav scrapes |
| `apollo_scrape_settings` | 1 | Configuration for Apollo scrapes |
| `apollo_instantdata_scrape_settings` | 13 | Configuration for Apollo Instant Data |
| `temp_bad_company_domains` | 0 | Temporary table for invalid domains |

### Edge Functions
| Name | Slug | Status | Version | Updated |
|------|------|--------|---------|---------|
| `leads-search` | `leads-search` | `ACTIVE` | 4 | Jan 26, 2026 |
| `filter-config` | `filter-config` | `ACTIVE` | 4 | Jan 26, 2026 |

### Key Extensions Installed
- `postgis` (3.3.7) - Spatial and geographic objects
- `vector` (0.8.0) - Vector similarity search (pgvector)
- `pg_cron` (1.6.4) - Job scheduler
- `pg_graphql` (1.5.11) - GraphQL support
- `pg_net` (0.19.5) - Async HTTP
- `supabase_vault` (0.3.1) - Secrets management
- `pg_stat_statements` - Query performance monitoring

### Storage Buckets
*No storage buckets found via `storage.buckets` query.*

## 5. Limitations & Gotchas

1.  **Direct Bucket Listing**: There is no dedicated `list_buckets` tool. You must use `execute_sql` to query `storage.buckets`.
2.  **SQL Safety**: The `execute_sql` tool runs raw queries. Be careful with `DROP` or `DELETE` statements as there is no confirmation step.
3.  **Log Retention**: The `get_logs` tool only retrieves logs from the last 24 hours. For older logs, use the Supabase dashboard.
4.  **Schema Scope**: `list_tables` defaults to `public`. You must explicitly specify other schemas (like `graphql`, `storage`, `vault`) if you need to see their tables.
5.  **Edge Function Files**: When deploying, you must provide the full file content in the `files` array. This is best for small functions or single-file deployments.
