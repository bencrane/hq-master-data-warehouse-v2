"""
SEC Filing Analysis Prompts

Edit these prompts to iterate on Gemini's analysis output.
The endpoints will pull from here at runtime.
"""

# 10-K Annual Report Analysis
PROMPT_10K = """
You are analyzing an SEC 10-K annual report for a sales team preparing for a call with this company.

Extract and summarize the following in a structured format:

1. **Business Overview** (2-3 sentences)
   - What does this company do? Who are their customers?

2. **Key Financial Metrics**
   - Revenue (latest year)
   - YoY growth %
   - Net income/loss
   - Cash position

3. **Strategic Priorities** (bullet points)
   - What are they focused on for the next 1-2 years?

4. **Risk Factors** (top 3 most relevant for a sales conversation)
   - What challenges are they facing?

5. **Technology & Infrastructure** (if mentioned)
   - What tech stack, platforms, or infrastructure do they discuss?

6. **Sales Talking Points** (2-3 actionable insights)
   - Based on this filing, what would be smart things to mention in a sales call?

Keep responses concise and actionable. Focus on what matters for a sales conversation.
"""

# 10-Q Quarterly Report Analysis
PROMPT_10Q = """
You are analyzing an SEC 10-Q quarterly report for a sales team preparing for a call with this company.

Extract and summarize the following in a structured format:

1. **Quarter Highlights** (2-3 sentences)
   - What happened this quarter? Any notable changes?

2. **Financial Performance**
   - Revenue this quarter
   - QoQ and YoY comparison
   - Any guidance updates?

3. **Recent Developments** (bullet points)
   - New products, partnerships, or initiatives mentioned?
   - Any leadership changes?

4. **Challenges or Concerns**
   - What headwinds are they facing?

5. **Sales Talking Points** (2-3 actionable insights)
   - What's timely and relevant to bring up in a sales call right now?

Keep responses concise and actionable. Focus on recent developments and timely insights.
"""

# 8-K Executive Changes Analysis
PROMPT_8K_EXECUTIVE = """
You are analyzing an SEC 8-K filing about executive changes for a sales team.

Extract:

1. **Who left?** (name, title, effective date)
2. **Who joined?** (name, title, background if mentioned)
3. **Why?** (reason given, if any)
4. **Sales Implication** (1-2 sentences)
   - Is this a good time to reach out? New decision maker? Transition period?

Keep it brief and actionable.
"""

# 8-K Earnings Analysis
PROMPT_8K_EARNINGS = """
You are analyzing an SEC 8-K earnings announcement for a sales team.

Extract:

1. **Headline Numbers**
   - Revenue, EPS, guidance

2. **Beat or Miss?**
   - How did they perform vs expectations (if mentioned)?

3. **Key Quotes** (1-2 from management)
   - What did the CEO/CFO emphasize?

4. **Sales Implication** (1-2 sentences)
   - Are they growing/struggling? Budget implications?

Keep it brief and actionable.
"""
