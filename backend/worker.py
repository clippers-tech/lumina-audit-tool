"""worker.py — 7-step pipeline orchestrator for the Lumina marketing audit.

Step 1: Scrape identity profiles (parallel, only provided URLs)
Step 2: Claude derives search terms from identity data
Step 3: Search all 4 platforms for brand mentions (parallel, always all 4)
Step 4: Perplexity researches competitor revenue + CPM (parallel)
Step 5: Claude generates structured audit JSON
Step 6: ReportLab renders branded 6-page PDF
Step 7: Email PDF to prospect + internal notification
"""

import asyncio
import json
import traceback
from datetime import datetime, timezone

from storage import update_job, get_job
from scraper import (
    scrape_linkedin_profile, scrape_youtube_profile,
    scrape_tiktok_profile, scrape_instagram_profile,
    scrape_twitter_profile,
    search_youtube, search_tiktok, search_instagram, search_twitter,
)
from term_deriver import derive_search_terms
from researcher import research
from analyzer import analyze
from pdf_generator import generate_pdf
from emailer import send_prospect_email, send_internal_notification


async def run_pipeline(job_id: str):
    """Execute the full 7-step audit pipeline."""
    job = get_job(job_id)
    if not job:
        return

    identity_data = {}
    search_terms = {}
    search_results = {}
    research_data = {}
    audit_data = {}

    try:
        # ══════════════════════════════════════════════
        # STEP 1 — Scrape identity profiles (parallel)
        # ══════════════════════════════════════════════
        update_job(job_id, status="scraping_identity", step=1)

        tasks = {}
        if job.get("linkedin_url"):
            tasks["linkedin"] = scrape_linkedin_profile(job["linkedin_url"])
        if job.get("youtube_url"):
            tasks["youtube"] = scrape_youtube_profile(job["youtube_url"])
        if job.get("tiktok_url"):
            tasks["tiktok"] = scrape_tiktok_profile(job["tiktok_url"])
        if job.get("instagram_url"):
            tasks["instagram"] = scrape_instagram_profile(job["instagram_url"])
        if job.get("twitter_url"):
            tasks["twitter"] = scrape_twitter_profile(job["twitter_url"])

        if tasks:
            keys = list(tasks.keys())
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for key, result in zip(keys, results):
                if isinstance(result, Exception):
                    print(f"[Worker] Step 1 — {key} scrape failed: {result}")
                    identity_data[key] = {"data_found": False}
                else:
                    identity_data[key] = result

        # Determine person_name from identity data or form
        person_name = job["full_name"]
        for platform in ["linkedin", "youtube", "tiktok", "instagram", "twitter"]:
            pd = identity_data.get(platform, {})
            if pd.get("data_found"):
                found_name = (
                    pd.get("person_name") or pd.get("channel_name") or
                    pd.get("display_name") or pd.get("full_name") or ""
                )
                if found_name:
                    person_name = found_name
                    break

        update_job(job_id, person_name=person_name)

        # ══════════════════════════════════════════════
        # STEP 2 — Derive search terms (Claude)
        # ══════════════════════════════════════════════
        update_job(job_id, status="deriving_terms", step=2)

        search_terms = await derive_search_terms(
            identity_data, job["company_name"], person_name
        )
        update_job(job_id, search_terms=json.dumps(search_terms))

        # ══════════════════════════════════════════════
        # STEP 3 — Search all platforms (parallel, always all 4)
        # ══════════════════════════════════════════════
        update_job(job_id, status="searching_platforms", step=3)

        yt_task = search_youtube(search_terms.get("youtube_query", job["company_name"]))
        tt_task = search_tiktok(search_terms.get("tiktok_query", job["company_name"]))
        ig_task = search_instagram(search_terms.get("instagram_query", job["company_name"]))
        tw_task = search_twitter(search_terms.get("x_query", job["company_name"]))

        yt_res, tt_res, ig_res, tw_res = await asyncio.gather(
            yt_task, tt_task, ig_task, tw_task, return_exceptions=True
        )

        # Handle exceptions gracefully
        if isinstance(yt_res, Exception):
            print(f"[Worker] YouTube search failed: {yt_res}")
            yt_res = {"total_views_48h": 0, "video_count": 0, "top_video_title": "", "top_video_views": 0, "data_found": False}
        if isinstance(tt_res, Exception):
            print(f"[Worker] TikTok search failed: {tt_res}")
            tt_res = {"total_views_48h": 0, "video_count": 0, "top_video_desc": "", "top_video_views": 0, "data_found": False}
        if isinstance(ig_res, Exception):
            print(f"[Worker] Instagram search failed: {ig_res}")
            ig_res = {"total_interactions_48h": 0, "post_count": 0, "estimated_reach": 0, "data_found": False}
        if isinstance(tw_res, Exception):
            print(f"[Worker] Twitter search failed: {tw_res}")
            tw_res = {"total_impressions_48h": 0, "tweet_count": 0, "top_tweet_text": "", "top_tweet_impressions": 0, "data_found": False}

        # Combined views = YouTube views + TikTok views + Instagram reach + Twitter impressions
        combined = (
            yt_res.get("total_views_48h", 0) +
            tt_res.get("total_views_48h", 0) +
            ig_res.get("estimated_reach", 0) +
            tw_res.get("total_impressions_48h", 0)
        )

        search_results = {
            "youtube": yt_res,
            "tiktok": tt_res,
            "instagram": ig_res,
            "x_twitter": tw_res,
            "combined_total_views_48h": combined,
        }

        update_job(job_id, combined_views_48h=combined)

        # ══════════════════════════════════════════════
        # STEP 4 — Research competitor revenue + CPM (parallel)
        # ══════════════════════════════════════════════
        update_job(job_id, status="researching", step=4)

        research_data = await research(
            job.get("competitor_name", ""),
            job.get("industry", ""),
        )

        comp_rev = research_data.get("competitor_revenue", "")
        update_job(job_id, competitor_revenue=comp_rev[:500] if comp_rev else "")

        # ══════════════════════════════════════════════
        # STEP 5 — Claude audit generation
        # ══════════════════════════════════════════════
        update_job(job_id, status="analyzing", step=5)

        form_data = {
            "full_name": job["full_name"],
            "email": job["email"],
            "company_name": job["company_name"],
            "industry": job["industry"],
            "own_revenue": job.get("own_revenue", ""),
            "competitor_name": job.get("competitor_name", ""),
        }

        audit_data = await analyze(identity_data, search_results, research_data, form_data)

        # Extract scores
        vis_score = audit_data.get("prospect", {}).get("visibility_score", 0)
        fit_score = audit_data.get("lumina_fit_score", 0)
        update_job(job_id, visibility_score=vis_score, lumina_fit_score=fit_score)

        # ══════════════════════════════════════════════
        # STEP 6 — Generate PDF
        # ══════════════════════════════════════════════
        update_job(job_id, status="generating", step=6)

        generate_pdf(audit_data, job_id)

        # ══════════════════════════════════════════════
        # STEP 7 — Email PDF + internal notification
        # ══════════════════════════════════════════════
        update_job(job_id, status="sending", step=7)

        first_name = job["full_name"].split()[0] if job["full_name"] else "there"
        import os as _os
        _script_dir = _os.path.dirname(_os.path.abspath(__file__))
        pdf_path = _os.path.join(_script_dir, "outputs", f"{job_id}.pdf")

        # Send prospect email (non-blocking — don't fail pipeline on email errors)
        try:
            await send_prospect_email(
                to_email=job["email"],
                first_name=first_name,
                pdf_path=pdf_path,
            )
        except Exception as e:
            print(f"[Worker] Prospect email failed (non-fatal): {e}")

        # Send internal notification
        try:
            await send_internal_notification(
                name=job["full_name"],
                email=job["email"],
                company=job["company_name"],
                industry=job["industry"],
                own_revenue=job.get("own_revenue", ""),
                competitor=job.get("competitor_name", ""),
                visibility_score=vis_score,
                fit_score=fit_score,
                combined_views=combined,
            )
        except Exception as e:
            print(f"[Worker] Internal notification failed (non-fatal): {e}")

        # ══════════════════════════════════════════════
        # DONE
        # ══════════════════════════════════════════════
        now = datetime.now(timezone.utc).isoformat()
        update_job(job_id, status="complete", completed_at=now)

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        tb = traceback.format_exc()
        print(f"[Pipeline Error] Job {job_id}: {error_msg}\n{tb}")
        update_job(job_id, status="failed", error_msg=error_msg)
