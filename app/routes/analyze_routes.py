# app/routes/analyze_routes.py
from fastapi import APIRouter, Form, UploadFile, File, HTTPException
from app.controllers.ai_analyze import analyze_frame

router = APIRouter(tags=["AI Frame Analysis"])


@router.post("/analyze_frame/")
async def ai_analyze_frame(candidate_id: str = Form(...), frame: UploadFile = File(...)):
    """Route for analyzing webcam frame"""
    try:
        return await analyze_frame(candidate_id, frame)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
