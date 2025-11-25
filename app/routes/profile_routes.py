from fastapi import APIRouter, Form, HTTPException, Request, Depends
from app.controllers.candidate_info import get_candidate_info
from app.models.interview_candidate_details import InterviewCandidateDetails
from sqlalchemy.orm import Session
from app.config.database import SessionLocal, get_db
from app.config.auth import create_access_token, get_current_user
from datetime import datetime

router = APIRouter(tags=["Candidate Interview"])

@router.get("/candidate/{candidate_id}")
def getUser(candidate_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return get_candidate_info(candidate_id,db)

@router.get("/candidate/meeting-status/")
def meetingStatus(candidate_id: int, meeting_id: int, type_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):

    row = db.query(InterviewCandidateDetails).filter(
        InterviewCandidateDetails.id == candidate_id,
        InterviewCandidateDetails.meeting_id == meeting_id
        ).first()

    if not row:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Update login status
    if type_id == 1:
        row.login_status = "1"
    elif type_id == 2:
        row.login_status = "2"
    elif type_id == 3:
        row.login_status = "3"
    elif type_id == 4:
        row.login_status = "4"
    else:
        raise HTTPException(status_code=400, detail="Invalid type_id")

    row.modify_date = datetime.utcnow()

    db.commit()
    db.refresh(row)

    return {
        "status": "success",
        "message": "Login status updated",
        "candidate_id": row.id,
        "meeting_id": row.meeting_id,
        "login_status": row.login_status
    }
