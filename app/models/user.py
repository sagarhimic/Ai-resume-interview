from sqlalchemy import Column, Integer, String, Text, Date, DateTime
import datetime
from app.config.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, nullable=True)
    name = Column(String(50), nullable=True)
    email = Column(String(128), nullable=True)
    mobile = Column(String(16), nullable=True)
    password = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
