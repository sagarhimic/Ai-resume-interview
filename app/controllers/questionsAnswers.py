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

    # ❌ No 404 error — return empty result instead
    if not candidate_answers:
        return {
            "candidate_id": candidate_id,
            "total_answers": 0,
            "avg_accuracy_score": 0.0,
            "answers": []
        }

    result = []
    total_score = 0
    scored_count = 0   # to avoid None values affecting average

    # Loop through answers and attach question text
    for ans in candidate_answers:

        question = db.query(InterviewQuestion).filter(InterviewQuestion.id == ans.question_id).first()

        result.append({
            # "question_id": ans.question_id,
            "question_text": question.question_text if question else "Question not found",
            "answer_text": ans.answer_text,
            "accuracy_score": ans.accuracy_score
            # "created_at": ans.created_at.isoformat()
        })

        # Calculate average (ignore None values)
        if ans.accuracy_score is not None:
            total_score += float(ans.accuracy_score)
            scored_count += 1

    # Prevent division by zero
    avg_accuracy = round(total_score / scored_count, 2) if scored_count > 0 else 0.0

    return {
        "candidate_id": candidate_id,
        "total_answers": len(result),
        "avg_accuracy_score": avg_accuracy,
        "answers": result
    }
