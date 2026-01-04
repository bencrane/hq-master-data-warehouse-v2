export const SALES_BRIEFING_PROMPT = `
You are generating ICP (Ideal Customer Profile) criteria for a B2B company. Based on the company information provided, analyze what types of companies and people they likely sell to, and output structured criteria.

## Output Format

Return a JSON object with exactly two keys:
```json
{
    "company_criteria": {
        "industries": [],
            "employee_count_min": null,
                "employee_count_max": null,
                    "size": [],
                        "countries": [],
                            "founded_min": null,
                                "founded_max": null
    },
    "person_criteria": {
        "title_contains_any": [],
            "title_contains_all": []
    }
}
```

## Field Definitions

**company_criteria:**
- `industries`: Array of industry strings (e.g., "Software Development", "Technology, Information and Internet", "Financial Services")
- `employee_count_min`: Minimum employee count (integer)
- `employee_count_max`: Maximum employee count (integer)
- `size`: Array of size bucket strings (e.g., "51-200 employees", "201-500 employees")
- `countries`: Array of country strings (e.g., "US", "United States")
- `founded_min`: Earliest founding year to include (integer, optional)
- `founded_max`: Latest founding year to include (integer, optional)

**person_criteria:**
- `title_contains_any`: Array of seniority/role keywords where at least ONE must appear in title (e.g., "VP", "Director", "Head of", "Chief", "Senior Director")
- `title_contains_all`: Array of function keywords where at least ONE must also appear in title (e.g., "Marketing", "Demand Gen", "Growth", "Revenue", "Sales", "Finance")

## Instructions

1. Research or infer what the company does based on their name and domain
2. Determine their likely target market (company size, industry, geography)
3. Determine the likely buyer persona (job titles, seniority, function)
4. Output valid JSON only — no explanation, no markdown, no additional text

---

## Target Client

Company Name: {company_name}
Domain: {domain}
LinkedIn URL: {company_linkedin_url}
`;
