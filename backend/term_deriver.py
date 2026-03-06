"""term_deriver.py — Claude Step 2: derive unified search terms from identity data.

Takes all identity data collected in Step 1 and asks Claude to synthesise
a brand identity + optimised search queries for Step 3 platform searches.
"""

import os
import json
from anthropic import AsyncAnthropic

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """You are given profile data scraped from one or more social platforms
for a person or brand. Your job is to identify who they are and
generate the best search queries to find mentions of their brand
across YouTube, TikTok, Instagram, and X in the last 48 hours.

Return ONLY valid JSON — no prose, no markdown:
{
  "person_name":       str,
  "company_name":      str,
  "brand_summary":     str,
  "youtube_query":     str,
  "tiktok_query":      str,
  "instagram_query":   str,
  "x_query":           str,
  "primary_search":    str
}

Rules:
- brand_summary: 1 sentence on who they are
- Each query should be the most effective search term to find mentions of this brand on that specific platform
- primary_search: single strongest term that works across all platforms
- Keep queries short and specific — brand names, product names, or unique identifiers work best
- If data is sparse, use the company name and person name as fallbacks"""


async def derive_search_terms(identity_data: dict, company_name: str, person_name: str) -> dict:
    """Send all identity data to Claude and get unified search terms back.

    Args:
        identity_data: dict with keys like linkedin, youtube, tiktok, instagram, twitter
        company_name: company name from the form
        person_name: full name from the form

    Returns:
        dict with search terms for each platform
    """
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    # Build context message with all collected identity data
    context_parts = [
        f"Form data — Name: {person_name}, Company: {company_name}",
        "",
        "=== Scraped Identity Data ===",
    ]

    for platform, data in identity_data.items():
        if data.get("data_found"):
            context_parts.append(f"\n--- {platform.upper()} ---")
            context_parts.append(json.dumps(data, indent=2, default=str))

    user_message = "\n".join(context_parts)
    user_message += "\n\nDerive the search terms. Return ONLY valid JSON."

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        text = response.content[0].text.strip()

        # Strip markdown fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        terms = json.loads(text)

        # Validate required keys
        required = ["person_name", "company_name", "brand_summary",
                     "youtube_query", "tiktok_query", "instagram_query",
                     "x_query", "primary_search"]
        for key in required:
            if key not in terms:
                terms[key] = company_name or person_name

        return terms

    except Exception as e:
        print(f"[TermDeriver] Claude error: {e} — using fallback terms.")
        return _fallback_terms(person_name, company_name)


def _fallback_terms(person_name: str, company_name: str) -> dict:
    """Fallback search terms when Claude is unavailable."""
    primary = company_name or person_name
    return {
        "person_name": person_name,
        "company_name": company_name,
        "brand_summary": f"{person_name} at {company_name}",
        "youtube_query": primary,
        "tiktok_query": primary,
        "instagram_query": primary,
        "x_query": primary,
        "primary_search": primary,
    }
