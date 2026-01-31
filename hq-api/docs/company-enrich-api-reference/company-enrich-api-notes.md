# CompanyEnrich API - Important Usage Notes

## The Batch Domain Gotcha

When using the `/companies/similar/preview` endpoint, there's a critical behavior to understand about how the `domains` array works.

### What You Might Expect

If you send multiple domains:

```json
{
  "domains": ["stripe.com", "airbnb.com", "notion.so"],
  "similarityWeight": 0.5,
  "countries": ["US"]
}
```

You might expect to get back results like:
- "Here are companies similar to stripe.com"
- "Here are companies similar to airbnb.com"
- "Here are companies similar to notion.so"

### What Actually Happens

The API treats all domains as a **single input set** and returns companies that are similar to **the combination of all provided domains**.

So if you send `["stripe.com", "airbnb.com", "notion.so"]`, you get back a single list of companies that are similar to "a company that's like Stripe AND Airbnb AND Notion combined."

The response does not indicate which origin domain each result is similar to. You just get one flat list of similar companies.

### The Problem

This makes it impossible to answer the question: "For each company in my list, what are the similar companies?"

If you have 100 companies and want to find similar companies for each one, sending them all in one request gives you a useless combined result rather than 100 separate result sets.

### The Solution

**Process domains one at a time.** Make individual API calls for each domain:

```javascript
// WRONG - gives combined results
const response = await fetch(API_URL, {
  body: JSON.stringify({
    domains: ["stripe.com", "airbnb.com", "notion.so"]
  })
});

// CORRECT - process individually
for (const domain of domains) {
  const response = await fetch(API_URL, {
    body: JSON.stringify({
      domains: [domain]  // Single domain per request
    })
  });
  // Now you know these results are similar to THIS specific domain
}
```

### Performance Considerations

Processing domains individually means more API calls. For large lists:

- Consider rate limiting (add delays between requests)
- Use parallel processing with concurrency limits (e.g., 10 concurrent requests)
- The `/preview` endpoint is free but returns max 25 results per domain

### Summary

| Approach | Result |
|----------|--------|
| Send N domains in one request | 1 combined result set (not useful for per-domain analysis) |
| Send 1 domain per request, N times | N separate result sets (what you actually want) |

Always send **one domain per request** when you need to know which similar companies map to which origin domain.
