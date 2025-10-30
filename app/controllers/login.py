from fastapi import FastAPI, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.config.database import SessionLocal, engine, get_db
from app.models.interview_candidate_details import InterviewCandidateDetails
from app.config.auth import create_access_token
import re

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
MAX_BCRYPT_LENGTH = 72  # bcrypt supports up to 72 bytes

def userLogin(
    meeting_id: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Fetch user from database
    user = db.query(InterviewCandidateDetails).filter(
        InterviewCandidateDetails.meeting_id == meeting_id
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid meeting ID")

    # --- Step 1: Sanitize / truncate password for bcrypt ---
    trimmed_password = password.encode("utf-8")[:MAX_BCRYPT_LENGTH].decode("utf-8", "ignore")

    # --- Step 2: Verify password safely ---
    password_valid = False

    try:
        # Try verifying as bcrypt hash
        password_valid = pwd_context.verify(trimmed_password, user.password)
    except ValueError:
        # bcrypt may throw ValueError if user.password isn't a bcrypt hash
        password_valid = (password == user.password)

    if not password_valid:
        raise HTTPException(status_code=401, detail="Invalid password")

    # Compare plain-text or hashed passwords
    # if not pwd_context.verify(password, user.password):
    #      raise HTTPException(status_code=401, detail="Invalid password")


    # ✅ Create JWT token
    access_token = create_access_token({"sub": user.meeting_id})

    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "data": {
            "candidate_id": user.id,
            "job_title": user.job_title,
            "job_description": user.job_description,
            "duration": user.interview_duration,
            "experience": re.sub(r'\s+', ' ', user.profile_exp).strip().replace('years', '').strip() if user.profile_exp else None,
            "required_skills": user.required_skills,
            "candidate_skills": user.profile_skills,
        }
    }
