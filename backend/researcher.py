"""researcher.py — Perplexity API: competitor revenue + CPM lookup.

Step 4 runs two parallel queries:
  A) Competitor annual revenue estimate
  B) CPM costs for the prospect's industry on TikTok, Instagram, YouTube
"""

import os
import json
import asyncio
import httpx

PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
TIMEOUT = 120


async def _perplexity_query(query: str, instructions: str) -> str:
    """Run a single Perplexity Agent API query. Returns the text response."""
    if not PERPLEXITY_API_KEY:
        return ""

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                "https://api.perplexity.ai/v1/responses",
                headers={
                    "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "anthropic/claude-sonnet-4-6",
                    "input": query,
                    "instructions": instructions,
                    "max_output_tokens": 2048,
                    "tools": [{"type": "web_search"}],
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = ""
        for output_item in data.get("output", []):
            if output_item.get("type") == "message":
                for block in output_item.get("content", []):
                    if block.get("type") == "output_text":
                        content += block.get("text", "")
        return content

    except Exception as e:
        print(f"[Researcher] Perplexity error: {e}")
        return ""


async def research_competitor_revenue(competitor_name: str, industry: str) -> str:
    """Query A — estimated annual revenue for the competitor."""
    query = (
        f"What is the estimated annual revenue of {competitor_name} in {industry} "
        f"for the most recent available year?"
    )
    instructions = (
        "You are a financial research analyst. Find the most recent estimated annual "
        "revenue figure for the company. Return a concise answer with the revenue "
        "figure, the year it's from, and the source. If you can't find exact revenue, "
        "provide the best estimate and explain why."
    )
    result = await _perplexity_query(query, instructions)
    return result or f"Revenue data for {competitor_name} not available."


async def research_cpm_costs(industry: str) -> dict:
    """Query B — CPM costs for the industry across platforms."""
    query = (
        f"What is the average CPM (cost per 1000 views) for paid ads targeting "
        f"{industry} audiences on TikTok, Instagram, and YouTube in 2025?"
    )
    instructions = (
        "You are a digital advertising analyst. Find the average CPM rates for paid ads "
        "on TikTok, Instagram, and YouTube for the given industry. Return your answer "
        "as a concise summary with specific numbers per platform. If exact data isn't "
        "available, provide industry benchmarks and explain your estimate."
    )
    result = await _perplexity_query(query, instructions)

    # Try to extract structured CPM data; fall back to industry averages
    cpm_data = _parse_cpm(result, industry)
    return cpm_data


def _parse_cpm(text: str, industry: str) -> dict:
    """Best-effort extraction of CPM numbers from Perplexity's response.
    Falls back to sensible industry averages if parsing fails.
    """
    import re

    # Default CPMs by platform (industry averages in USD)
    defaults = {"tiktok": 10.0, "instagram": 12.0, "youtube": 15.0}

    cpm = {}
    for platform in ["tiktok", "instagram", "youtube"]:
        # Look for patterns like "TikTok: $X" or "TikTok CPM is $X"
        pattern = rf"{platform}[^$]*\$(\d+(?:\.\d+)?)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            cpm[platform] = float(match.group(1))
        else:
            cpm[platform] = defaults[platform]

    cost_100k = {
        "tiktok": round(cpm["tiktok"] * 100, 2),
        "instagram": round(cpm["instagram"] * 100, 2),
        "youtube": round(cpm["youtube"] * 100, 2),
    }
    cost_100k["average"] = round(sum(cost_100k[p] for p in ["tiktok", "instagram", "youtube"]) / 3, 2)

    return {
        "industry": industry,
        "cpm_by_platform": cpm,
        "cost_for_100k_views": cost_100k,
        "raw_response": text,
    }


async def research(competitor_name: str, industry: str) -> dict:
    """Run both research queries in parallel and return combined results."""
    revenue_task = research_competitor_revenue(competitor_name, industry)
    cpm_task = research_cpm_costs(industry)

    revenue_text, cpm_data = await asyncio.gather(revenue_task, cpm_task)

    return {
        "competitor_revenue": revenue_text,
        "cpm_data": cpm_data,
    }
