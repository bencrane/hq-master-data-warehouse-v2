# Post-Mortem: Railway Deployment Root Directory Misconfiguration

**Date:** January 27, 2026
**Duration:** ~4 hours of debugging
**Severity:** High (blocked all new feature deployments)
**Service Affected:** hq-master-data-api on Railway

## Summary

New API routes were being added to `hq-api/` but consistently returned 404 after "successful" Railway deployments. The root cause was Railway deploying from the repository root (`/`) instead of the `hq-api/` subdirectory.

## Timeline

- **16:00** - Started adding auth endpoints to `hq-api/routers/auth.py`
- **16:30** - First noticed `/api/auth/me` returning 404 despite code being pushed
- **17:00** - Multiple redeploys attempted, environment variables checked and re-entered
- **17:30** - Discovered AUTH_DATABASE_URL had formatting issues (leading space), fixed
- **18:00** - Auth endpoints started working intermittently after agent forced manual deploy
- **18:30** - Added magic link endpoints, pushed to GitHub, still 404
- **19:00** - Agent diagnosed root cause: Railway Root Directory was set to `/` instead of `/hq-api`
- **19:15** - Fixed Root Directory setting, deployments now work correctly

## Root Cause

Railway's **Root Directory** setting was configured to `/` (repository root). The hq-api code lives in the `/hq-api` subdirectory. This caused Railway to:

1. Build from the wrong directory
2. Not find the FastAPI app or requirements.txt
3. Cache stale builds from previous manual deployments
4. Show "SUCCESS" even when deploying the wrong code

## What Made Debugging Difficult

1. **Railway showed "SUCCESS"** - No obvious error to indicate wrong directory
2. **Some routes worked** - Old routes from cached builds still functioned
3. **Env var red herring** - We spent time debugging AUTH_DATABASE_URL formatting
4. **Multiple deployment methods** - Mix of GitHub auto-deploy and CLI `railway up` caused confusion
5. **No clear build logs** - Didn't immediately show "wrong directory" as an issue

## Resolution

Changed Railway Settings → Source → **Root Directory** from `/` to `/hq-api`

## Lessons Learned

1. **Check Root Directory FIRST** when routes don't appear after deployment
2. **Monorepo projects require explicit subdirectory configuration**
3. **Railway "SUCCESS" doesn't mean your code deployed** - verify routes in /openapi.json
4. **Document Railway configuration** for future reference

## Action Items

- [x] Fix Root Directory setting in Railway
- [x] Document this in `docs/mcp/mcp-railway.md`
- [x] Create this post-mortem for future reference

## Prevention

For any new Railway service deploying from a monorepo subdirectory:
1. Set Root Directory immediately after creating the service
2. Verify `/openapi.json` shows expected routes after first deploy
3. Check build logs to confirm correct files are being deployed
