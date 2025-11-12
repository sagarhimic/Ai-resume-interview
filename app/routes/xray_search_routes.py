from fastapi import APIRouter, Form, HTTPException, Request, Depends
from app.controllers.xray_search import xray_search
from sqlalchemy.orm import Session
from app.config.database import SessionLocal, get_db
from app.config.auth import create_access_token, get_current_user

router = APIRouter()

@router.post("/xray_search/")

async def getProfiles(role: str = Form(...), location: str = Form(...)):
    return await xray_search(role, location)
