from fastapi import APIRouter, Form, UploadFile, File, HTTPException, Request, Depends
from app.controllers.GenerateQuestions import submit_answer
from app.models.interview_candidate_details import InterviewCandidateDetails
from sqlalchemy.orm import Session
from app.config.auth import get_current_user
from app.config.database import get_db

router = APIRouter(tags=["Candidate Interview"])

@router.post("/submit-answer/")
def submit_candidate_answers(candidate_id: int = Form(...),
                            meeting_id: int = Form(...),
                            question_id: int = Form(...),
                            answer_text: str = Form(...),
                            candidate_skills: str = Form(...),      # comma separated: "Python, HTML, CSS"
                            experience: str = Form(...),
                            job_description: str = Form(...),
                            required_skills: str = Form(...),
                            current_user: InterviewCandidateDetails = Depends(get_current_user),
                            db: Session = Depends(get_db)):

    return submit_answer(candidate_id,meeting_id,question_id,answer_text,candidate_skills,experience,job_description,required_skills,current_user,db)
