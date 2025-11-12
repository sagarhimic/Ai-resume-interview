# app/controllers/xray_search.py
from fastapi import APIRouter, Form, HTTPException
import requests
import os

router = APIRouter(tags=["X-Ray Search"])

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

async def xray_search(role: str = Form(...), location: str = Form(...)):
    """
    Perform AI-based X-Ray search for candidate profiles.
    """
    try:
        # Build dynamic Boolean query
        query = f'site:linkedin.com/in ("{role}") "{location}" -jobs -hiring'

        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }

        payload = {
            "q": query,
            "num": 10  # number of results
        }

        resp = requests.post("https://google.serper.dev/search", headers=headers, json=payload)
        data = resp.json()

        results = []
        for item in data.get("organic", []):
            link = item.get("link")
            title = item.get("title")
            snippet = item.get("snippet")

            results.append({
                "name": title.split(" - ")[0] if title else None,
                "role": role,
                "location": location,
                "profile_url": link,
                "summary": snippet
            })

        return {
            "status": "success",
            "query": query,
            "results_found": len(results),
            "profiles": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
