from sqlalchemy import Column, Integer, String, Text, Date, DateTime
import datetime
from app.config.database import Base

class InterviewQuestion(Base):
    __tablename__ = "interview_questions"
    id = Column(Integer, primary_key=True)
    job_description = Column(Text, nullable=True)
    question_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
