# DOE Framework: Complete Reference for AI Agents

This document provides comprehensive context on the DOE (Directive Orchestration Execution) framework — a methodology for building reliable agentic workflows. Use this as a reference when incorporating DOE patterns into an existing codebase.

---

## Part 1: The Problem DOE Solves

### Why LLMs Fail at Business Automation

Large Language Models are **probabilistic**. They predict distributions of possible outputs, not deterministic results. This creates a fundamental mismatch with business requirements, which demand consistency and reliability.

**The compounding error problem:**

When you chain multiple LLM operations together, errors compound multiplicatively:

| Steps | Per-Step Accuracy | Total Success Rate |
|-------|-------------------|-------------------|
| 3 | 90% | 72.9% |
| 5 | 90% | 59.0% |
| 10 | 90% | 34.9% |
| 20 | 90% | 12.2% |

The math: `0.9^5 = 0.59` (59% success over 5 steps)

**Business reality:** If an invoice workflow has a 5% error rate, that's not a 5% revenue impact — it's potentially a 95% impact on client relationships. Businesses cannot tolerate probabilistic failures in core operations.

### The Root Cause

When an LLM "does everything itself" — scraping, API calls, data transforms, file operations — each operation has variance. The LLM might:
- Call an API slightly differently each time
- Structure data in inconsistent formats
- Handle edge cases unpredictably
- Fail silently or recover inconsistently

This variance compounds across steps, making complex workflows unreliable.

### The Solution: Separation of Concerns

DOE solves this by separating:
- **What to do** (natural language directives) — handled by humans
- **Decision-making** (orchestration) — handled by the LLM
- **How to do it** (execution) — handled by deterministic code

The LLM's intelligence is reserved for judgment, routing, and handling ambiguity. Repeatable operations are pushed into deterministic scripts that produce identical outputs for identical inputs.

**Result:** 2-3% error rates on business functions instead of 40-60%.

---

## Part 2: The Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 1: DIRECTIVES                      │
│                      (The WHAT)                             │
│                                                             │
│  • Natural language SOPs in Markdown                        │
│  • Define goals, inputs, outputs, edge cases                │
│  • Live in /directives folder                               │
│  • Readable by any human in the organization                │
│  • Contain ZERO code                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   LAYER 2: ORCHESTRATION                    │
│                       (The WHO)                             │
│                                                             │
│  • This is the AI agent                                     │
│  • Reads directives, makes routing decisions                │
│  • Calls execution scripts in correct order                 │
│  • Handles errors, retries, fallbacks                       │
│  • Updates directives with learnings                        │
│  • The "glue" between intent and execution                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 3: EXECUTION                       │
│                       (The HOW)                             │
│                                                             │
│  • Deterministic scripts (typically Python)                 │
│  • Live in /execution folder                                │
│  • Handle API calls, data processing, file ops              │
│  • Same inputs → Same outputs (no hallucination)            │
│  • Testable, version-controllable, optimizable              │
└─────────────────────────────────────────────────────────────┘
```

### Layer 1: Directives (The WHAT)

**Purpose:** High-level instructions that define what the workflow accomplishes.

**Characteristics:**
- Written in Markdown (`.md` files)
- Natural language, like instructions for a mid-level employee
- Contain zero code — must be readable by non-technical team members
- Define goals, inputs, tools to use, expected outputs, edge cases
- Live in the `/directives` folder
- One workflow = one directive file

**Why natural language matters:** If a directive is so technical that a non-engineer can't read and understand it, you've pushed too much complexity into the wrong layer. Directives should be comprehensible by anyone in the organization who understands the business process.

### Layer 2: Orchestration (The WHO)

**Purpose:** The AI agent acts as an intelligent router — reading directives, making decisions, calling tools, handling errors.

**Responsibilities:**
- Read and interpret directives
- Decide which execution scripts to call and in what order
- Pass correct parameters to scripts
- Handle errors and decide when to retry or pivot
- Ask for clarification when genuinely stuck
- Update directives with learnings (edge cases, API quirks, timing)
- Coordinate multi-step workflows

**Key insight:** The orchestrator doesn't do the work itself. It doesn't try to scrape websites, call APIs, or process data directly. It reads the directive, understands what needs to happen, and calls the appropriate execution scripts.

**Analogy:** A project manager rarely does hands-on work. They take inputs, make routing decisions, delegate to specialists, and ensure work gets completed according to specifications. The AI agent operates the same way.

### Layer 3: Execution (The HOW)

**Purpose:** Deterministic scripts that perform the actual work.

**Characteristics:**
- Typically Python (but any language works)
- Live in the `/execution` folder
- Each script does ONE thing well
- Same inputs → Same outputs (deterministic)
- No hallucination — either works correctly or throws clear error
- Can be tested in isolation (unit testing)
- Can be version controlled and optimized independently

**Why deterministic code matters:**
- Sorting 10,000 items: Python = milliseconds, LLM = 30+ seconds
- Python is 10,000-100,000x faster for basic operations
- CPU computation is essentially free vs. LLM token costs
- No ambiguity — scripts either succeed or fail with clear errors

**Reusability:** Multiple directives can call the same execution script. Once a script is optimized and battle-tested, it works reliably everywhere it's used.

---

## Part 3: Why This Architecture Works

### Constraining the Output Space

Probabilistic systems have wide output distributions. DOE constrains this:

```
Without DOE:
[──────────────────────────────────────────────] ← Wide range of possible outputs
         ↑ Desired output somewhere in here

With DOE:
                    [────────]                   ← Narrow, bounded range
                        ↑ Desired output reliably here
```

By pushing deterministic operations into code, you eliminate variance from those steps entirely. The only remaining variance is in the orchestration decisions, which are constrained by explicit directives.

### The Bowling Guardrails Analogy

Think of bowling with bumper rails:
- Without rails: Ball can veer into gutters (workflow fails unpredictably)
- With rails: Ball bounces off bumpers and still hits pins (workflow recovers and succeeds)

DOE provides guardrails that keep the workflow on track even when individual components behave unexpectedly.

### Compound Reliability

When execution scripts are deterministic (100% reliable for valid inputs), the only error source is orchestration decisions. If orchestration is 95% accurate:

| Steps | Orchestration Accuracy | Total Success |
|-------|----------------------|---------------|
| 5 | 95% | 77.4% |
| 5 | 98% | 90.4% |
| 5 | 99% | 95.1% |

Compare to raw LLM (90% per step): 59% success over 5 steps.

DOE shifts the reliability equation fundamentally.

---

## Part 4: File Organization

### Required Structure

```
workspace/
├── directives/           # Layer 1: Natural language SOPs
│   ├── workflow_one.md
│   ├── workflow_two.md
│   └── ...
│
├── execution/            # Layer 3: Deterministic scripts
│   ├── script_one.py
│   ├── script_two.py
│   └── ...
│
├── .env                  # API keys and secrets (never committed)
├── CLAUDE.md             # System prompt for Claude
├── AGENTS.md             # Universal fallback system prompt
├── GEMINI.md             # System prompt for Gemini
├── requirements.txt      # Python dependencies
└── package.json          # Node dependencies (if applicable)
```

### Optional Additions

```
├── .tmp/                 # Temporary/intermediate files (gitignored)
├── resources/            # Reference materials, templates
├── credentials.json      # OAuth credentials (gitignored)
└── token.json           # OAuth tokens (gitignored)
```

### Key Principles

**Deliverables vs. Intermediates:**
- **Deliverables:** Cloud-based outputs users can access (Google Sheets, Slides, etc.)
- **Intermediates:** Temporary files needed during processing (live in `.tmp/`)

**Local files are for processing only.** Final outputs should live in cloud services where users can access them. Everything in `.tmp/` can be deleted and regenerated.

**Credentials in `.env`:** Never hardcode API keys. Scripts reference environment variables (`os.getenv("API_KEY")`). This allows sharing directives without exposing secrets.

---

## Part 5: Writing Effective Directives

### Directive Structure

A well-formed directive contains:

1. **Overview/Description** — What this workflow accomplishes
2. **When to Use** — Conditions that trigger this workflow
3. **Inputs** — What data/parameters are required
4. **Process** — Step-by-step instructions with script references
5. **Output** — What the workflow produces
6. **Edge Cases** — Known exceptions and how to handle them
7. **Troubleshooting** — Common problems and solutions
8. **Learnings** — Accumulated knowledge from running the workflow

### Example Directive: Lead Generation

```markdown
# Google Maps Lead Generation

Generate high-quality B2B leads from Google Maps with deep contact enrichment.

## Overview

This pipeline scrapes Google Maps for businesses, then enriches each result by:
1. Scraping their website (main page + up to 5 contact pages)
2. Searching DuckDuckGo for additional contact info
3. Using Claude to extract structured contact data from all sources

## When to Use

- Building outbound sales lists for local service businesses
- Generating leads for B2B services (contractors, medical, legal, etc.)
- Researching businesses in a specific geographic area

## Inputs

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--search` | Yes | Search query (e.g., "plumbers in Austin TX") |
| `--limit` | No | Max results to scrape (default: 10) |
| `--sheet-url` | No | Existing Google Sheet to append to |

## Execution

```bash
python3 execution/gmaps_lead_pipeline.py --search "plumbers in Austin TX" --limit 50
```

## Output Schema

- `business_name`, `category`, `address`, `phone`, `website`
- `emails` — All email addresses found
- `owner_name`, `owner_email`, `owner_linkedin`
- `lead_id` — Unique identifier for deduplication

## Edge Cases

- **403 errors:** ~10-15% of sites block scrapers. Handled gracefully, lead saved with Google Maps data only.
- **No website:** Some businesses have no website. Enrichment skipped, basic data still captured.

## Troubleshooting

### "No businesses found"
- Include location in query (e.g., "plumbers in Austin, TX" not just "plumbers")

### Duplicate detection
- Pipeline uses `lead_id` (MD5 of name|address) to skip existing leads

## Learnings

- Google Maps actor returns `website` field directly — no need to scrape for it
- Claude Haiku is sufficient for extraction and costs 10x less than Sonnet
- ~10-15% of business websites return 403/503 errors — this is normal
- 50 leads takes ~3-4 minutes with 3 workers
```

### Writing Guidelines

1. **Write like you're instructing a competent employee** — clear but not micromanaging
2. **Include the exact script path and usage** — `execution/script_name.py --param value`
3. **Document the output schema** — what fields are returned and their meaning
4. **Capture edge cases as you discover them** — each failure makes the directive stronger
5. **Include a "Learnings" section** — accumulated knowledge from running the workflow
6. **Be explicit about success criteria** — how does the agent know the workflow succeeded?

---

## Part 6: Writing Effective Execution Scripts

### Script Characteristics

1. **Single responsibility** — each script does ONE thing well
2. **CLI interface** — accept parameters via argparse or stdin
3. **JSON I/O** — read JSON input, output JSON result (for composability)
4. **Deterministic** — same inputs produce same outputs
5. **Clear errors** — fail loudly with actionable error messages
6. **Retry logic** — handle rate limits and transient failures
7. **Environment variables** — credentials from `.env`, never hardcoded

### Example Script Pattern

```python
#!/usr/bin/env python3
"""
Brief description of what this script does.
"""

import os
import sys
import json
import argparse
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
API_KEY = os.getenv("SERVICE_API_KEY")


def main_operation(param1: str, param2: int) -> dict:
    """
    Core logic. Returns structured result dict.
    """
    if not API_KEY:
        raise ValueError("SERVICE_API_KEY not found in environment")
    
    # ... do the work ...
    
    return {
        "success": True,
        "data": result_data,
        "metadata": {...}
    }


def main():
    parser = argparse.ArgumentParser(description="Script description")
    parser.add_argument("--param1", required=True, help="Description")
    parser.add_argument("--param2", type=int, default=10, help="Description")
    
    args = parser.parse_args()
    
    try:
        result = main_operation(args.param1, args.param2)
        print(json.dumps(result, indent=2))
    except Exception as e:
        logger.error(f"Error: {e}")
        print(json.dumps({"success": False, "error": str(e)}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Script Guidelines

1. **Always output JSON** — enables parsing by the orchestrator
2. **Include `success` boolean** — makes it easy to check if operation succeeded
3. **Return structured errors** — `{"success": False, "error": "message", "type": "validation"}`
4. **Log progress** — helps debugging without cluttering output
5. **Handle rate limits** — implement exponential backoff for API calls
6. **Save intermediates to `.tmp/`** — enables recovery and debugging

---

## Part 7: The Self-Annealing Pattern

### What It Is

Self-annealing means the system automatically improves when errors occur:

1. Workflow runs and encounters an error
2. Agent diagnoses the problem
3. Agent fixes the execution script
4. Agent updates the directive with the new edge case
5. Agent retries the operation
6. Future runs don't repeat the same mistake

### The Self-Annealing Loop

```
Error occurs
     ↓
Read error message and stack trace
     ↓
Diagnose root cause
     ↓
Fix the execution script
     ↓
Test the fix
     ↓
Update directive with learnings
     ↓
Retry operation
     ↓
System is now stronger
```

### Implementation in System Prompt

Include these instructions in your AGENTS.md / CLAUDE.md:

```markdown
## Self-Annealing Behavior

When you encounter an error:
1. DO NOT immediately ask the user for help
2. Read the error message and stack trace carefully
3. Diagnose the root cause
4. Fix the execution script
5. Test the fix (unless it uses paid credits — check with user first)
6. Update the directive with what you learned
7. Retry the operation
8. Only escalate to user after 3 failed self-fix attempts

When you successfully fix an issue:
- Document the fix in the execution script (as comments)
- Add the edge case to the directive's "Learnings" or "Edge Cases" section
- This ensures future instances don't repeat the same mistake
```

### Why This Works

Each error becomes a learning opportunity. Instead of failing and requiring human intervention, the system:
- Captures the failure mode
- Implements a fix
- Documents the fix for future reference
- Becomes more robust over time

After 10-20 iterations, you have a "battle-tested" workflow that has seen and handled most edge cases.

---

## Part 8: System Prompt Reference

### Complete AGENTS.md Example

This is the system prompt that teaches the AI agent how to operate within DOE:

```markdown
# Agent Instructions

> This file is mirrored across CLAUDE.md, AGENTS.md, and GEMINI.md so the same 
> instructions load in any AI environment.

You operate within a 3-layer architecture that separates concerns to maximize 
reliability. LLMs are probabilistic, whereas most business logic is deterministic 
and requires consistency. This system fixes that mismatch.

## The 3-Layer Architecture

**Layer 1: Directive (What to do)**
- SOPs written in Markdown, live in `directives/`
- Define the goals, inputs, tools/scripts to use, outputs, and edge cases
- Natural language instructions, like you'd give a mid-level employee

**Layer 2: Orchestration (Decision making)**
- This is you. Your job: intelligent routing.
- Read directives, call execution tools in the right order, handle errors, 
  ask for clarification, update directives with learnings
- You're the glue between intent and execution
- Example: you don't try scraping websites yourself—you read 
  `directives/scrape_website.md` and then run `execution/scrape_single_site.py`

**Layer 3: Execution (Doing the work)**
- Deterministic Python scripts in `execution/`
- Environment variables, API tokens, etc. are stored in `.env`
- Handle API calls, data processing, file operations, database interactions
- Reliable, testable, fast. Use scripts instead of manual work.

**Why this works:** If you do everything yourself, errors compound. 90% accuracy 
per step = 59% success over 5 steps. The solution: push complexity into 
deterministic code. You focus on decision-making only.

## Operating Principles

**1. Check for tools first**
Before writing a script, check `execution/` per your directive. Only create 
new scripts if none exist.

**2. Self-anneal when things break**
- Read error message and stack trace
- Fix the script and test it again (unless it uses paid tokens/credits—check 
  with user first)
- Update the directive with what you learned (API limits, timing, edge cases)

**3. Update directives as you learn**
Directives are living documents. When you discover API constraints, better 
approaches, common errors, or timing expectations—update the directive. But 
don't create or overwrite directives without asking unless explicitly told to.

## Self-Annealing Loop

Errors are learning opportunities. When something breaks:
1. Fix it
2. Update the tool
3. Test tool, make sure it works
4. Update directive to include new edge case
5. System is now stronger

## File Organization

**Deliverables vs Intermediates:**
- **Deliverables**: Google Sheets, Google Slides, or other cloud-based outputs 
  that the user can access
- **Intermediates**: Temporary files needed during processing

**Directory structure:**
- `.tmp/` - All intermediate files. Never commit, always regenerated.
- `execution/` - Python scripts (the deterministic tools)
- `directives/` - SOPs in Markdown (the instruction set)
- `.env` - Environment variables and API keys

**Key principle:** Local files are only for processing. Deliverables live in 
cloud services where the user can access them.

## Summary

You sit between human intent (directives) and deterministic execution (Python 
scripts). Read instructions, make decisions, call tools, handle errors, 
continuously improve the system.

Be pragmatic. Be reliable. Self-anneal.
```

---

## Part 9: Integration Guidelines

### When to Apply DOE Patterns

DOE is most valuable when:
- Workflows have multiple steps that must succeed together
- Operations involve external APIs with rate limits or failures
- Consistency matters (business-critical processes)
- You want workflows to improve over time automatically
- Multiple people or agents need to understand/modify the workflow

DOE may be overkill when:
- Single-shot operations with no chaining
- Purely conversational interactions
- Exploratory/research tasks with no defined success criteria

### Incremental Adoption

You don't need to restructure an entire codebase to benefit from DOE. Consider:

1. **Start with one workflow** — pick a repetitive process that fails sometimes
2. **Extract the directive** — document what the workflow should do
3. **Identify deterministic operations** — which parts could be scripts?
4. **Create execution scripts** — move API calls, data transforms into scripts
5. **Wire up the orchestration** — teach the agent to use the new structure
6. **Iterate** — run, fix, document, improve

### Coexisting with Existing Code

DOE patterns can coexist with existing code:
- Place new directives in `/directives` without touching existing files
- Add execution scripts to `/execution` incrementally
- Keep working code as-is; only refactor what benefits from DOE
- Use the system prompt (AGENTS.md) to teach the agent about both old and new patterns

### Key Questions When Refactoring

When deciding whether to apply DOE to existing code:

1. **Is this operation deterministic?** If yes → candidate for execution script
2. **Does this fail unpredictably?** If yes → needs better error handling in script
3. **Is this repeated across workflows?** If yes → extract to reusable script
4. **Would a non-engineer understand this?** If no → directive needs simplification
5. **Does this require judgment?** If yes → keep in orchestration layer

---

## Part 10: Quick Reference

### The Core Loop

```
User provides high-level intent
         ↓
Agent reads relevant directive
         ↓
Agent calls execution script(s)
         ↓
Scripts return deterministic output
         ↓
Agent validates against success criteria
         ↓
Agent self-anneals if errors occur
         ↓
User receives result
```

### File Purposes

| File | Purpose |
|------|---------|
| `directives/*.md` | Natural language workflow instructions |
| `execution/*.py` | Deterministic scripts that do the work |
| `AGENTS.md` | System prompt teaching agent how to operate |
| `CLAUDE.md` | Claude-specific system prompt |
| `.env` | API keys and secrets |
| `.tmp/` | Temporary files (gitignored) |

### Directive Checklist

- [ ] Clear objective statement
- [ ] When to use this workflow
- [ ] Required inputs documented
- [ ] Step-by-step process with script paths
- [ ] Output schema defined
- [ ] Edge cases documented
- [ ] Troubleshooting section
- [ ] Learnings section (updated over time)

### Execution Script Checklist

- [ ] Single responsibility (does one thing)
- [ ] CLI interface with argparse
- [ ] JSON output for composability
- [ ] Credentials from environment variables
- [ ] Retry logic for API calls
- [ ] Clear error messages
- [ ] Logging for debugging

### Self-Annealing Rules

1. Try to fix errors yourself first
2. Check with user before spending money (paid API calls)
3. Update the script with the fix
4. Update the directive with the edge case
5. Test before declaring success
6. Escalate only after 3 failed attempts

---

## Appendix: Example Files

### Example Directive (create_proposal.md)

```markdown
---
description: Create a PandaDoc proposal for a client
---

## Tool
**Script:** `execution/create_proposal.py`
**Usage:** Automatically generates PandaDoc proposals from structured input

## Process

1. **Gather Information**
   - Client: firstName, lastName, email, company
   - Project: title, problems (4), benefits (4), investment breakdown
   - Either structured input OR extract from sales call transcript

2. **Generate Content**
   - Expand 4 problems into strategic paragraphs (max 50 words each)
   - Expand 4 benefits into implementation-focused paragraphs
   - Use direct "you" language, focus on revenue impact

3. **Execute Proposal Creation**
   - Construct JSON payload
   - Run: `python3 execution/create_proposal.py < input.json`
   - Returns PandaDoc document link

4. **Send Follow-Up Email**
   - Thank them for the discussion
   - Break down proposed solution
   - Include: "I'll send you a full proposal shortly"

## Definition of Done
- [ ] PandaDoc document created and accessible
- [ ] Follow-up email sent to client
- [ ] Internal link returned for review
```

### Example Execution Script Pattern

```python
#!/usr/bin/env python3
"""Creates PandaDoc proposals from structured JSON input."""

import os
import sys
import json
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("PANDADOC_API_KEY")
TEMPLATE_UUID = os.getenv("PANDADOC_TEMPLATE_UUID")

def create_document(config: dict) -> dict:
    """Creates a PandaDoc document from template."""
    if not API_KEY:
        raise ValueError("PANDADOC_API_KEY not found")
    
    headers = {
        "Authorization": f"API-Key {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": config["project_title"],
        "template_uuid": TEMPLATE_UUID,
        "recipients": [{"email": config["client_email"], ...}],
        "tokens": config["tokens"]
    }
    
    response = requests.post(API_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

def main():
    data = json.loads(sys.stdin.read())
    try:
        result = create_document(data)
        print(json.dumps({"success": True, "documentId": result["id"]}, indent=2))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

*This document provides complete context on the DOE framework. Use it as a reference when incorporating DOE patterns into existing code. The goal is increased reliability and maintainability, not wholesale restructuring.*