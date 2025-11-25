from fastapi import APIRouter, Form, HTTPException, Request, Depends
from app.controllers.login import userLogin
from sqlalchemy.orm import Session
from app.config.database import SessionLocal, get_db

router = APIRouter(tags=["Candidate Interview"])

@router.post("/login/")

def authentication(meeting_id: str = Form(...),password: str = Form(...),db: Session = Depends(get_db)):
    return userLogin(meeting_id,password,db)
