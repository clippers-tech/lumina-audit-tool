"""worker.py — 6-step audit pipeline executed as an async background task."""

import traceback
from datetime import datetime, timezone

from storage import update_job
from scraper import scrape_linkedin_profile, scrape_linkedin_company
from researcher import research
from analyzer import analyze
from pdf_generator import generate_pdf


async def run_pipeline(job_id: str, url: str):
    """Execute the full 6-step audit pipeline for a given job."""
    profile_data = {}
    company_data = {}
    research_data = {}
    audit_data = {}

    try:
        # ── Step 1: Scrape LinkedIn profile ──
        update_job(job_id, status="scraping", step=1)
        profile_data = await scrape_linkedin_profile(url)
        prospect_name = profile_data.get("fullName", "Unknown")
        update_job(job_id, prospect_name=prospect_name)

        # ── Step 2: Extract company LinkedIn URL ──
        update_job(job_id, status="scraping", step=2)
        company_url = profile_data.get("companyLinkedin", "")
        company_name = profile_data.get("companyName", "")

        if not company_url and company_name:
            # Try to construct a company URL from the name
            slug = company_name.lower().replace(" ", "-").replace(",", "").replace(".", "")
            company_url = f"https://www.linkedin.com/company/{slug}"

        if not company_url:
            # No company data available — create minimal company data
            company_data = {
                "name": company_name or "Unknown",
                "description": "",
                "industry": "",
                "numberOfEmployees": 0,
                "followersCount": 0,
                "website": "",
                "foundedYear": "",
                "headquarters": "",
                "specialties": [],
                "companySize": "",
                "recentPosts": [],
            }
            update_job(job_id, company_name=company_name or "Unknown", step=3)
        else:
            # ── Step 3: Scrape company page ──
            update_job(job_id, status="scraping", step=3)
            try:
                company_data = await scrape_linkedin_company(company_url)
                company_name = company_data.get("name", company_name)
            except Exception:
                # Company scrape failed — use basic info from profile
                company_data = {
                    "name": company_name or "Unknown",
                    "description": "",
                    "industry": "",
                    "numberOfEmployees": 0,
                    "followersCount": 0,
                    "website": "",
                    "foundedYear": "",
                    "headquarters": "",
                    "specialties": [],
                    "companySize": "",
                    "recentPosts": [],
                }
            update_job(job_id, company_name=company_name or "Unknown")

        # ── Step 4: Research via Perplexity ──
        update_job(job_id, status="researching", step=4)
        research_data = await research(prospect_name, company_name)

        # ── Step 5: Analyze via Claude ──
        update_job(job_id, status="analyzing", step=5)
        audit_data = await analyze(profile_data, company_data, research_data)

        # Extract metrics from audit
        brand_score = audit_data.get("prospect", {}).get("score", 0)
        personal_gaps = len(audit_data.get("personal_brand_gaps", []))
        company_gaps = len(audit_data.get("company_brand_gaps", []))
        content_gaps = len(audit_data.get("content_strategy_gaps", []))
        total_gaps = personal_gaps + company_gaps + content_gaps

        update_job(job_id, brand_score=brand_score, gap_count=total_gaps)

        # ── Step 6: Generate PDF ──
        update_job(job_id, status="generating", step=6)
        generate_pdf(audit_data, job_id)

        # ── Done ──
        now = datetime.now(timezone.utc).isoformat()
        update_job(job_id, status="complete", completed_at=now)

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        tb = traceback.format_exc()
        print(f"[Pipeline Error] Job {job_id}: {error_msg}\n{tb}")
        update_job(job_id, status="failed", error_msg=error_msg)
