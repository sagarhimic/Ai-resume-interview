from fastapi import APIRouter, Form, HTTPException, Request, Depends
from app.controllers.candidate_info import get_candidate_info
from sqlalchemy.orm import Session
from app.config.database import SessionLocal, get_db
from app.config.auth import create_access_token, get_current_user

router = APIRouter()

@router.get("/candidate/{candidate_id}")

def getUser(candidate_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return get_candidate_info(candidate_id,db)
