# main.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.interview_candidate_details import InterviewCandidateDetails
from app.config.database import SessionLocal, engine, get_db
from app.config.auth import create_access_token, get_current_user
import re


def get_candidate_info(candidate_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    candidate = db.query(InterviewCandidateDetails).filter(InterviewCandidateDetails.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return {
        "id": candidate.id,
        "job_title": candidate.job_title,
        "job_description": candidate.job_description,
        "profile_skills": candidate.profile_skills,
        "profile_exp": re.sub(r'\s+', ' ', candidate.profile_exp).strip() if candidate.profile_exp else None,
        "resume_text": candidate.resume_text,
        "required_skills": candidate.required_skills,
        "interview_date": candidate.interview_date,
        "interview_location": candidate.interview_location,
        "interview_duration": candidate.interview_duration,
        "profile_name": candidate.profile_name,
    }
