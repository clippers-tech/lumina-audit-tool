"""analyzer.py — Claude Step 5: generate the structured audit JSON.

Receives the full assembled context (identity data, platform search results,
competitor revenue, CPM data) and produces the complete audit output.

The output JSON is consumed directly by pdf_generator.py v3 (dashboard-style).
"""

import os
import json
from anthropic import AsyncAnthropic

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """You are an expert brand strategist and marketing audit analyst working for Lumina Clippers.

## About Lumina Clippers
Lumina Clippers is a performance-based short-form content distribution platform with 62,900+ creators. Lumina clips long-form content into viral short-form videos distributed across TikTok, Instagram Reels, YouTube Shorts, and X. Clients pay per 1,000 views — fully performance-based with zero upfront risk. Lumina handles the entire content supply chain: clipping, editing, captioning, distribution, and analytics.

## Your Task
Analyze the provided data and produce a structured marketing audit. This audit will be rendered as a 6-page dashboard-style PDF and emailed to the prospect.

The PDF pages are:
1. Visibility Score gauge (0-100)
2. Brand Exposure — total views + per-platform breakdown
3. Competitor Exposure — their total views + comparison bar + per-platform breakdown
4. Revenue Comparison — side-by-side bar chart
5. CPM Comparison — Meta Ads vs Clipping
6. CTA — Lumina fit score + personalised pitch

## CRITICAL: Data Noise Detection
Search results OFTEN contain irrelevant data — unrelated accounts, brand-name collisions, viral content from other creators. You MUST:
1. Strip noise from view counts — only count genuinely relevant brand mentions
2. If 95% of results are unrelated, the real visibility is near zero
3. Be harsh with scoring — most prospects should score 15-45

## Scoring Guide — Visibility Score
- 0-20: Invisible — no genuine organic mentions
- 21-40: Barely visible — scattered presence, mostly noise
- 41-60: Some traction — occasional real mentions but no strategy
- 61-80: Solid presence — regular visibility, room for growth
- 81-100: Dominant — they don't need us (almost nobody scores here)

## Output Format
Return ONLY valid JSON matching this exact schema — no markdown, no code fences, no explanation:

{
    "prospect": {
        "name": "string",
        "company": "string",
        "industry": "string",
        "visibility_score": 0-100,
        "score_rationale": "string — 1 sentence"
    },
    "visibility_audit": {
        "their_total_views_48h": int,
        "platform_breakdown": [
            {
                "platform": "string — e.g. Twitter / X, TikTok, Instagram, YouTube",
                "their_views": int
            }
        ]
    },
    "competitor_visibility": {
        "competitor_name": "string",
        "competitor_total_views_48h": int,
        "platform_breakdown": [
            {
                "platform": "string",
                "their_views": int
            }
        ]
    },
    "revenue_comparison": {
        "own_revenue": "string — as submitted, e.g. $500k",
        "competitor_name": "string",
        "competitor_revenue": "string — ALWAYS a dollar estimate, NEVER N/A (see estimation rules)",
        "competitor_revenue_is_estimate": bool,
        "own_views_48h": int,
        "competitor_views_48h": int
    },
    "cost_analysis": {
        "meta_cpm": float — average Meta Ads CPM for their industry (typically $8-$25),
        "clipping_cpm": float — Lumina's effective CPM (typically $0.50-$1.50)
    },
    "lumina_fit_score": 0-100,
    "lumina_pitch": "string — 2 sentences max, personalised, reference their visibility gap"
}

Rules:
- visibility_score and lumina_fit_score are independent scores
- their_total_views_48h = sum of platform views (after noise stripping)
- competitor views should reflect real data from search results. If no competitor search data exists, estimate based on their social following and industry benchmarks
- own_views_48h and competitor_views_48h in revenue_comparison should match visibility totals
- meta_cpm: use real industry average data (research provided). If unknown, estimate based on industry.
- clipping_cpm: Lumina's performance-based model typically delivers $0.50-$1.50 CPM
- lumina_pitch: personalised, reference their specific visibility gap and competitor. No fluff.
- Keep ALL text minimal — this is a dashboard PDF, not a report. Numbers speak.

## CRITICAL: Competitor Revenue Estimation (NEVER show N/A)
competitor_revenue MUST always be a dollar figure — NEVER "N/A", "Not available", or empty.
This is a ROUGH ESTIMATE and that's fine — prospects understand it's directional.

Use this priority:
1. If Perplexity research found a real revenue figure → use it. Set "competitor_revenue_is_estimate": false.
2. If no real data AND the prospect provided their own revenue → ESTIMATE. Set "competitor_revenue_is_estimate": true.
   Use the view ratio as a starting point: competitor_revenue_est = own_revenue × (competitor_views_48h / own_views_48h)
   BUT apply these safeguards:
   - If the audited brand has near-zero views (< 500), they likely rely on ads, not organic social. Do NOT extrapolate to absurd multiples.
     Instead, estimate the competitor's revenue using their follower counts, industry size, and known benchmarks.
   - CAP the estimate: competitor revenue should never exceed 50× the brand's own revenue. If the math gives $50M but the brand reports $100k, something is off — use industry context to pick a reasonable figure.
   - For small/medium businesses, keep estimates grounded: $200k–$10M range is typical. Only go higher for clearly large brands.
3. If NEITHER real data NOR own_revenue is available → estimate based on competitor's social reach, industry, and follower counts. Set "competitor_revenue_is_estimate": true.
   Use rough heuristics: small niche brand = $200k–$1M, mid-size = $1M–$10M, large = $10M+.

Format as a clean dollar string: "~$3.75M", "~$1.2M", "~$800k" (use ~ prefix for estimates). No caveats in the value.
The "competitor_revenue_is_estimate" boolean field tells the PDF renderer to label it as estimated."""


async def analyze(
    identity_data: dict,
    search_results: dict,
    research_data: dict,
    form_data: dict,
) -> dict:
    """Send all context to Claude and get structured JSON audit back.

    Args:
        identity_data: identity profiles from Step 1
        search_results: platform search results from Step 3
        research_data: competitor revenue + CPM from Step 4
        form_data: original form submission (name, email, company, industry, etc.)
    """
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    # Build user message
    user_message = f"""## Prospect Information (from form)
Name: {form_data.get('full_name', 'Unknown')}
Company: {form_data.get('company_name', 'Unknown')}
Industry: {form_data.get('industry', 'Unknown')}
Self-reported revenue: {form_data.get('own_revenue', 'Not provided')}
Biggest competitor: {form_data.get('competitor_name', 'Not provided')}

## Identity Data (Step 1 — profile scrapes)
{json.dumps(identity_data, indent=2, default=str)}

## Platform Search Results (Step 3 — brand mentions, last 48h)
{json.dumps(search_results, indent=2, default=str)}

## Competitor Revenue Research (Step 4)
{research_data.get('competitor_revenue', 'Not available')}

## CPM Cost Research (Step 4)
{json.dumps(research_data.get('cpm_data', {}), indent=2, default=str)}

Produce the complete audit JSON now."""

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    text = response.content[0].text.strip()

    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    audit = json.loads(text)

    # Validate required top-level keys
    required_keys = [
        "prospect", "visibility_audit", "competitor_visibility",
        "revenue_comparison", "cost_analysis",
        "lumina_fit_score", "lumina_pitch",
    ]
    for key in required_keys:
        if key not in audit:
            raise ValueError(f"Claude response missing required key: {key}")

    return audit
