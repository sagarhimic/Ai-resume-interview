# app/controllers/xray_search.py
from fastapi import HTTPException
import requests, os, concurrent.futures, re
from dotenv import load_dotenv

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not SERPER_API_KEY:
    raise Exception("❌ Missing SERPER_API_KEY in environment variables")

SERPER_URL = "https://google.serper.dev/search"

HEADERS = {
    "X-API-KEY": SERPER_API_KEY,
    "Content-Type": "application/json",
}

PLATFORMS = {
    "LinkedIn": "site:linkedin.com/in",
    "GitHub": "site:github.com",
    "StackOverflow": "site:stackoverflow.com/users",
    "Indeed": "site:indeed.com/profile",
    "Naukri": "site:naukri.com",
    "HackerRank": "site:hackerrank.com/profile",
}

# -------------------------
# Extract Experience Helper
# -------------------------
def extract_experience(text: str):
    if not text:
        return None

    patterns = [
        r"(\d+)\+?\s*years",
        r"(\d+)\s*yrs",
        r"(\d+)\s*yr",
        r"(\d+)\s*\+?\s*experience"
    ]

    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except:
                return None
    return None

# -------------------------
# Fetch results for a platform
# -------------------------
def fetch_platform_results(platform_name: str, query: str, pages: int):
    all_results = []

    for page in range(1, pages + 1):
        payload = {
            "q": query,
            "num": 10,
            "page": page
        }

        try:
            resp = requests.post(SERPER_URL, headers=HEADERS, json=payload)
            if resp.status_code != 200:
                continue

            data = resp.json()
            organic = data.get("organic", [])

            for item in organic:
                all_results.append({
                    "platform": platform_name,
                    "title": item.get("title"),
                    "profile_url": item.get("link"),
                    "summary": item.get("snippet", "")
                })

        except Exception as e:
            print(f"⚠️ Error in {platform_name}: {e}")

    return all_results

def build_skill_query(skills: str):
    if not skills:
        return ""

    skill_list = [s.strip() for s in skills.split(",") if s.strip()]

    # AND logic -> more accurate
    and_query = " ".join(f'"{s}"' for s in skill_list)

    # OR logic -> more results
    or_query = "(" + " OR ".join(f'"{s}"' for s in skill_list) + ")"

    return f"{and_query} {or_query}"

# -------------------------
# MAIN X-RAY SEARCH FUNCTION
# -------------------------
def xray_search(req: dict):

    role = req.get("role")
    location = req.get("location")
    skills = req.get("skills", "")
    company = req.get("company", "")
    min_exp = int(req.get("min_exp", 0))
    max_exp = int(req.get("max_exp", 40))
    pages = int(req.get("pages", 2))

    if not role or not location:
        raise HTTPException(status_code=400, detail="role & location are required")

    skill_query = build_skill_query(skills)

    # Build search queries
    queries = {
        platform: f'{pattern} ("{role}") "{location}" "{skill_query}" "{company}" -jobs -hiring'
        for platform, pattern in PLATFORMS.items()
    }

    all_results = []

    # Multi-threading for speed
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(fetch_platform_results, platform, query, pages): platform
            for platform, query in queries.items()
        }

        for future in concurrent.futures.as_completed(futures):
            platform = futures[future]
            try:
                results = future.result()
                all_results.extend(results)
            except Exception as e:
                print(f"❌ Error from {platform}: {e}")

    # Deduplicate by URL
    unique_profiles = {p["profile_url"]: p for p in all_results}.values()

    # EXPERIENCE FILTER
    filtered = []
    for p in unique_profiles:
        summary = p.get("summary", "")
        title = p.get("title", "")

        exp = extract_experience(summary) or extract_experience(title)
        p["experience_years"] = exp

        if exp is None:
            filtered.append(p)  # optional keep
        else:
            if min_exp <= exp <= max_exp:
                filtered.append(p)

    return {
        "status": "success",
        "role": role,
        "location": location,
        "skills": skills,
        "company": company,
        "exp_range": f"{min_exp} - {max_exp}",
        "total_before_filter": len(unique_profiles),
        "total_after_filter": len(filtered),
        "profiles": filtered
    }
