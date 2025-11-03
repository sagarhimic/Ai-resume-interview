from fastapi import FastAPI, Form, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, JSON, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.models.interview_candidate_details import InterviewCandidateDetails
from app.models.Candidate_Answer import CandidateAnswer
from app.models.Interview_Question import InterviewQuestion
from app.config.auth import get_current_user
from app.config.database import get_db
from app.config.database import SessionLocal
import datetime
from google import genai
import os
import requests

# ---------------- Gemini AI Config ----------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCTwt-PO38KpxWp2CQLUhJijmMolDMziwM")
client = genai.Client(api_key=GEMINI_API_KEY)


# ---------------- Gemini Chat Function ----------------
def gemini_chat(prompt: str):
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",  # ✅ or gemini-2.5-flash if available
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"Error: {str(e)}"

# ---------------- Generate Interview Questions ----------------
def generate_questions(
    job_title: str = Form(...),
    job_description: str = Form(...),
    duration: int = Form(...),
    experience: int = Form(...),
    required_skills: str = Form(...),        # "Python, Flask, SQL"
    candidate_skills: str = Form(...),
    current_user: InterviewCandidateDetails = Depends(get_current_user),
    db: Session = Depends(get_db)):

    prompt = f"""
    You are an expert technical interviewer.
    Generate {duration} minutes {job_title} interview questions for a candidate with {experience} years experience.

    Job Description: {job_description}
    Required Skills: {required_skills}
    Candidate Skills: {candidate_skills}

    - Include technical, OOP, database, and framework questions.
    - Make them slightly challenging based on candidate's skills.
    - Output only questions separated by new lines.
    """

    # ✅ Get questions from Gemini
    ai_response = gemini_chat(prompt)
    questions = [q.strip() for q in ai_response.split("\n") if q.strip()]

    # ✅ Store questions in DB
    db = SessionLocal()
    question_objs = []
    for q in questions:
        iq = InterviewQuestion(
            job_description=job_description,
            question_text=q,
            created_at=datetime.datetime.utcnow(),
        )
        db.add(iq)
        db.commit()
        db.refresh(iq)
        question_objs.append({"id": iq.id, "question": iq.question_text})

    db.close()
    return {"questions": question_objs}

# ---------------- Submit Candidate Answer ----------------

# ---------------- Submit Candidate Answer ----------------
def submit_answer(
    candidate_id: int = Form(...),
    question_id: int = Form(...),
    answer_text: str = Form(...),
    candidate_skills: str = Form(...),
    experience: str = Form(...),
    job_description: str = Form(...),
    required_skills: str = Form(...),
    current_user: InterviewCandidateDetails = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db = SessionLocal()
    try:
        # 🔹 Fetch question text immediately and store it before session closes
        question = db.query(InterviewQuestion).filter_by(id=question_id).first()
        if not question:
            return {"error": f"Question with ID {question_id} not found"}

        question_text = question.question_text  # ✅ store before commit/close

        # 🔹 Build prompt
        prompt = f"""
        You are an expert technical interviewer.
        Candidate Info:
          - Experience: {experience} years
          - Skills: {candidate_skills}
        Job Description: {job_description}
        Required Skills: {required_skills}

        Question: {question_text}
        Candidate Answer: {answer_text}

        Rate the candidate's answer from 0 to 100 based on:
        - Correctness
        - Completeness
        - Relevance to the question and the job role

        Respond only with a numeric score (e.g., 85).
        """

        # 🔹 Gemini evaluation
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            score_text = response.text.strip()
        except Exception as e:
            return {"error": f"Gemini API Error: {str(e)}"}

        # 🔹 Parse numeric score
        try:
            score = float(score_text)
        except ValueError:
            score = 0.0

        # 🔹 Save to DB
        ans = CandidateAnswer(
            candidate_id=candidate_id,
            question_id=question_id,
            answer_text=answer_text,
            accuracy_score=score
        )
        db.add(ans)
        db.commit()
        db.refresh(ans)

        return {
            "status": "success",
            "question": question_text,
            "answer": answer_text,
            "accuracy_score": score
        }

    finally:
        db.close()
