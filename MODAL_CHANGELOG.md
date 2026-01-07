# Modal Changelog

Master log of all changes to Modal infrastructure. Each entry links to a detailed document.

---

## 2026-01-07

### [FIX-001: Person Extraction Column Name Mismatch](./modal-docs/FIX-001-person-extraction-columns.md)

**Status:** 🔧 Pending deploy  
**Affected endpoints:** `ingest-clay-person-profile`  
**Severity:** Critical — extraction completely broken  

Column name mismatch in `extraction/person.py` caused all person profile extraction to fail silently. Raw data was being stored but extraction threw errors due to non-existent column names.

---

