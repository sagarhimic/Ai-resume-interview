# app/controllers/generate_jd.py
from fastapi import APIRouter, Form, HTTPException
from google import genai
import re
import os
router = APIRouter(tags=["AI JD Generator"])
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCTwt-PO38KpxWp2CQLUhJijmMolDMziwM")
client = genai.Client(api_key=GEMINI_API_KEY)

@router.post("/generate_jd/")
async def generate_jd(client_name: str = Form(...), role: str = Form(...)):
    """
    🔹 Generate a dynamic Job Description using Gemini AI
    🔹 Combines client projects, tech stacks, and job role relevance
    """

    try:
        prompt = f"""
        You are an AI HR Analyst.
        Your task is to generate a complete, detailed Job Description (JD) for the role of "{role}"
        at the company "{client_name}".

        Steps:
        1. Analyze what types of projects {client_name} (e.g., TCS) has worked on historically.
        2. Identify technologies commonly used by {client_name} for roles like {role}.
        3. Use global hiring trends and best practices to enrich the JD.
        4. Include key responsibilities, technical skills, qualifications, and company overview.
        5. Also, provide a concise list of 5–10 technical skills extracted from the JD.

        Output format:
        Job Description:
        [Write detailed text here]

        Skills:
        [Comma-separated list of extracted technologies and skills]
        """

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        output_text = response.text.strip()

        # ✅ Parse JD & Skills from Gemini output
        jd_match = re.search(r"(?i)job description[:\-]*([\s\S]*?)skills[:\-]", output_text)
        skills_match = re.search(r"(?i)skills[:\-]*([\s\S]*)", output_text)

        jd_text = jd_match.group(1).strip() if jd_match else output_text
        skills_text = skills_match.group(1).strip() if skills_match else "Python, Communication, Problem-Solving"

        skills_list = [s.strip() for s in re.split(r"[,;\n]+", skills_text) if len(s.strip()) > 1]

        return {
            "status": "success",
            "client_name": client_name,
            "role": role,
            "job_description": jd_text,
            "skills_extracted": skills_list
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JD generation failed: {e}")
