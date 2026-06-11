# CloudOps Community – Job Scraper

Automatically scrapes DevOps and Cloud Engineering jobs daily from LinkedIn (via JSearch), We Work Remotely, and Glassdoor.

## Filters
- **Remote jobs** – open to Africa (worldwide/EMEA/Africa-specific roles)
- **On-site jobs** – Cameroon only

## Sources
| Source | Method |
|--------|--------|
| LinkedIn | JSearch API (RapidAPI) |
| Indeed | JSearch API (RapidAPI) |
| We Work Remotely | RSS Feed |
| Glassdoor | JSearch API (RapidAPI) |

## Schedule
Runs automatically every day at **6AM UTC (7AM WAT)** via GitHub Actions.
You can also trigger it manually from the **Actions** tab → **Daily Job Scraper** → **Run workflow**.

## Setup

### 1. Add your RapidAPI key as a GitHub Secret
- Go to your repo → **Settings** → **Secrets and variables** → **Actions**
- Click **New repository secret**
- Name: `RAPIDAPI_KEY`
- Value: your RapidAPI key

### 2. That's it!
The scraper runs daily and commits the updated `devops_jobs.json` automatically.

## Output
Results are saved to `devops_jobs.json` in the root of this repo.
Each job entry looks like:
```json
{
  "title": "DevOps Engineer",
  "company": "Acme Corp",
  "location": "Remote",
  "salary": "Not specified",
  "url": "https://...",
  "source": "linkedin",
  "description": "...",
  "remote": true,
  "date_scraped": "2026-06-11"
}
```
