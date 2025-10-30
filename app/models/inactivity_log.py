# app/models/inactivity_log.py
from sqlalchemy import Column, Integer, String, Float, DateTime, func
from app.config.database import Base

class InactivityLog(Base):
    __tablename__ = "inactivity_logs"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String(50))
    event_type = Column(String(100))  # e.g. "face_missing", "no_lip_movement", "proxy_detected"
    event_message = Column(String(255))
    severity = Column(String(20))  # info / warning / critical
    frame_count = Column(Integer, default=0)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
