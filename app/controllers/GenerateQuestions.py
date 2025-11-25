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
    You are an experienced and friendly technical interviewer conducting a real human-like interview.

    Interview Context:
    - Job Title: {job_title}
    - Job Description: {job_description}
    - Duration: {duration} minutes
    - Candidate Experience: {experience} years
    - Required Skills: {required_skills}
    - Candidate Skills: {candidate_skills}

    Interview Goal:
    Conduct a conversational-style interview where you start with a self-introduction
    and build rapport, then gradually move from personal/human questions to
    behavioral, situational, and finally technical questions.

    Format and Style:
    - Sound natural, like a real human interviewer.
    - Start with a greeting and a short self-introduction.
    - Ask the candidate to introduce themselves.
    - Ask one question per line (no numbering, no explanations).
    - Avoid robotic phrasing or lists — every question should sound human and spontaneous.
    - Prefer open-ended questions (e.g., “Can you tell me about…” rather than “What is…”).
    - Then move to:
        1. **Personality / Communication questions** (e.g., confidence, motivation, strengths)
        2. **Behavioral / HR questions** (e.g., team challenges, problem-solving, adaptability)
        3. **Situational / Decision-making questions**
        4. **Technical / OOP / Database / Framework questions** based on skills listed
        5. **Finish with one wrap-up question (e.g., “Do you have any questions for me?”)
    - Make technical questions slightly challenging for the candidate's experience level.
    - Output only one question per line (no numbering or explanations).

    Example format:
    Hi, I’m your interviewer for today. How are you feeling?
    Could you please introduce yourself?
    Can you share a project that you’re most proud of?
    Describe a time you solved a complex issue under pressure.
    How would you optimize performance in a large-scale {job_title.lower()} system?
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

def submit_answer(
    candidate_id: int = Form(...),
    meeting_id: str = Form(...),
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
        # 🔹 Fetch question text
        question = db.query(InterviewQuestion).filter_by(id=question_id).first()
        if not question:
            return {"error": f"Question with ID {question_id} not found"}

        question_text = question.question_text.strip()

        # 🔹 Detect skip / uncertain answers
        skip_phrases = [
            "don't know", "dont know", "not sure", "no idea",
            "skip", "next question", "ask another", "repeat please",
            "sorry", "I have no answer", "I cannot answer"
        ]

        lower_answer = answer_text.lower().strip()
        is_skip = any(p in lower_answer for p in skip_phrases)

        if is_skip:
            # 🧠 Generate a new follow-up question instead of scoring
            follow_prompt = f"""
            You are an adaptive interviewer.
            The candidate could not answer or skipped the question:
            "{question_text}"

            Please ask a **simpler or related follow-up question**
            that helps the candidate re-engage.
            Make it conversational and natural (no bullet points or numbers).
            """

            try:
                follow_response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=follow_prompt
                )
                next_question = follow_response.text.strip()
            except Exception as e:
                next_question = "Let's try something different. Can you tell me about your last project?"

            # Save skipped answer with score 0
            skipped_answer = CandidateAnswer(
                candidate_id=candidate_id,
                meeting_id=meeting_id,
                question_id=question_id,
                answer_text=answer_text,
                accuracy_score=0.0
            )
            db.add(skipped_answer)
            db.commit()
            db.refresh(skipped_answer)

            return {
                "status": "skipped",
                "reason": "Candidate requested to skip or was unsure.",
                "next_question": next_question,
                "question_id": question_id,
                "answer": answer_text,
                "accuracy_score": 0.0
            }

        # ✅ Regular scoring path
        eval_prompt = f"""
        You are a professional interviewer evaluating a candidate's response.

        Question: "{question_text}"
        Candidate Answer: "{answer_text}"

        Please return your result in this exact format:

        Score: [numeric value between 0 and 100]
        Next Question: [a natural follow-up question]
        """

        try:
            eval_response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=eval_prompt
            )
            full_text = eval_response.text.strip()
        except Exception as e:
            return {"error": f"Gemini API Error: {str(e)}"}

        # 🔍 Extract score and question using regex
        import re

        score_match = re.search(r"(?i)score[:\-\s]*([0-9]+(?:\.[0-9]*)?)", full_text)
        question_match = re.search(r"(?i)next\s*question[:\-\s]*(.*)", full_text)

        score = float(score_match.group(1)) if score_match else 0.0
        next_question = (
            question_match.group(1).strip()
            if question_match and len(question_match.group(1).strip()) > 5
            else "Could you elaborate further on your previous answer?"
        )

        # 🧠 Safety: Gemini sometimes gives extra newlines
        next_question = next_question.split("\n")[0].strip()

        # 💾 Save normal answer to DB
        ans = CandidateAnswer(
            candidate_id=candidate_id,
            meeting_id=meeting_id,
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
            "accuracy_score": score,
            "next_question": next_question,
            "raw_output": full_text  # (optional: for debugging)
        }

    finally:
        db.close()
