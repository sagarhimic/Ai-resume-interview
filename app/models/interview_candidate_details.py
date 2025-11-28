from sqlalchemy import Column, Integer, String, Text, Date, DateTime
from app.config.database import Base

class InterviewCandidateDetails(Base):
    __tablename__ = "interview_candidate_details"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    meeting_id = Column(String(50), nullable=False)
    password = Column(String(125), nullable=False)
    submission_id = Column(Integer, nullable=True)
    profile_id = Column(String(125), nullable=True)
    profile_name = Column(String(250), nullable=True)
    profile_email = Column(String(45), nullable=True)
    cell_phone = Column(String(45), nullable=True)
    job_title = Column(String(250), nullable=True)
    job_description = Column(Text, nullable=True)
    profile_skills = Column(Text, nullable=False)
    profile_exp = Column(String(250), nullable=True)
    resume_text = Column(Text, nullable=False)
    required_skills = Column(String(500), nullable=False)
    interview_date = Column(DateTime, nullable=False)
    interview_location = Column(String(125), nullable=False)
    interview_duration = Column(String(45), nullable=False)
    recruiter_id = Column(Integer, nullable=False)
    created_date = Column(Date, nullable=False)
    modify_date = Column(Date, nullable=False)
    resume_path = Column(Text, nullable=True)
    login_status = Column(Integer, nullable=False, default=0)


class CandidatePassword(Base):
    __tablename__ = "candidate_password"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    candidate_id = Column(Integer, nullable=True)
    password = Column(String(45), nullable=True)
    created_at = Column(Date, nullable=False)
