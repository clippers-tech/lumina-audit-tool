"""scraper.py — Apify actor calls for LinkedIn profile and company data."""

import os
import httpx

APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")
APIFY_BASE = "https://api.apify.com/v2"
TIMEOUT = 180  # seconds — actor runs can take a while


async def scrape_linkedin_profile(url: str) -> dict:
    """Run apify/linkedin-profile-scraper and return the first result item."""
    actor_id = "2SyF0bVxmgGr8IVCZ"  # dev_fusion/Linkedin-Profile-Scraper
    endpoint = f"{APIFY_BASE}/acts/{actor_id}/run-sync-get-dataset-items"

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            endpoint,
            params={"token": APIFY_TOKEN},
            json={"profileUrls": [url]},
        )
        resp.raise_for_status()
        items = resp.json()

    if not items or (isinstance(items, list) and len(items) == 0):
        raise ValueError("Apify returned no profile data for this URL.")

    profile = items[0] if isinstance(items, list) else items
    return _normalise_profile(profile)


async def scrape_linkedin_company(url: str) -> dict:
    """Run curious_coder/linkedin-company-detail-scraper and return the first result."""
    actor_id = "curious_coder~linkedin-company-detail-scraper"
    endpoint = f"{APIFY_BASE}/acts/{actor_id}/run-sync-get-dataset-items"

    cookies_raw = os.environ.get("LI_COOKIES", "")
    cookies = []
    if cookies_raw:
        try:
            import json
            cookies = json.loads(cookies_raw)
        except Exception:
            cookies = []

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            endpoint,
            params={"token": APIFY_TOKEN},
            json={"urls": [url], "cookies": cookies},
        )
        resp.raise_for_status()
        items = resp.json()

    if not items or (isinstance(items, list) and len(items) == 0):
        raise ValueError("Apify returned no company data for this URL.")

    company = items[0] if isinstance(items, list) else items
    return _normalise_company(company)


def _normalise_profile(raw: dict) -> dict:
    """Extract and normalise key fields from the profile scraper output."""
    full_name = raw.get("fullName") or ""
    if not full_name:
        first = raw.get("firstName", "")
        last = raw.get("lastName", "")
        full_name = f"{first} {last}".strip()

    experiences = []
    for exp in raw.get("experiences", []) or []:
        experiences.append({
            "title": exp.get("title", ""),
            "company": exp.get("companyName", ""),
            "description": exp.get("jobDescription") or exp.get("description", ""),
            "start": exp.get("jobStartedOn") or exp.get("startedOn", ""),
            "end": exp.get("jobEndedOn") or exp.get("endedOn", ""),
            "industry": exp.get("companyIndustry", ""),
        })

    skills = []
    for s in raw.get("skills", []) or []:
        if isinstance(s, dict):
            name = s.get("name") or s.get("title", "")
        else:
            name = str(s)
        if name:
            skills.append(name)

    # Updates/posts — field can be "updates" or "posts"
    posts = []
    for p in raw.get("updates", []) or raw.get("posts", []) or []:
        posts.append({
            "text": p.get("postText") or p.get("text", ""),
            "likes": p.get("likes", 0),
            "comments": p.get("comments", 0),
            "shares": p.get("shares", 0),
        })

    return {
        "fullName": full_name,
        "headline": raw.get("headline", ""),
        "summary": raw.get("about") or raw.get("summary", ""),
        "connections": raw.get("connections", 0),
        "followers": raw.get("followers", 0),
        "companyName": raw.get("companyName", ""),
        "companyLinkedin": raw.get("companyLinkedin", ""),
        "companyIndustry": raw.get("companyIndustry", ""),
        "companyWebsite": raw.get("companyWebsite", ""),
        "experiences": experiences,
        "skills": skills,
        "posts": posts,
        "totalExperienceYears": raw.get("totalExperienceYears", 0),
        "isCreator": raw.get("isCreator", False),
        "isInfluencer": raw.get("isInfluencer", False),
        "isPremium": raw.get("isPremium", False),
        "raw": raw,
    }


def _normalise_company(raw: dict) -> dict:
    """Extract and normalise key fields from the company scraper output."""
    return {
        "name": raw.get("name", ""),
        "description": raw.get("description", ""),
        "industry": raw.get("Industry", ""),
        "numberOfEmployees": raw.get("numberOfEmployees", 0),
        "followersCount": raw.get("FollowersCount", 0),
        "website": raw.get("website", ""),
        "foundedYear": raw.get("founded_year", ""),
        "headquarters": raw.get("Headquarters", ""),
        "specialties": raw.get("Specialties", []) or [],
        "companySize": raw.get("Company size", ""),
        "recentPosts": raw.get("recentPosts", []) or [],
        "raw": raw,
    }
