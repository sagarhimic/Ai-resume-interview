# main.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.interview_candidate_details import InterviewCandidateDetails
from app.models.Candidate_Answer import CandidateAnswer
from app.models.Interview_Question import InterviewQuestion
from app.config.database import SessionLocal, engine, get_db
from app.config.auth import create_access_token, get_current_user
import re


def get_candidate_answers(candidate_id: int, meeting_id: str, current_user: InterviewCandidateDetails = Depends(get_current_user),
    db: Session = Depends(get_db)):

    # ✅ Corrected query - using order_by properly
    candidate_answers = (
        db.query(CandidateAnswer)
        .filter(CandidateAnswer.candidate_id == candidate_id)
        .filter(CandidateAnswer.meeting_id == meeting_id)
        .order_by(CandidateAnswer.created_at.desc())  # or desc(CandidateAnswer.created_at)
        .all()
    )

    if not candidate_answers:
        raise HTTPException(status_code=404, detail="No answers found for this candidate")

    result = []

    # Loop through answers and attach question text
    for ans in candidate_answers:

        question = db.query(InterviewQuestion).filter(InterviewQuestion.id == ans.question_id).first()

        result.append({
            # "question_id": ans.question_id,
            "question_text": question.question_text if question else "Question not found",
            "answer_text": ans.answer_text
            # "accuracy_score": ans.accuracy_score,
            # "created_at": ans.created_at.isoformat()
        })

    return {
        "candidate_id": candidate_id,
        "total_answers": len(result),
        "answers": result
    }
