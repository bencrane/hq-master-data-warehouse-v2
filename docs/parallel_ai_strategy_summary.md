# Parallel AI Integration Strategy & Learnings

## 1. Core MCP Servers & Capabilities

We are focusing on two primary Parallel AI MCP servers:

### A. `parallel-search` (Lookup)
*   **Tool:** `web_search_preview`
*   **Best For:** Quick, one-off lookups, finding URLs, or answering simple questions.
*   **Example Use Case:** Finding a company's G2 reviews page URL.
*   **Input:** Natural language query (e.g., "Find the G2 URL for Airtable").

### B. `parallel-task` (Enrichment)
*   **Tool:** `createTaskGroup`
*   **Best For:** Structured data enrichment, batch processing, and filling database columns.
*   **Example Use Case:** Finding competitors, revenue, or employee counts for a list of companies.
*   **Input:**
    *   **Dynamic Values:** JSON object (e.g., `{"company": "Airtable", "domain": "airtable.com"}`).
    *   **Prompt:** Defines the output schema (e.g., "Return a JSON list of top 5 competitors...").

---

## 2. Integration Approaches

### Option 1: The "Enrichment" Way (Recommended for DB)
*   **Mechanism:** `parallel-task` -> `createTaskGroup`
*   **Workflow:**
    1.  Submit a batch of companies.
    2.  Define a strict output schema in the prompt.
    3.  Parallel AI agents research and return structured JSON.
    4.  Write results to the Data Warehouse (`extracted` -> `core` schemas).
*   **Pros:** Structured, scalable, designed for database ingestion.

### Option 2: The "Search" Way (Quick Lookup)
*   **Mechanism:** `parallel-search` -> `web_search_preview`
*   **Workflow:**
    1.  Perform a search query.
    2.  Parse the raw search results (URLs/snippets).
    3.  (Optional) Crawl specific URLs if needed.
*   **Pros:** Fast, good for finding "needles" (like a specific URL).

---

## 3. Handling Selective Field Enrichment

**The Challenge:**
We often have partial data (e.g., Company A needs `revenue`, Company B needs `employee_count`). Can we send one batch with conditional logic ("If x is missing, find x")?

**The Verdict: NO.**
*   **Reasoning:**
    *   **Reliability:** LLMs struggle with complex per-row conditional logic in a single prompt ("hallucination risk").
    *   **Cost/Efficiency:** The underlying "Processor" plans research based on the global prompt. It may perform unnecessary searches for rows that don't need them.

**The Solution: Discrete Micro-Enrichments**
Manage the logic in **Python Code**, not the LLM Prompt.

1.  **Filter in Code:**
    ```python
    # Python Controller Logic
    needs_revenue = [c for c in companies if c.revenue is None]
    needs_funding = [c for c in companies if c.funding is None]
    ```

2.  **Discrete Endpoints/Batches:**
    *   Create specific tasks for specific needs.
    *   `enrich_financials` (Revenue, Funding)
    *   `enrich_firmographics` (Employees, Location)

**Benefits:**
*   **Focus:** Agents perform better when focused on a single domain (e.g., "Find Financials").
*   **Cost:** You only pay for the data holes you actually have.
*   **Cleanliness:** Database updates are simpler (`UPDATE company SET revenue = ...`).
