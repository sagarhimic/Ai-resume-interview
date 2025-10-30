from fastapi import APIRouter, Form, UploadFile, File, HTTPException, Request
from app.controllers.GenerateQuestions import submit_answer

router = APIRouter()

@router.post("/submit_answer/")
def submit_candidate_answers(candidate_id: int = Form(...),
                            question_id: int = Form(...),
                            answer_text: str = Form(...),
                            candidate_skills: str = Form(...),      # comma separated: "Python, HTML, CSS"
                            experience: str = Form(...),
                            job_description: str = Form(...),
                            required_skills: str = Form(...)):

    return submit_answer(candidate_id,question_id,answer_text,candidate_skills,experience,job_description,required_skills)
