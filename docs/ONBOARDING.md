# AI Session Onboarding

**New session? Read these files in order.**

This is the mandatory reading list for any AI instance working on this codebase. Do not start work until you have read these.

---

## Required Reading (In Order)

### 1. Project Context
| File | Why |
|------|-----|
| [CLAUDE.md](./CLAUDE.md) | Project summary, stack, principles, gotchas |
| [SESSION_STATE.md](./workbench/SESSION_STATE.md) | Current work state, what was just done, what's next |

### 2. Active Work
| File | Why |
|------|-----|
| [/docs/workbench/README.md](./workbench/README.md) | Current session priorities |
| [/docs/workbench/TODO.md](./workbench/TODO.md) | Full task list |
| Any files in `/docs/workbench/active/` | Work currently in progress |

### 3. Architecture (Read as needed)
| File | Why |
|------|-----|
| [/docs/architecture/overview.md](./architecture/overview.md) | System architecture diagram |
| [/docs/architecture/api-principles.md](./architecture/api-principles.md) | API design rules |
| [/docs/architecture/data-ingestion.md](./architecture/data-ingestion.md) | 4-schema data flow |

### 4. Reference (When working on specific areas)
| Area | File |
|------|------|
| Modal workflows | [/docs/workflows/README.md](./workflows/README.md) |
| Frontend | [/docs/architecture/frontend-principles.md](./architecture/frontend-principles.md) |
| DOE framework | [/docs/workbench/active/doe-framework.md](./workbench/active/doe-framework.md) |

---

## Quick Start Checklist

- [ ] Read CLAUDE.md (5 min)
- [ ] Read SESSION_STATE.md to understand current state
- [ ] Check workbench/README.md for today's priorities
- [ ] Scan TODO.md for context on pending work
- [ ] Ask user what they want to focus on

---

## Operating Rules

After reading onboarding docs, you are expected to:

1. **Self-anneal** — Update docs when you learn something (not optional)
2. **Update SESSION_STATE.md** — After completing any major milestone
3. **Keep knowledge in the repo** — Not in chat transcripts
4. **Always use the Supabase psql connection string** — Never use `$DATABASE_URL`. Always use: `postgresql://postgres:rVcat1Two1d8LQVE@db.ivcemmeywnlhykbuafwv.supabase.co:5432/postgres`
5. **Deploy Modal with uv** — Always `cd modal-functions && uv run modal deploy src/app.py`
6. **No RPC/raw SQL workarounds** — If a schema isn't accessible via PostgREST, tell the user to expose it in Supabase. Don't hack around it.

See CLAUDE.md for full operating principles.
