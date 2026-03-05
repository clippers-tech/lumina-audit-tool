"""main.py — FastAPI application for the Lumina Clippers LinkedIn Audit Tool."""

import asyncio
import os
import re
import uuid
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()  # Load .env file if present

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from storage import init_db, create_job, get_job, get_all_jobs, update_job
from worker import run_pipeline

# Ensure outputs directory exists
os.makedirs("outputs", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Lumina Audit Tool", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ──

class AnalyzeRequest(BaseModel):
    url: str


# ── LinkedIn URL validation ──

LINKEDIN_PATTERN = re.compile(
    r"^https?://(www\.)?linkedin\.com/in/[\w\-%.]+/?$",
    re.IGNORECASE,
)


def validate_linkedin_url(url: str) -> str:
    """Validate and normalise a LinkedIn profile URL."""
    url = url.strip().rstrip("/")
    # Remove query params
    if "?" in url:
        url = url.split("?")[0]
    if not LINKEDIN_PATTERN.match(url):
        raise ValueError(
            "Invalid LinkedIn profile URL. Expected format: "
            "https://www.linkedin.com/in/username"
        )
    return url


# ── Routes ──

@app.post("/analyze")
async def analyze_endpoint(req: AnalyzeRequest):
    """Accept a LinkedIn URL, create a job, and fire the pipeline."""
    try:
        url = validate_linkedin_url(req.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    job_id = str(uuid.uuid4())
    job = create_job(job_id, url)

    # Fire background task
    asyncio.create_task(run_pipeline(job_id, url))

    return JSONResponse({"job_id": job_id, "status": "queued"})


@app.get("/status/{job_id}")
async def status_endpoint(job_id: str):
    """Return current status and step for a job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(job)


@app.get("/jobs")
async def jobs_endpoint():
    """Return all jobs for the dashboard."""
    jobs = get_all_jobs()
    return JSONResponse(jobs)


@app.get("/download/{job_id}")
async def download_endpoint(job_id: str):
    """Return the generated PDF file."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "complete":
        raise HTTPException(status_code=422, detail="Job not complete yet")

    filepath = os.path.join("outputs", f"{job_id}.pdf")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="PDF file not found")

    prospect_name = (job.get("prospect_name") or "audit").replace(" ", "_")
    filename = f"Lumina_Audit_{prospect_name}.pdf"

    return FileResponse(
        filepath,
        media_type="application/pdf",
        filename=filename,
    )


# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
