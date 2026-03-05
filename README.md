# Lumina Clippers — LinkedIn Audit Tool

Automated LinkedIn brand audit pipeline for sales prospecting. Paste a LinkedIn profile URL; the tool scrapes the profile and company page, researches the prospect online, analyzes gaps with Claude, and generates a branded dark-theme PDF report.

## Stack

- **Backend**: FastAPI + Python (Apify, Perplexity, Anthropic Claude, ReportLab)
- **Frontend**: Vanilla HTML/CSS/JS (dark theme, no build step)
- **Database**: SQLite (job persistence)
- **Deploy**: Render (backend), Vercel (frontend)

## Setup

1. Copy `backend/.env.example` to `backend/.env` and fill in your API keys:
   - `APIFY_TOKEN` — for LinkedIn scraping
   - `ANTHROPIC_API_KEY` — for Claude analysis
   - `PERPLEXITY_API_KEY` — for web research
   - `LI_COOKIES` — optional LinkedIn cookies JSON for company scraping

2. Install dependencies:
   ```bash
   cd backend && pip install -r requirements.txt
   ```

3. Run locally:
   ```bash
   cd backend && uvicorn main:app --reload
   ```

4. Open `frontend/index.html` in a browser (or serve with any static server).

## Deploy

- **Backend**: Connect repo to Render, use `render.yaml` (set env vars in dashboard)
- **Frontend**: Connect `frontend/` folder to Vercel
