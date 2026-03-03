# Modal Deployment Protocol

## Correct Order (ALWAYS follow this)

1. **Write code** - make your changes
2. **Git add** - stage the files
3. **Git commit** - commit to main
4. **Git push** - push to origin/main
5. **Modal deploy** - `uv run modal deploy src/app.py`

## Commands

```bash
# Step 1-4: Commit and push first
cd /Users/benjamincrane/hq-master-data-warehouse-v2
git add <files>
git commit -m "feat: description"
git push origin main

# Step 5: Then deploy
cd modal-functions
uv run modal deploy src/app.py
```

## Rules

1. **All code must be committed to main BEFORE deploy**
2. Always deploy from the `src/app.py` entry point
3. Always deploy from the main branch
4. Always use `uv run modal deploy` (not bare `modal deploy`)

## Why This Order Matters

- Deployed code must match what's in git
- Railway auto-deploys from git push
- Ensures traceability - you can always see what's deployed via git history
- Prevents deploying uncommitted/untested code

## DO NOT

- Deploy before committing
- Deploy from a feature branch
- Use `modal deploy` without `uv run`
- Skip the git push step
