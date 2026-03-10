"""researcher.py — Competitor revenue + CPM lookup.

Step 4 runs two parallel queries:
  A) Competitor annual revenue estimate
  B) CPM costs for the prospect's industry on TikTok, Instagram, YouTube

Primary: Perplexity Sonar (web-grounded search)
Fallback: Claude (knowledge-based estimates) if Perplexity quota is exhausted
"""

import os
import json
import asyncio
import httpx

PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
TIMEOUT = 120


# ══════════════════════════════════════════════════
# Perplexity (primary — web search grounded)
# ══════════════════════════════════════════════════

async def _perplexity_query(system_prompt: str, user_query: str) -> str:
    """Run a Perplexity Sonar chat completion. Returns the text response."""
    if not PERPLEXITY_API_KEY:
        return ""

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "sonar",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query},
                    ],
                    "max_tokens": 1024,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        # Extract content from chat completion response
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
        return ""

    except Exception as e:
        print(f"[Researcher] Perplexity error: {e}")
        return ""


# ══════════════════════════════════════════════════
# Claude fallback (knowledge-based, no web search)
# ══════════════════════════════════════════════════

async def _claude_query(system_prompt: str, user_query: str) -> str:
    """Run a Claude query as fallback when Perplexity is unavailable."""
    if not ANTHROPIC_API_KEY:
        return ""

    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_query}],
        )
        return response.content[0].text if response.content else ""
    except Exception as e:
        print(f"[Researcher] Claude fallback error: {e}")
        return ""


async def _query(system_prompt: str, user_query: str) -> str:
    """Try Perplexity first, fall back to Claude."""
    result = await _perplexity_query(system_prompt, user_query)
    if result:
        return result
    print("[Researcher] Perplexity unavailable, falling back to Claude")
    return await _claude_query(system_prompt, user_query)


# ══════════════════════════════════════════════════
# Research functions
# ══════════════════════════════════════════════════

async def research_competitor_revenue(competitor_name: str, industry: str) -> str:
    """Query A — estimated annual revenue for the competitor."""
    if not competitor_name or not competitor_name.strip():
        return "No competitor specified."

    system_prompt = (
        "You are a financial research analyst. Provide concise, factual answers "
        "about company revenue. If exact data isn't available, provide the best "
        "estimate with reasoning. Keep your answer under 200 words."
    )
    user_query = (
        f"What is the estimated annual revenue of {competitor_name} "
        f"({'in the ' + industry + ' industry ' if industry else ''}"
        f"for the most recent available year? Include the revenue figure, "
        f"year, and source."
    )
    result = await _query(system_prompt, user_query)
    return result or f"Revenue data for {competitor_name} not available."


async def research_cpm_costs(industry: str) -> dict:
    """Query B — CPM costs for the industry across platforms."""
    system_prompt = (
        "You are a digital advertising analyst. Provide specific CPM numbers "
        "per platform. Always include dollar amounts. Keep your answer under 200 words."
    )
    user_query = (
        f"What is the average CPM (cost per 1000 views) for paid ads targeting "
        f"{industry} audiences on TikTok, Instagram, and YouTube in 2025-2026? "
        f"Give specific dollar figures per platform."
    )
    result = await _query(system_prompt, user_query)

    # Try to extract structured CPM data; fall back to industry averages
    cpm_data = _parse_cpm(result, industry)
    return cpm_data


def _parse_cpm(text: str, industry: str) -> dict:
    """Best-effort extraction of CPM numbers from the response.
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
