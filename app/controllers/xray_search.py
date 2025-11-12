# app/controllers/xray_search.py
from fastapi import APIRouter, Form, HTTPException
import requests, os, concurrent.futures
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# Base Serper API URL
SERPER_URL = "https://google.serper.dev/search"

# Common headers for Serper API
HEADERS = {
    "X-API-KEY": SERPER_API_KEY,
    "Content-Type": "application/json"
}

# Supported platforms
PLATFORMS = {
    "LinkedIn": "site:linkedin.com/in",
    "GitHub": "site:github.com",
    "Stack Overflow": "site:stackoverflow.com/users",
    "Indeed": "site:indeed.com/profile",
    "Naukri": "site:naukri.com",
    "HackerRank": "site:hackerrank.com/profile"
}

def fetch_platform_results(platform_name, query):
    """Helper to perform search on one platform"""
    try:
        payload = {"q": query, "num": 10}
        response = requests.post(SERPER_URL, headers=HEADERS, json=payload)
        if response.status_code != 200:
            return []

        data = response.json()
        results = []
        for item in data.get("organic", []):
            results.append({
                "platform": platform_name,
                "title": item.get("title"),
                "profile_url": item.get("link"),
                "summary": item.get("snippet", "")
            })
        return results

    except Exception as e:
        print(f"⚠️ Error fetching {platform_name}: {e}")
        return []


def xray_search(role: str, location: str):
    """Perform X-Ray search across multiple job platforms."""
    if not SERPER_API_KEY:
        raise HTTPException(status_code=500, detail="Missing SERPER_API_KEY environment variable")

    try:
        # Build search queries per platform
        queries = {
            name: f'{pattern} ("{role}") "{location}" -jobs -hiring'
            for name, pattern in PLATFORMS.items()
        }

        all_results = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(fetch_platform_results, name, query): name
                for name, query in queries.items()
            }

            for future in concurrent.futures.as_completed(futures):
                platform = futures[future]
                try:
                    result = future.result()
                    all_results.extend(result)
                except Exception as e:
                    print(f"Error from {platform}: {e}")

        # Deduplicate profiles by URL
        unique_profiles = {p["profile_url"]: p for p in all_results}.values()

        return {
            "status": "success",
            "role": role,
            "location": location,
            "total_platforms_checked": len(PLATFORMS),
            "total_results": len(unique_profiles),
            "profiles": list(unique_profiles)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
