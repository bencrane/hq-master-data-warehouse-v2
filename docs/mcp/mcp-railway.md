# Railway MCP Server Documentation

This document provides a comprehensive guide to the Railway MCP server (`@railway/mcp-server`) configured in this workspace. It allows you to interact with your Railway infrastructure directly through Cursor.

---

## ⚠️ CRITICAL: Monorepo Root Directory Configuration

**READ THIS FIRST if deploying from a subdirectory (like `hq-api/`).**

When a Railway service deploys code from a **subdirectory** of a monorepo, you MUST configure the Root Directory setting:

1. Go to Railway Dashboard → Select Service → **Settings** tab
2. Under **Source**, find **Root Directory**
3. Set it to the subdirectory path (e.g., `/hq-api`)

**What happens if you don't:**
- Railway deploys from the repo root
- Your app won't start or will use cached/stale code
- Deployments show "SUCCESS" but routes return 404
- You will waste hours debugging

**Current Services and Their Root Directories:**

| Service | Root Directory |
|---------|----------------|
| hq-master-data-api | `/hq-api` |
| modal-mcp-server | `/modal-mcp-server` |

**Verification:** After any deploy, check `https://your-domain/openapi.json` to confirm new routes appear.

See: `/docs/postmortems/2026-01-27-railway-root-directory.md` for full incident details.

---

## Authentication & Connection

The Railway MCP server relies on the **Railway CLI** being installed and authenticated on your local machine.

- **Authentication Method**: It uses the local Railway CLI's authentication state.
- **Setup Requirement**: You must have the Railway CLI installed and run `railway login` in your terminal.
- **Verification**: You can use the `check-railway-status` tool to verify if the CLI is installed and authenticated.

## Available Tools

The following tools are exposed by the MCP server. Most tools require a `workspacePath` argument, which should point to a local directory linked to a Railway project (or where you want to link one).

| Tool Name | Description | Key Parameters |
|-----------|-------------|----------------|
| `check-railway-status` | Verifies Railway CLI installation and login status. | None |
| `list-projects` | Lists all Railway projects for the authenticated account. | None |
| `create-project-and-link` | Creates a new project and links it to the current directory. | `projectName`, `workspacePath` |
| `list-services` | Lists services for the linked project. | `workspacePath` |
| `list-deployments` | Lists deployments for a service with status/metadata. | `workspacePath`, `service`, `environment`, `limit`, `json` |
| `list-variables` | Shows environment variables for the active environment. | `workspacePath`, `service`, `environment`, `kv`, `json` |
| `set-variables` | Sets environment variables. | `workspacePath`, `variables` (array of "KEY=VAL"), `service` |
| `get-logs` | Retrieves build or deploy logs. | `workspacePath`, `logType` ("build"/"deploy"), `deploymentId`, `lines`, `filter` |
| `deploy` | Deploys the current directory to Railway. | `workspacePath`, `environment`, `service`, `ci` |
| `deploy-template` | Deploys a Railway template. | `workspacePath`, `searchQuery` |
| `create-environment` | Creates a new environment, optionally duplicating another. | `workspacePath`, `environmentName`, `duplicateEnvironment` |
| `link-environment` | Links the local directory to a specific Railway environment. | `workspacePath`, `environmentName` |
| `link-service` | Links the local directory to a specific Railway service. | `workspacePath`, `serviceName` |
| `generate-domain` | Generates or retrieves the domain for a service. | `workspacePath`, `service` |

## My Projects & Services

The following Railway projects are currently accessible:

### 1. cal-outbound-solutions
- **ID**: `b4f22ae6-9295-4c1d-8946-2285cc1c38a8`
- **Environments**: `production`
- **Services**:
  - Cal.com Web App
  - Postgres
- **Last Updated**: 1/10/2026

### 2. cal-everything-automation
- **ID**: `a1cc5904-c13b-49f0-bcc2-540b8fedd060`
- **Environments**: `production`
- **Services**:
  - Cal.com Web App
  - Postgres
- **Last Updated**: 1/10/2026

### 3. cal-revenue-activation
- **ID**: `6b726c73-d8a6-4117-bffc-40915e1188e7`
- **Environments**: `production`
- **Services**:
  - Postgres
  - Cal.com Web App
- **Last Updated**: 1/10/2026

### 4. cal-revenue-engineer-dot-com
- **ID**: `7480be06-9f01-40e5-bf2d-ab3de778465a`
- **Environments**: `production`
- **Services**:
  - Postgres
  - Cal.com Web App
- **Last Updated**: 1/10/2026

> **Note**: To use project-specific tools (like `list-services`, `get-logs`, `deploy`) with these projects, you must first run `railway link` in your working directory to associate it with one of these projects.

## Example Usage

### Listing Projects
```json
// Tool: list-projects
{}
```

### Checking Logs (Last 50 lines of errors)
Requires a linked project directory.
```json
// Tool: get-logs
{
  "workspacePath": "/absolute/path/to/project",
  "logType": "deploy",
  "lines": 50,
  "filter": "@level:error"
}
```

### Deploying Changes
```json
// Tool: deploy
{
  "workspacePath": "/absolute/path/to/project"
}
```

### Setting Environment Variables
```json
// Tool: set-variables
{
  "workspacePath": "/absolute/path/to/project",
  "variables": ["API_KEY=12345", "DEBUG=true"],
  "service": "web"
}
```

## Limitations & Gotchas

1.  **Workspace Path Requirement**: Almost all tools require a `workspacePath` argument. This must be an absolute path to a local directory that is **linked** to a Railway project (via `railway link`). If the directory is not linked, the tool may fail or prompt for linking (which can't be handled interactively).
2.  **No Destructive Operations**: The MCP server does **not** expose tools for deleting projects, services, or environments. This is a safety feature. You must use the Railway dashboard or CLI directly for destructive actions.
3.  **Interactive Prompts**: Tools that typically require interactive selection (like `railway link` without arguments) cannot be fully automated via MCP. You should provide specific names/IDs (e.g., `link-service` with `serviceName`) to avoid ambiguity.
4.  **CLI Version**: Advanced log filtering and line limiting require Railway CLI v4.9.0+.
