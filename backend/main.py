"""main.py — FastAPI application for the Lumina Clippers Marketing Audit Tool."""

import asyncio
import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from typing import Optional

from storage import init_db, create_job, get_job, get_all_jobs
from worker import run_pipeline
from meta_capi import send_lead_event

# Ensure directories exist
os.makedirs("outputs", exist_ok=True)
os.makedirs("assets", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Lumina Clippers — Marketing Audit Tool", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Model ──

VALID_INDUSTRIES = [
    "SaaS", "E-commerce", "Creator / Personal Brand", "Agency",
    "Fintech", "Health & Wellness", "Real Estate", "Crypto / Web3",
    "Media / Entertainment", "Other",
]


class AuditRequest(BaseModel):
    full_name: str
    email: str
    company_name: str
    industry: str

    # Profile URLs — at least one must be provided
    linkedin_url: Optional[str] = None
    youtube_url: Optional[str] = None
    tiktok_url: Optional[str] = None
    instagram_url: Optional[str] = None
    twitter_url: Optional[str] = None

    # Business context
    own_revenue: Optional[str] = None
    competitor_name: Optional[str] = None

    # Meta Pixel cookies (for Conversions API attribution)
    fbc: Optional[str] = None   # _fbc cookie from browser
    fbp: Optional[str] = None   # _fbp cookie from browser
    event_id: Optional[str] = None  # shared with browser Pixel for dedup


# ── Routes ──

@app.post("/api/audit")
async def create_audit(req: AuditRequest):
    """Accept audit form submission, create job, fire pipeline."""
    # Validate at least one profile URL
    urls = [req.linkedin_url, req.youtube_url, req.tiktok_url,
            req.instagram_url, req.twitter_url]
    if not any(u and u.strip() for u in urls):
        raise HTTPException(
            status_code=422,
            detail="At least one profile URL is required.",
        )

    # Validate industry
    if req.industry not in VALID_INDUSTRIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid industry. Must be one of: {', '.join(VALID_INDUSTRIES)}",
        )

    # Validate required fields
    if not req.full_name.strip():
        raise HTTPException(status_code=422, detail="Full name is required.")
    if not req.email.strip() or "@" not in req.email:
        raise HTTPException(status_code=422, detail="A valid email is required.")
    if not req.company_name.strip():
        raise HTTPException(status_code=422, detail="Company name is required.")

    job_id = str(uuid.uuid4())

    # Clean URL fields — strip whitespace, set empty to None
    def clean_url(val):
        if val and val.strip():
            return val.strip()
        return None

    job_data = {
        "email": req.email.strip(),
        "full_name": req.full_name.strip(),
        "company_name": req.company_name.strip(),
        "industry": req.industry,
        "linkedin_url": clean_url(req.linkedin_url),
        "youtube_url": clean_url(req.youtube_url),
        "tiktok_url": clean_url(req.tiktok_url),
        "instagram_url": clean_url(req.instagram_url),
        "twitter_url": clean_url(req.twitter_url),
        "own_revenue": (req.own_revenue or "").strip() or None,
        "competitor_name": (req.competitor_name or "").strip() or None,
    }

    create_job(job_id, job_data)

    # Fire background pipeline
    asyncio.create_task(run_pipeline(job_id))

    # Send Lead event to Meta Conversions API (non-blocking)
    asyncio.create_task(
        send_lead_event(
            email=req.email.strip(),
            full_name=req.full_name.strip(),
            source_url="https://audits.luminaclippers.com",
            fbc=req.fbc,
            fbp=req.fbp,
            event_id=req.event_id,
        )
    )

    return JSONResponse({
        "job_id": job_id,
        "status": "queued",
        "email": req.email.strip(),
    })


@app.get("/api/status/{job_id}")
async def status_endpoint(job_id: str):
    """Return current status and step for a job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(job)


@app.get("/api/jobs")
async def jobs_endpoint():
    """Return all jobs (admin endpoint)."""
    jobs = get_all_jobs()
    return JSONResponse(jobs)


@app.get("/api/download/{job_id}")
async def download_endpoint(job_id: str):
    """Return the generated PDF file."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "complete":
        raise HTTPException(status_code=422, detail="Audit not complete yet")

    filepath = os.path.join("outputs", f"{job_id}.pdf")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="PDF file not found")

    name = (job.get("full_name") or "audit").replace(" ", "_")
    filename = f"Lumina_Audit_{name}.pdf"

    return FileResponse(
        filepath,
        media_type="application/pdf",
        filename=filename,
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/health")
async def health_root():
    return {"status": "ok"}


# Serve static files last so they don't override API routes
app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
