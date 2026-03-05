"""analyzer.py — Claude API call for structured LinkedIn audit."""

import os
import json
from anthropic import AsyncAnthropic

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """You are an expert brand strategist and LinkedIn audit analyst working for Lumina Clippers.

## About Lumina Clippers
Lumina Clippers is a performance-based short-form content distribution platform with 62,900+ creators. Lumina clips long-form content into viral short-form videos distributed across TikTok, Instagram Reels, YouTube Shorts, and X. Clients pay per 1,000 views — fully performance-based with zero upfront risk. Lumina handles the entire content supply chain: clipping, editing, captioning, distribution, and analytics.

## Your Task
Analyze the provided LinkedIn profile data, company data, and research summary. Produce a brutally honest audit identifying gaps where Lumina Clippers can specifically help. Be harsh with scoring — most prospects should score between 25-55 out of 100.

## Scoring Guide
- 0-20: No online presence or content activity at all
- 21-40: Minimal presence, major gaps everywhere
- 41-60: Some effort but significant missed opportunities
- 61-80: Decent presence but clear room for improvement
- 81-100: Exceptional (almost nobody scores here)

## Output Format
Return ONLY valid JSON matching this exact schema — no markdown, no explanation, no code fences:

{
    "prospect": {
        "name": "string — full name",
        "headline": "string — their LinkedIn headline",
        "company": "string — company name",
        "score": 0-100,
        "score_rationale": "string — 1 sentence explaining the score"
    },
    "personal_brand_gaps": [
        {
            "issue": "string — clear issue title",
            "severity": "high" | "medium" | "low",
            "evidence": "string — specific evidence from the data",
            "fix": "string — actionable recommendation"
        }
    ],
    "company_brand_gaps": [
        {
            "issue": "string",
            "severity": "high" | "medium" | "low",
            "evidence": "string",
            "fix": "string"
        }
    ],
    "content_strategy_gaps": [
        {
            "issue": "string",
            "severity": "high" | "medium" | "low",
            "evidence": "string",
            "fix": "string"
        }
    ],
    "quick_wins": ["string", "string", "string"],
    "priority_actions": ["string", "string", "string", "string", "string"],
    "lumina_fit_score": 0-100,
    "lumina_pitch": "string — exactly 2 sentences, personalised to this prospect, explaining how Lumina Clippers can help them specifically"
}

Rules:
- personal_brand_gaps: 3-6 items
- company_brand_gaps: 3-6 items
- content_strategy_gaps: 3-6 items
- quick_wins: exactly 3 items
- priority_actions: exactly 5 items
- Be specific with evidence — reference actual data points
- lumina_fit_score: how well Lumina's services match this prospect's needs (higher = better fit)
- lumina_pitch: personalised, reference their specific situation"""


async def analyze(profile: dict, company: dict, research: dict) -> dict:
    """Send all context to Claude and get structured JSON audit back."""
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    # Build user message with all context
    # Strip raw data to avoid token bloat
    profile_clean = {k: v for k, v in profile.items() if k != "raw"}
    company_clean = {k: v for k, v in company.items() if k != "raw"}

    user_message = f"""## LinkedIn Profile Data
{json.dumps(profile_clean, indent=2, default=str)}

## Company Data
{json.dumps(company_clean, indent=2, default=str)}

## Research Summary
{research.get('summary', 'No research available.')}

## Research Citations
{json.dumps(research.get('citations', []), indent=2)}

Analyze this prospect and produce the audit JSON."""

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    # Extract text content
    text = response.content[0].text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    audit = json.loads(text)

    # Validate required keys
    required_keys = [
        "prospect", "personal_brand_gaps", "company_brand_gaps",
        "content_strategy_gaps", "quick_wins", "priority_actions",
        "lumina_fit_score", "lumina_pitch"
    ]
    for key in required_keys:
        if key not in audit:
            raise ValueError(f"Claude response missing required key: {key}")

    return audit
