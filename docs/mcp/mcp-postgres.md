# PostgreSQL MCP Server Documentation

## Overview

This document provides comprehensive documentation for the PostgreSQL MCP (Model Context Protocol) server (`postgres-mcp`) configured in this workspace. This server enables the AI assistant to interact directly with the project's PostgreSQL database to inspect schemas, execute queries, and analyze database health.

## Connection & Authentication

The MCP server connects to the PostgreSQL database using standard connection parameters. In the Cursor environment, these are typically configured via the **Cursor Settings > Features > MCP** menu.

- **Server Identifier**: `user-postgres`
- **Connection Method**: PostgreSQL Connection String (e.g., `postgresql://user:password@host:port/dbname`) or individual parameters (Host, Port, User, Password, Database).
- **Environment Variables**: The server likely uses standard `libpq` environment variables if not explicitly configured in the UI:
    - `DATABASE_URL`
    - `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`

> **Note**: For security, never hardcode passwords in chat or commit them to version control. The MCP server handles authentication securely in the background.

## Available Tools

The following tools are exposed by the `user-postgres` server:

### 1. `execute_sql`
Executes any SQL query against the database.
- **Arguments**:
    - `sql` (string): The SQL query to execute.
- **Returns**: Result set of the query.

### 2. `list_schemas`
Lists all schemas in the database.
- **Arguments**: None.
- **Returns**: List of schema names, owners, and types (System/User).

### 3. `list_objects`
Lists objects (tables, views, etc.) within a specific schema.
- **Arguments**:
    - `schema_name` (string): The schema to list objects from.
    - `object_type` (string, default='table'): Type of object ('table', 'view', 'sequence', 'extension').
- **Returns**: List of object names and types.

### 4. `get_object_details`
Retrieves detailed information (columns, types, constraints, indexes) about a specific database object.
- **Arguments**:
    - `schema_name` (string): Schema containing the object.
    - `object_name` (string): Name of the object.
    - `object_type` (string, default='table'): Type of object.
- **Returns**: Detailed JSON structure defining the table/object.

### 5. `analyze_db_health`
Runs health checks on the database.
- **Arguments**:
    - `health_type` (string, default='all'): Type of check ('all', 'buffer', 'connection', 'constraint', 'index', 'replication', 'sequence', 'vacuum').
- **Returns**: Health report.

### 6. `explain_query`
Explains the execution plan for a SQL query.
- **Arguments**:
    - `sql` (string): The query to explain.
    - `analyze` (boolean, default=false): If true, runs the query to get actual statistics.
    - `hypothetical_indexes` (array): List of indexes to simulate during explanation.
- **Returns**: Execution plan and cost estimates.

### 7. `analyze_query_indexes`
Analyzes specific queries and recommends optimal indexes.
- **Arguments**:
    - `queries` (array of strings): Queries to analyze.
    - `max_index_size_mb` (integer): Storage constraint.
    - `method` (string): 'dta' or 'llm'.
- **Returns**: Index recommendations.

### 8. `analyze_workload_indexes`
Analyzes frequently executed queries (from `pg_stat_statements`) to recommend indexes.
- **Arguments**:
    - `max_index_size_mb` (integer)
    - `method` (string)
- **Returns**: Index recommendations based on actual workload.

### 9. `get_top_queries`
Reports the slowest or most resource-intensive queries.
- **Arguments**:
    - `sort_by` (string, default='resources'): 'total_time', 'mean_time', or 'resources'.
    - `limit` (integer, default=10).
- **Returns**: List of queries with statistics.

---

## Schema Overview

The database is organized into several user schemas. Key schemas include:

- **`core`**: Contains the master entities for the data warehouse.
- **`raw`**: Stores raw payloads from data providers (Clay, Apollo, SalesNav).
- **`public`**: Application settings and miscellaneous tables.
- **`api`**, **`extracted`**, **`final`**, **`manual`**, **`reference`**, **`staging`**, **`temp`**: Additional data layers.

### Key Table Definitions

#### `core.companies`
The central company entity table.
- **Primary Key**: `id` (uuid)
- **Unique Key**: `domain` (text)
- **Columns**:
    - `name` (text)
    - `linkedin_url` (text)
    - `created_at` (timestamptz)
    - `updated_at` (timestamptz)
- **Indexes**: Indices on `domain` and `name` for fast lookups.

#### `core.people`
The central person entity table.
- **Primary Key**: `id` (uuid)
- **Foreign Key**: `core_company_id` -> `core.companies(id)`
- **Unique Key**: `linkedin_url` (text)
- **Columns**:
    - `full_name` (text)
    - `linkedin_slug` (text)
    - `linkedin_url_type` (text)
    - `linkedin_user_profile_urn` (text)
    - `created_at`, `updated_at`
- **Indexes**: Indices on `linkedin_url` and `linkedin_slug`.

#### `raw` Schema Pattern
Tables in the `raw` schema (e.g., `clay_job_change_payloads`, `apollo_scrape`, `company_payloads`) generally follow this pattern:
- **ID**: `id` (uuid)
- **Payloads**: `jsonb` columns (e.g., `raw_event_payload`, `person_record_raw_payload`) storing the full unstructured data from the source.
- **Source Keys**: Columns like `person_linkedin_profile_url` or `clay_table_url` to link back to the source or entity.
- **Timestamps**: `created_at`.

#### `public.apollo_scrape_settings`
Example of an application settings table.
- **Columns**: `id`, `apollo_url` (unique), `search_query`, `filter_criteria` (jsonb), `scrape_title`.

## Example Usage

### 1. Count Companies
```sql
SELECT count(*) FROM core.companies;
```

### 2. Find a Company by Domain
```sql
SELECT id, name, linkedin_url 
FROM core.companies 
WHERE domain = 'example.com';
```

### 3. Check Database Health
Use the `analyze_db_health` tool with `health_type="index"` to check for bloated or unused indexes.

### 4. Inspect Raw Data
```sql
SELECT raw_event_payload 
FROM raw.clay_job_change_payloads 
LIMIT 1;
```

## Limitations & Gotchas

1.  **Sensitive Data**: Be cautious when querying tables with PII (Personally Identifiable Information) like `people` or `raw` payloads. Avoid listing full contents of these tables in chat output unless necessary.
2.  **Performance**:
    - Always use `LIMIT` when querying large tables (e.g., `raw` tables can be huge).
    - `get_object_details` is fast, but `list_objects` on a massive schema might take a moment.
3.  **Permissions**: The MCP server operates with the permissions of the configured user. If the user is `postgres` (superuser), it has full access. If it's a restricted user, some tables or operations might fail.
4.  **Write Operations**: While `execute_sql` *can* perform `INSERT`/`UPDATE`/`DELETE`, it is recommended to use it primarily for `SELECT` (read) operations to avoid accidental data loss. Always verify the SQL before running destructive commands.
5.  **JSONB**: The `raw` schema relies heavily on `jsonb`. Queries might need Postgres JSON operators (e.g., `->>`, `@>`) to extract meaningful data from these columns.
