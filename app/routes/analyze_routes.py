# app/routes/analyze_routes.py
from fastapi import APIRouter, Form, UploadFile, File, HTTPException, Depends
from app.controllers.ai_analyze import analyze_frame
from app.models.interview_candidate_details import InterviewCandidateDetails
from sqlalchemy.orm import Session
from app.config.auth import get_current_user
from app.config.database import get_db

router = APIRouter(tags=["AI Frame Analysis"])


@router.post("/analyze_frame/")
async def ai_analyze_frame(candidate_id: str = Form(...), frame: UploadFile = File(...),current_user: InterviewCandidateDetails = Depends(get_current_user),
    db: Session = Depends(get_db)):
    """Route for analyzing webcam frame"""
    try:
        return await analyze_frame(candidate_id, frame, current_user, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
