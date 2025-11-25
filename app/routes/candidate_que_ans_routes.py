from fastapi import APIRouter, Form, UploadFile, File, HTTPException, Request, Depends
from app.controllers.questionsAnswers import get_candidate_answers
from app.models.interview_candidate_details import InterviewCandidateDetails
from sqlalchemy.orm import Session
from app.config.auth import get_current_user
from app.config.database import get_db

router = APIRouter(tags=["Candidate Interview"])

@router.post("/get-candidate-answers/")

def get_candidate_question_answers(candidate_id: int = Form(...), meeting_id: str = Form(...), current_user: InterviewCandidateDetails = Depends(get_current_user),
                            db: Session = Depends(get_db)):

    return get_candidate_answers(candidate_id,meeting_id,current_user,db)
