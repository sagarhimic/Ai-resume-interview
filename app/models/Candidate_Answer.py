from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Float, ForeignKey
import datetime
from app.config.database import Base

class CandidateAnswer(Base):
    __tablename__ = "candidate_answers"

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("interview_candidate_details.id"))
    question_id = Column(Integer, ForeignKey("interview_questions.id"))
    answer_text = Column(Text, nullable=True)
    accuracy_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class CandidateAudio(Base):
    __tablename__ = "candidate_question_answer_audio"

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("interview_candidate_details.id"))
    question_id = Column(Integer, ForeignKey("interview_questions.id"))
    audio_file = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class CandidateFullVideo(Base):
    __tablename__ = "candidate_video"

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("interview_candidate_details.id"))
    video_file = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
