from fastapi import APIRouter, Form, UploadFile, File, HTTPException, Request, Depends
from app.controllers.GenerateQuestions import generate_questions
from sqlalchemy.orm import Session
from app.models.interview_candidate_details import InterviewCandidateDetails
from app.config.auth import get_current_user
from app.config.database import get_db

router = APIRouter()

@router.post("/generate-questions/")

def generate_ai_questions(job_title: str = Form(...),
                        job_description: str = Form(...),
                        duration: int = Form(...),
                        experience: int = Form(...),
                        required_skills: str = Form(...),
                        candidate_skills: str = Form(...),
                        current_user: InterviewCandidateDetails = Depends(get_current_user),
                        db: Session = Depends(get_db)
                        ):

    return generate_questions(job_title,job_description,duration,experience,required_skills,candidate_skills,current_user,db)
