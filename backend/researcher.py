"""researcher.py — Perplexity Agent API call for prospect/company research.

Uses Claude Sonnet 4.6 via Perplexity's Agent API with web search enabled
for deep brand presence and content strategy research.
"""

import os
import json
import httpx

PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
TIMEOUT = 120  # Agent API calls with web search can take longer


async def research(name: str, company: str) -> dict:
    """Query Perplexity Agent API with Claude Sonnet 4.6 + web search
    for brand presence and content strategy intel.

    Falls back gracefully if the API key is missing, expired, or quota exceeded.
    """
    if not PERPLEXITY_API_KEY:
        print("[Researcher] No PERPLEXITY_API_KEY set — skipping research step.")
        return _fallback_research(name, company)

    instructions = (
        "You are a brand research analyst. Research the given person and company "
        "thoroughly using web search. Focus on: brand presence, content strategy, "
        "online reputation, social media activity, content gaps, and opportunities "
        "for improvement. Be specific and cite your sources."
    )

    query = (
        f"Research {name} and their company {company}. "
        f"Analyze their brand presence, content strategy, online reputation, "
        f"social media activity, content gaps, and opportunities for improvement. "
        f"Be thorough and specific."
    )

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
                    "max_output_tokens": 4096,
                    "tools": [{"type": "web_search"}],
                },
            )
            resp.raise_for_status()
            data = resp.json()

        # Extract content from Agent API response format
        content = ""
        citations = []

        for output_item in data.get("output", []):
            # Extract search results as citations
            if output_item.get("type") == "search_results":
                for result in output_item.get("results", []):
                    citations.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                    })

            # Extract message content
            if output_item.get("type") == "message":
                for content_block in output_item.get("content", []):
                    if content_block.get("type") == "output_text":
                        content += content_block.get("text", "")

        if not content:
            print("[Researcher] Perplexity Agent API returned empty content — using fallback.")
            return _fallback_research(name, company)

        return {
            "summary": content,
            "citations": citations,
        }
    except Exception as e:
        print(f"[Researcher] Perplexity Agent API error: {e} — using fallback research.")
        return _fallback_research(name, company)


def _fallback_research(name: str, company: str) -> dict:
    """Minimal research data when Perplexity is unavailable."""
    return {
        "summary": (
            f"Research for {name} at {company} was not available via external API. "
            f"The audit should rely on the LinkedIn profile and company data provided. "
            f"Assess brand presence based solely on the LinkedIn data — profile completeness, "
            f"content activity, engagement metrics, headline quality, and company page presence."
        ),
        "citations": [],
    }
