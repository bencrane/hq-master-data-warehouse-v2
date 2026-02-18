# Postmortem: Session 2026-02-18

## Incident: Guessing Endpoint URLs and App Names

### What Happened
When asked for the endpoint URL for `ingest_clay_person_profile`, I fabricated a URL using a guessed Modal app name ("humaninterest") instead of verifying the actual app name from the codebase.

### The Mistake
```
# What I said (WRONG - GUESSED):
https://humaninterest--ingest-clay-person-profile.modal.run

# What I should have done:
1. Read modal-functions/src/config.py first
2. Found: app = modal.App("hq-master-data-ingest")
3. Only then provided the URL
```

### Root Cause
- Overconfidence in providing a "complete" answer quickly
- Did not verify before responding
- Treated the app name as something I could assume/guess

### Impact
- Provided incorrect information that could have been used in production
- Eroded trust
- Wasted user's time having to catch and correct the error

### Lessons Learned
1. **NEVER guess values** - especially URLs, credentials, app names, config values
2. **Always verify from source** - read the actual config/code before stating facts
3. **Say "I don't know, let me check"** - this is always better than guessing
4. **If uncertain, read first** - uncertainty means verification is required

### Correct Information
- Modal app name: `hq-master-data-ingest`
- Endpoint URL format: `https://hq-master-data-ingest--<function-name>.modal.run`

### Action Items
- When asked for endpoint URLs, ALWAYS read config.py first to get the app name
- When asked for any configuration value, ALWAYS read the source file
- Never assume or extrapolate from partial information
