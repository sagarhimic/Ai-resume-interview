# app/controllers/xray_search.py
from fastapi import HTTPException
import requests
import os
import concurrent.futures
import re
from dotenv import load_dotenv
from typing import List

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
if not SERPER_API_KEY:
    raise Exception("❌ Missing SERPER_API_KEY in environment variables")

SERPER_URL = "https://google.serper.dev/search"
HEADERS = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}

DOMAIN_TO_PLATFORM = {
    "linkedin.com": "LinkedIn",
    "www.linkedin.com": "LinkedIn",
    "In.Linkedin.Com" : "LinkedIn",
    "github.com": "GitHub",
    "www.github.com": "GitHub",
    "stackoverflow.com": "StackOverflow",
    "www.stackoverflow.com": "StackOverflow",
    "indeed.com": "Indeed",
    "www.indeed.com": "Indeed",
    "naukri.com": "Naukri",
    "www.naukri.com": "Naukri",
    "hackerrank.com": "HackerRank",
    "www.hackerrank.com": "HackerRank",
}

def extract_platform_name(url: str):
    """Extract clean platform name from URL and normalize subdomains."""
    if not url or "/" not in url:
        return "Unknown"

    domain = url.split("/")[2].lower()  # example: in.linkedin.com

    # Handle LinkedIn country domains (in.linkedin.com, uk.linkedin.com, etc.)
    if "linkedin.com" in domain:
        return "LinkedIn"

    if "github.com" in domain:
        return "GitHub"

    if "stackoverflow.com" in domain:
        return "StackOverflow"

    if "indeed.com" in domain:
        return "Indeed"

    if "naukri.com" in domain:
        return "Naukri"

    if "hackerrank.com" in domain:
        return "HackerRank"

    # Default: return clean domain
    return domain.replace("www.", "").title()

PLATFORMS = {
    "LinkedIn": "site:linkedin.com/in",
    "GitHub": "site:github.com",
    "StackOverflow": "site:stackoverflow.com/users",
    "Indeed": "site:indeed.com/profile",
    "Naukri": "site:naukri.com",
    "HackerRank": "site:hackerrank.com/profile",
}

# -------------------------
# Experience extraction
# -------------------------
def extract_experience(text: str):
    if not text:
        return None
    patterns = [
        r"(\d+)\+?\s*years",
        r"(\d+)\s*yrs",
        r"(\d+)\s*yr",
        r"(\d+)\s*\+?\s*experience",
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
# Helpers for skill/company/location query parts
# -------------------------
def build_skill_query(skills: str):
    """Return a combined AND+OR skill query that works reliably with Serper/Google."""
    if not skills:
        return ""
    skill_list = [s.strip() for s in re.split(r',|\|', skills) if s.strip()]
    if not skill_list:
        return ""
    # AND part: "skill1" "skill2" ...
    and_part = " ".join(f'"{s}"' for s in skill_list)
    # OR part: ("skill1" OR "skill2" OR ...)
    or_part = "(" + " OR ".join(f'"{s}"' for s in skill_list) + ")"
    return f"{and_part} {or_part}"

# small company alias mapping; dynamic fallback used when not found
COMPANY_MAPPING = {
    "tcs": ["TCS", "Tata Consultancy Services"],
    "infosys": ["Infosys", "Infosys Ltd"],
    "wipro": ["Wipro", "Wipro Technologies"],
    "cognizant": ["Cognizant", "Cognizant Technology Solutions"],
    "hcl": ["HCL", "HCL Technologies"],
    "accenture": ["Accenture", "Accenture Solutions"],
    "deloitte": ["Deloitte", "Deloitte Consulting"],
}

def build_company_query(company: str):
    if not company:
        return ""
    key = company.strip().lower()
    if key in COMPANY_MAPPING:
        vals = COMPANY_MAPPING[key]
        return "(" + " OR ".join(f'"{v}"' for v in vals) + ")"
    # default: quote the name (can be multi-word)
    return f'"{company.strip()}"'

# Basic country list to detect if the location is a country or city
COMMON_COUNTRIES = {
    "india", "united states", "usa", "canada", "uk", "united kingdom", "uae", "australia",
    "singapore", "germany", "france", "brazil", "south africa", "qatar", "saudi arabia",
    "uae", "netherlands", "switzerland"
}

def is_country(location: str) -> bool:
    if not location:
        return False
    loc = location.strip().lower()
    # treat multi-word (e.g., "united states") or exact matches
    return loc in COMMON_COUNTRIES or len(loc.split()) > 1 and any(c in loc for c in COMMON_COUNTRIES)

def build_location_query(location: str):
    """
    Build a dynamic location fragment. Works for city or country.
    If the location is a country (detected), we search the country and avoid excluding it.
    If location is a city, we build variants and exclude common foreign countries to reduce noise.
    """
    if not location:
        return ""
    loc = location.strip()
    city_like = not is_country(loc)

    if city_like:
        # city-focused: allow variants, exclude unrelated countries
        exclude = [
            "USA", "United States", "Canada", "UK", "United Kingdom", "UAE",
            "Saudi", "Qatar", "Bahrain", "Australia", "New Zealand",
            "Singapore", "South Africa"
        ]
        exclude_part = " ".join(f'-"{c}"' for c in exclude if c.lower() != loc.lower())
        return (
            "("
            f'"{loc}" OR "{loc} City" OR "{loc} Area" OR "{loc}, {loc}" OR "near {loc}"'
            ") "
            f"{exclude_part}"
        )
    else:
        # country-focused: search country and common synonyms (do not exclude country)
        return f'("{loc}" OR "{loc.title()}" OR "{loc.upper()}")'

# -------------------------
# Serper fetch logic
# -------------------------
def fetch_serper_results(query: str, pages: int = 1) -> List[dict]:
    results = []
    for page in range(1, max(1, pages) + 1):
        payload = {"q": query, "num": 10, "page": page}
        try:
            resp = requests.post(SERPER_URL, headers=HEADERS, json=payload, timeout=12)
        except Exception as e:
            # network/timeout — skip this page
            print("⚠️ Serper request error:", e)
            continue
        if resp.status_code != 200:
            # skip if not ok
            continue
        try:
            data = resp.json()
        except:
            continue
        organic = data.get("organic", []) or []
        for item in organic:
            results.append({
                "title": item.get("title"),
                "profile_url": item.get("link"),
                "summary": item.get("snippet", "")
            })
    return results

# -------------------------
# Matching & scoring
# -------------------------
def compute_match_score(profile: dict, role: str, location: str, skill_list: List[str], company_variants: List[str], min_exp: int, max_exp: int):
    """
    score weights:
     - location match: 3
     - role match: 2
     - company match: 2
     - each skill match: 1
     - experience in range: +1
    """
    text = " ".join([profile.get("title", ""), profile.get("summary", "")]).lower()
    matched = {"location": False, "role": False, "company": False, "skills": []}
    score = 0

    # location
    if location and location.lower() in text:
        score += 3
        matched["location"] = True

    # role: check presence of main role tokens
    if role:
        role_tokens = [t.strip().lower() for t in re.split(r'[/,|-]|\s+', role) if t.strip()]
        # require at least one meaningful token
        role_found = any(tok in text for tok in role_tokens if len(tok) > 2)
        if role_found:
            score += 2
            matched["role"] = True

    # company
    if company_variants:
        for c in company_variants:
            if c.strip('"').lower() in text:
                score += 2
                matched["company"] = True
                break

    # skills
    for s in skill_list:
        if s.lower() in text:
            score += 1
            matched["skills"].append(s)

    # experience
    exp = extract_experience(text)
    if exp is not None:
        profile["experience_years"] = exp
        if min_exp <= exp <= max_exp:
            score += 1
    else:
        profile["experience_years"] = None

    profile["_match_score"] = score
    profile["_matched_fields"] = matched
    return profile

# -------------------------
# Build multiple query variations & orchestrate fetch
# -------------------------
def build_query_variations(pattern: str, role: str, location: str, skill_query: str, company_query: str):
    """
    Create several variants from strict to relaxed to improve SERP coverage.
    Returns list of query strings.
    """
    queries = []

    # strict: role + location + skills + company
    q_strict = f'{pattern} "{role}" {build_location_query(location)} {skill_query} {company_query} -jobs -hiring -recruiter'
    queries.append(q_strict)

    # relaxed1: role + location + skills
    q_relaxed1 = f'{pattern} "{role}" {build_location_query(location)} {skill_query} -jobs -hiring'
    queries.append(q_relaxed1)

    # relaxed2: role + skills + location (no quotes around role)
    q_relaxed2 = f'{pattern} {role} {skill_query} {build_location_query(location)} -jobs -hiring'
    queries.append(q_relaxed2)

    # skills-only + location fallback
    q_skills = f'{pattern} {skill_query} {build_location_query(location)} -jobs -hiring'
    queries.append(q_skills)

    # role-only + company
    q_role_company = f'{pattern} "{role}" {company_query} {build_location_query(location)} -jobs -hiring'
    queries.append(q_role_company)

    # last fallback: role + location only
    q_role_loc = f'{pattern} "{role}" {build_location_query(location)} -jobs -hiring'
    queries.append(q_role_loc)

    # remove empty duplicates
    clean_queries = []
    seen = set()
    for q in queries:
        q = " ".join(q.split())
        if q and q not in seen:
            seen.add(q)
            clean_queries.append(q)
    return clean_queries

# -------------------------
# MAIN X-RAY SEARCH FUNCTION
# -------------------------
def xray_search(req: dict):
    role = (req.get("role") or "").strip()
    location = (req.get("location") or "").strip()
    skills = (req.get("skills") or "").strip()
    company = (req.get("company") or "").strip()
    min_exp = int(req.get("min_exp", 0))
    max_exp = int(req.get("max_exp", 40))
    pages = int(req.get("pages", 2))
    page = int(req.get("page", 1))
    limit = int(req.get("limit", 20))

    if not role or not location:
        raise HTTPException(status_code=400, detail="role & location are required")

    # prepare skill/company tokens
    skill_list = [s.strip() for s in re.split(r',|\|', skills) if s.strip()]
    skill_query = build_skill_query(skills)
    company_query = build_company_query(company) if company else ""

    # For company match checks, create simple variants (unquoted)
    company_variants = []
    if company:
        key = company.strip().lower()
        if key in COMPANY_MAPPING:
            company_variants = COMPANY_MAPPING[key]
        else:
            company_variants = [company.strip()]

    # Run queries across platforms with multiple variations (parallel)
    all_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(PLATFORMS) * 3)) as executor:
        future_to_query = {}
        for platform, pattern in PLATFORMS.items():
            q_variations = build_query_variations(pattern, role, location, skill_query, company_query)
            # submit each variation
            for q in q_variations:
                future = executor.submit(fetch_serper_results, q, pages)
                future_to_query[future] = q

        # gather results
        for future in concurrent.futures.as_completed(future_to_query):
            try:
                res = future.result()
                if res:
                    all_results.extend(res)
            except Exception as e:
                # ignore single query failures
                print("⚠️ query/fetch error:", e)

    # deduplicate by profile_url
    unique_map = {}
    for item in all_results:
        url = item.get("profile_url")
        if not url:
            continue

        platform_name = extract_platform_name(url)

        if url not in unique_map:
            unique_map[url] = {
                "title": item.get("title"),
                "profile_url": url,
                "summary": item.get("summary"),
                "platforms": [platform_name]
            }
        else:
            # aggregate platforms or snippets if necessary
            if platform_name not in unique_map[url]["platforms"]:
                unique_map[url]["platforms"].append(platform_name)

    unique_profiles = list(unique_map.values())

    # compute match scores and filter by experience range optionally
    scored = []
    for p in unique_profiles:
        scored_profile = compute_match_score(p, role, location, skill_list, company_variants, min_exp, max_exp)
        # keep even if location not found but score will be lower - UI can filter by score threshold if needed
        scored.append(scored_profile)

    # sort by score desc, then by experience desc (if present)
    def sort_key(x):
        return (x.get("_match_score", 0), x.get("experience_years") or 0)
    scored_sorted = sorted(scored, key=sort_key, reverse=True)

    # Optional: if user insisted on location-only strict results, we could filter matched location True (but keep flexible by default)

    # PAGINATION on scored_sorted
    total_results = len(scored_sorted)
    total_pages = (total_results + limit - 1) // limit if limit > 0 else 1
    # clamp page
    page = max(1, min(page, total_pages or 1))
    start = (page - 1) * limit
    end = start + limit
    paginated = scored_sorted[start:end]

    # Prepare friendly response (strip internal keys but keep score info)
    profiles_out = []
    for p in paginated:
        profiles_out.append({
            "title": p.get("title"),
            "profile_url": p.get("profile_url"),
            "summary": p.get("summary"),
            "platforms": p.get("platforms", []),
            "experience_years": p.get("experience_years"),
            "match_score": p.get("_match_score", 0),
            "matched_fields": p.get("_matched_fields", {})
        })

    return {
        "status": "success",
        "role": role,
        "location": location,
        "skills": skills,
        "company": company,
        "exp_range": f"{min_exp} - {max_exp}",
        "total_before_filter": len(all_results),
        "total_unique_profiles": total_results,
        # pagination metadata
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "profiles": profiles_out
    }
