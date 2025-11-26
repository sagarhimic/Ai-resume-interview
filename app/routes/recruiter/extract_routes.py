from fastapi import APIRouter, UploadFile, Form, Depends, HTTPException, File
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, date
import io
import re
from app.config.database import get_db
from app.config.recruiter_auth import get_current_user
from app.models.interview_candidate_details import InterviewCandidateDetails, CandidatePassword
from app.models.user import User
from app.services.resume_extracter import extract_resume_text, extract_skills, extract_experience
from app.utils import generate_random_meeting_id, generate_random_password, format_interview_date, interview_status_name
from passlib.context import CryptContext

router = APIRouter(tags=["Recruiter Authentication"])

@router.post("/recruiter/upload_candidate/")
async def upload_candidate(
    profile_name: str = Form(...),
    # profile_id: int = Form(...),
    # submission_id: int = Form(...),
    job_title: str = Form(...),
    profile_email: str = Form(...),
    mobile: str = Form(...),
    interview_date: str = Form(...),
    interview_duration: int = Form(...),
    location: str = Form(...),
    recruiter_id: int = Form(...),
    job_description: str = Form(...),
    required_skills: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate file type
    allowed_ext = ["pdf", "docx", "txt"]
    ext = file.filename.split(".")[-1].lower()

    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, TXT files allowed")

    # Read file bytes
    file_bytes = await file.read()
    file_stream = io.BytesIO(file_bytes)

    # Extract resume text
    try:
        resume_text = extract_resume_text(file_stream, ext)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Resume parsing failed: {str(e)}")

    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="Resume text is empty")

    # Extract skills & experience
    parsed_skills = extract_skills(resume_text)
    parsed_exp = extract_experience(resume_text)

    # Generate Meeting ID & Password
    meeting_id = generate_random_meeting_id()
    password = generate_random_password()

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash(password)

    # Insert into database
    row = InterviewCandidateDetails(
        meeting_id=meeting_id,
        password=hashed_password,
        submission_id=0,
        profile_id="",
        profile_name=profile_name,
        profile_email=profile_email,
        cell_phone=mobile,
        job_title=job_title,
        job_description=job_description,
        profile_skills=parsed_skills,
        profile_exp=parsed_exp,
        resume_text=resume_text,
        required_skills=required_skills,
        interview_date=datetime.strptime(interview_date, "%Y-%m-%d %H:%M:%S"),
        interview_location=location,
        interview_duration=str(interview_duration),
        recruiter_id=recruiter_id,
        login_status="0",
        created_date=datetime.utcnow(),
        modify_date=datetime.utcnow()
    )

    db.add(row)
    db.commit()
    db.refresh(row)

    password_info = CandidatePassword(
        candidate_id=row.id,
        password=password,
        created_at=date.today(),
    )

    db.add(password_info)
    db.commit()
    db.refresh(password_info)
    db.close()

    return {
        "status": "success",
        "message": "Candidate uploaded successfully",
        "meeting_id": meeting_id,
        "password": password,
        "detected_skills": parsed_skills,
        "detected_experience": parsed_exp
    }

@router.post("/recruiter/interview_schedules/")

def get_interview_schedule_info(recruiter_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):

    candidates = (
        db.query(InterviewCandidateDetails)
          .filter(InterviewCandidateDetails.recruiter_id == recruiter_id)
          .order_by(desc(InterviewCandidateDetails.created_date))
          .all()
          )

    if not candidates:
        raise HTTPException(status_code=404, detail="Candidate not found")

    result = []

    for candidate in candidates:

        result.append({
            "id": candidate.id,
            "profile_name": candidate.profile_name,
            "job_title": candidate.job_title,
            "profile_skills": candidate.profile_skills,
            "profile_exp": re.sub(r'\s+', ' ', candidate.profile_exp).strip() if candidate.profile_exp else None,
            "required_skills": candidate.required_skills,
            "interview_date": format_interview_date(candidate.interview_date),
            "interview_duration": candidate.interview_duration,
            "interview_location": candidate.interview_location,
            "login_status": candidate.login_status,
            "status_name": interview_status_name(int(candidate.login_status)),
            "job_description": candidate.job_description

        })

    return {
        "status": 200,
        "total_interviews": len(candidates),
        "records": result
    }
