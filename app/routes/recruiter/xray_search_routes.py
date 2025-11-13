from fastapi import APIRouter, Form, HTTPException, Request, Depends, Body
from app.controllers.xray_search import xray_search
from app.models.xray_search import XRaySearchRequest
from sqlalchemy.orm import Session
from app.config.database import SessionLocal, get_db
from app.config.recruiter_auth import create_access_token, get_current_user

router = APIRouter(tags=["Recruiter Authentication"])

# @router.post("/xray_search/")
# def getProfiles(role: str, location: str):
#     return xray_search(role,location)

@router.post("/xray_search/")
def getProfiles(body: XRaySearchRequest):
    """
    Accepts JSON Body:
    {
        "role": "Python Developer",
        "location": "Hyderabad",
        "skills": "Django, APIs",
        "company": "TCS",
        "min_exp": 3,
        "max_exp": 8,
        "pages": 3
    }
    """
    try:
        return xray_search(body.dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
