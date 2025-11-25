# app/routes/auth_routes.py
from fastapi import APIRouter, Form, UploadFile, File, HTTPException, Request, Depends
from app.controllers.resume_parser import parse_resume

router = APIRouter(tags=["Candidate Interview"])

# File Upload
@router.post("/parse-resume/")

def resumeUploadParser(profile_name: str = Form(...),
                profile_id: int = Form(...),
                submission_id: int = Form(...),
                job_title: str = Form(...),
                profile_email: str = Form(...),
                mobile: str = Form(...),
                interview_date: str = Form(...),
                interview_duration: int = Form(...),
                location: str = Form(...),
                recruiter_id: int = Form(...),
                job_description: str = Form(...),
                resume_text: str = Form(...),
                required_skills: str = Form(...),
                file: UploadFile = File(...)):

    return parse_resume(profile_name,
                        profile_id,
                        submission_id,
                        job_title,
                        profile_email,
                        mobile,
                        interview_date,
                        interview_duration,
                        location,
                        recruiter_id,
                        job_description,
                        resume_text,
                        required_skills,
                        file)
