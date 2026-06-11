import requests
import json
import os
from datetime import date
from bs4 import BeautifulSoup

today = str(date.today())
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_existing(path="devops_jobs.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_jobs(jobs, path="devops_jobs.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved {len(jobs)} jobs to {path}")

def dedup(existing, new_jobs):
    """Keep existing jobs, add only new ones by URL."""
    seen_urls = {j.get("url") for j in existing if j.get("url")}
    added = 0
    for job in new_jobs:
        if job.get("url") not in seen_urls:
            existing.append(job)
            seen_urls.add(job.get("url"))
            added += 1
    print(f"  → {added} new jobs added (duplicates skipped)")
    return existing

# ── JSearch (LinkedIn + Indeed via RapidAPI) ──────────────────────────────────

JSEARCH_URL = "https://jsearch.p.rapidapi.com/search"
JSEARCH_HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
}

JSEARCH_QUERIES = [
    # Remote - open to Africa
    {"query": "DevOps Engineer remote Africa",          "remote": True},
    {"query": "Cloud Engineer remote Africa",           "remote": True},
    {"query": "Site Reliability Engineer remote Africa","remote": True},
    {"query": "Platform Engineer remote Africa",        "remote": True},
    {"query": "DevSecOps Engineer remote Africa",       "remote": True},
    # Physical - Cameroon
    {"query": "DevOps Engineer Cameroon",               "remote": False},
    {"query": "Cloud Engineer Cameroon",                "remote": False},
    {"query": "IT Infrastructure Engineer Cameroon",    "remote": False},
]

def scrape_jsearch():
    jobs = []
    for q in JSEARCH_QUERIES:
        print(f"  JSearch: {q['query']}")
        try:
            params = {"query": q["query"], "page": "1", "num_pages": "2", "date_posted": "month"}
            resp = requests.get(JSEARCH_URL, headers=JSEARCH_HEADERS, params=params, timeout=15)
            data = resp.json()
            for j in data.get("data", []):
                jobs.append({
                    "title":        j.get("job_title", ""),
                    "company":      j.get("employer_name", ""),
                    "location":     f"{j.get('job_city', '')} {j.get('job_country', '')}".strip(),
                    "salary":       _jsearch_salary(j),
                    "url":          j.get("job_apply_link") or j.get("job_google_link", ""),
                    "company_url":  j.get("employer_website", ""),
                    "source":       "linkedin" if "linkedin" in (j.get("job_apply_link") or "") else "jsearch",
                    "description":  j.get("job_description", "")[:600],
                    "remote":       j.get("job_is_remote", q["remote"]),
                    "date_scraped": today,
                })
        except Exception as e:
            print(f"    ⚠️ JSearch error: {e}")
    print(f"  JSearch total: {len(jobs)} jobs")
    return jobs

def _jsearch_salary(j):
    mn = j.get("job_min_salary")
    mx = j.get("job_max_salary")
    period = j.get("job_salary_period", "")
    if mn and mx:
        return f"{mn}–{mx} {period}".strip()
    if mn:
        return f"From {mn} {period}".strip()
    return "Not specified"

# ── We Work Remotely ──────────────────────────────────────────────────────────

WWR_FEEDS = [
    "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
    "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
]

AFRICA_KEYWORDS = ["africa", "cameroon", "nigeria", "kenya", "ghana", "worldwide",
                   "anywhere", "global", "remote", "all timezones", "emea"]

def scrape_weworkremotely():
    jobs = []
    for feed_url in WWR_FEEDS:
        print(f"  WWR: {feed_url}")
        try:
            resp = requests.get(feed_url, timeout=15)
            soup = BeautifulSoup(resp.content, "xml")
            for item in soup.find_all("item"):
                title    = item.find("title").text if item.find("title") else ""
                link     = item.find("link").text if item.find("link") else ""
                desc     = item.find("description").text if item.find("description") else ""
                region   = item.find("region").text.lower() if item.find("region") else ""
                pub_date = item.find("pubDate").text[:10] if item.find("pubDate") else today

                # Filter: DevOps / Cloud / SRE titles only
                title_lower = title.lower()
                if not any(kw in title_lower for kw in [
                    "devops", "cloud", "sre", "reliability", "infrastructure",
                    "platform engineer", "devsecops", "kubernetes", "terraform"
                ]):
                    continue

                # Filter: Africa-friendly or worldwide
                region_text = (region + " " + desc).lower()
                if not any(kw in region_text for kw in AFRICA_KEYWORDS):
                    continue

                clean_desc = BeautifulSoup(desc, "html.parser").get_text()[:600]
                jobs.append({
                    "title":        title.split(" at ")[0].strip() if " at " in title else title,
                    "company":      title.split(" at ")[1].strip() if " at " in title else "",
                    "location":     region.title() or "Remote",
                    "salary":       "Not specified",
                    "url":          link,
                    "company_url":  "",
                    "source":       "weworkremotely",
                    "description":  clean_desc,
                    "remote":       True,
                    "date_scraped": today,
                })
        except Exception as e:
            print(f"    ⚠️ WWR error: {e}")
    print(f"  WWR total: {len(jobs)} jobs")
    return jobs

# ── Glassdoor (via JSearch fallback query) ────────────────────────────────────

def scrape_glassdoor():
    """Glassdoor blocks direct scraping; we pull their listings via JSearch."""
    jobs = []
    queries = [
        "DevOps Engineer remote site:glassdoor.com",
        "Cloud Engineer Cameroon site:glassdoor.com",
    ]
    for q in queries:
        print(f"  Glassdoor (via JSearch): {q}")
        try:
            params = {"query": q, "page": "1", "num_pages": "1", "date_posted": "month"}
            resp = requests.get(JSEARCH_URL, headers=JSEARCH_HEADERS, params=params, timeout=15)
            data = resp.json()
            for j in data.get("data", []):
                jobs.append({
                    "title":        j.get("job_title", ""),
                    "company":      j.get("employer_name", ""),
                    "location":     f"{j.get('job_city','')} {j.get('job_country','')}".strip(),
                    "salary":       _jsearch_salary(j),
                    "url":          j.get("job_apply_link") or j.get("job_google_link", ""),
                    "company_url":  j.get("employer_website", ""),
                    "source":       "glassdoor",
                    "description":  j.get("job_description", "")[:600],
                    "remote":       j.get("job_is_remote", False),
                    "date_scraped": today,
                })
        except Exception as e:
            print(f"    ⚠️ Glassdoor error: {e}")
    print(f"  Glassdoor total: {len(jobs)} jobs")
    return jobs

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 CloudOps Job Scraper starting...")
    print(f"📅 Date: {today}\n")

    existing = load_existing()
    print(f"📂 Existing jobs loaded: {len(existing)}\n")

    print("🔍 Scraping JSearch (LinkedIn + Indeed)...")
    jsearch_jobs = scrape_jsearch()

    print("\n🔍 Scraping We Work Remotely...")
    wwr_jobs = scrape_weworkremotely()

    print("\n🔍 Scraping Glassdoor (via JSearch)...")
    glassdoor_jobs = scrape_glassdoor()

    all_new = jsearch_jobs + wwr_jobs + glassdoor_jobs
    print(f"\n📊 Total new jobs scraped: {len(all_new)}")

    final = dedup(existing, all_new)
    save_jobs(final)
    print(f"\n✅ Done! Total unique jobs in file: {len(final)}")
