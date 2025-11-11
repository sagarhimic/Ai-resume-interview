from fastapi import APIRouter, File, UploadFile, Form, Depends
from app.config.database import get_db
from sqlalchemy.orm import Session
import os
from datetime import datetime

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def upload_question_audio(candidate_id: str = Form(...),question_id: str = Form(None),audio_file: UploadFile = File(...),db: Session = Depends(get_db)):
    try:
        ext = os.path.splitext(audio_file.filename)[1] or ".webm"
        fname = f"q_{candidate_id}_{question_id or 'na'}_{int(datetime.utcnow().timestamp())}{ext}"
        path = os.path.join(UPLOAD_DIR, fname)
        with open(path, "wb") as f:
            f.write(await audio_file.read())

        db = SessionLocal()
        # --- Save record in DB ---
        record = CandidateAudio(
            candidate_id=candidate_id,
            question_id=question_id,
            audio_file=path,
            created_at=datetime.utcnow()
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return {
            "status": "success",
            "message": "Audio uploaded successfully",
            "data": {
                "id": record.id,
                "path": path
            }
        }

    except Exception as e:
        db.rollback()
        return {"status": "error", "detail": str(e)}

async def upload_full_video(candidate_id: str = Form(...),video_file: UploadFile = File(...),db: Session = Depends(get_db)):
    try:
        ext = os.path.splitext(video_file.filename)[1] or ".webm"
        fname = f"full_{candidate_id}_{int(datetime.utcnow().timestamp())}{ext}"
        path = os.path.join(UPLOAD_DIR, fname)
        with open(path, "wb") as f:
            f.write(await video_file.read())

        # --- Save DB record ---
        db = SessionLocal()
        record = CandidateFullVideo(
            candidate_id=candidate_id,
            video_file=path,
            created_at=datetime.utcnow()
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return {
            "status": "success",
            "message": "Full video uploaded successfully",
            "data": {
                "id": record.id,
                "path": path
            }
        }
    except Exception as e:
        db.rollback()
        return {"status": "error", "detail": str(e)}
