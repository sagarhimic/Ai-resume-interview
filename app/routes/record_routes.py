from fastapi import APIRouter, File, UploadFile, Form, Depends
from app.config.database import get_db
from sqlalchemy.orm import Session
import os
from datetime import datetime
from app.controllers.records import upload_full_video, upload_question_audio

router = APIRouter()

@router.post("/upload-question-audio/")
async def upload_question_audio_rec(candidate_id: str = Form(...),
                                question_id: str = Form(None),
                                audio_file: UploadFile = File(...),
                                db: Session = Depends(get_db)):

        return await upload_question_audio(candidate_id,question_id,audio_file,db)


@router.post("/upload-full-video/")
async def upload_full_video_rec(candidate_id: str = Form(...),
                            video_file: UploadFile = File(...),
                            db: Session = Depends(get_db)):

    return await upload_full_video(candidate_id,video_file,db)
