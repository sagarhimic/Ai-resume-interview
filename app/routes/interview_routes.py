from fastapi import APIRouter, Form, UploadFile, File, HTTPException, Request
from app.controllers.GenerateQuestions import generate_questions

router = APIRouter()

@router.post("/generate-questions/")

def generate_ai_questions(job_title: str = Form(...),
                        job_description: str = Form(...),
                        duration: int = Form(...),
                        experience: int = Form(...),
                        required_skills: str = Form(...),
                        candidate_skills: str = Form(...)
                        ):

    return generate_questions(job_title,job_description,duration,experience,required_skills,candidate_skills)
