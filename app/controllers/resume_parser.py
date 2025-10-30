from fastapi import FastAPI, File, UploadFile, Form, Depends
from fastapi.responses import JSONResponse
from datetime import datetime, date
import tempfile
import PyPDF2
import spacy
import re
from docx import Document
import openpyxl
from sqlalchemy.orm import Session
from app.config.database import SessionLocal, get_db
from app.config.auth import get_current_user
from app.models.interview_candidate_details import InterviewCandidateDetails, CandidatePassword
from app.utils import generate_random_meeting_id, generate_random_password, clean_utf8
from passlib.context import CryptContext

nlp = spacy.load("en_core_web_sm")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SKILL_KEYWORDS = [
    "python", "java", "c++", "php", "javascript", "laravel", "django", "flask",
    "mysql", "mongodb", "html", "css", "react", "angular", "vue",
    "aws", "git", "docker", "linux", "rest api", "nodejs", "machine learning",
    "Photoshop", "Illustrator", "Adobe XD", "Figma", "WordPress", "svn"
]

# --------------- File Readers ---------------
def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

def extract_text_from_docx(file_path):
    doc = Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def extract_text_from_xlsx(file_path):
    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active
    text = ""
    for row in sheet.iter_rows(values_only=True):
        for cell in row:
            if cell:
                text += str(cell) + " "
    return text

# --------------- Helper Functions ---------------
def extract_contact_info(text):
    email = re.findall(r'[\w\.-]+@[\w\.-]+', text)
    phone = re.findall(r'\+?\d[\d\s\-]{8,15}', text)
    return {
        "email": email[0] if email else None,
        "phone": phone[0] if phone else None
    }

def extract_skills(text):
    text_lower = text.lower()
    found_skills = [skill for skill in SKILL_KEYWORDS if skill in text_lower]
    return list(set(found_skills))

def extract_name(text):
    # Take top lines (usually contain the name)
    top_section = "\n".join(text.split("\n")[:10])
    lines = [l.strip() for l in top_section.split("\n") if l.strip()]

    # Remove unwanted words
    ignore_words = ["resume", "cv", "summary", "profile", "curriculum"]
    candidates = [
        l for l in lines
        if not any(word.lower() in l.lower() for word in ignore_words)
        and 3 <= len(l.split()) <= 4  # likely 2–3 word names
        and len(l) < 50
    ]

    # Try regex for all-caps names
    regex_name = re.findall(r'^[A-Z][A-Z\s]{3,}$', top_section, re.MULTILINE)
    if regex_name:
        return regex_name[0].title().strip()

    # Fallback: pick first candidate line
    if candidates:
        return candidates[0].title().strip()

    # Last resort: SpaCy NER
    doc = nlp(top_section)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text.strip()

    return None

def parse_resume(profile_name: str = Form(...),
                profile_id: int = Form(...),
                submission_id: int = Form(...),
                job_title: str = Form(...),
                profile_email: str = Form(...),
                mobile: str = Form(...),
                interview_date: str = Form(...),
                interview_duration: int = Form(...),
                location: str = Form(...),
                recruiter_id: int = Form(...),
                job_description: str = Form(...),
                resume_text: str = Form(...),
                required_skills: str = Form(...),
                file: UploadFile = File(...),
                current_user: InterviewCandidateDetails = Depends(get_current_user),
                db: Session = Depends(get_db)):
    try:
        # Use synchronous read
        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
            tmp.write(file.file.read())  # <-- synchronous read
            tmp_path = tmp.name

        ext = file.filename.split(".")[-1].lower()
        if ext == "pdf":
            text = extract_text_from_pdf(tmp_path)
        elif ext == "docx":
            text = extract_text_from_docx(tmp_path)
        elif ext == "xlsx":
            text = extract_text_from_xlsx(tmp_path)
        else:
            return JSONResponse(content={"status": "error", "message": f"Unsupported file: .{ext}"})

        text = re.sub(r'\s+', '\n', text.strip())
        name = extract_name(text)
        contact = extract_contact_info(text)
        skills = extract_skills(text)
        profile_skills_str = ','.join(skills) if isinstance(skills, list) else str(skills)

        # ---- New logic for designation & experience ----
        meeting_id = generate_random_meeting_id()
        password = generate_random_password()
        profile_id = profile_id
        submission_id = submission_id
        profile_name = profile_name
        job_title = job_title
        profile_email = profile_email
        mobile = mobile
        interview_date = interview_date
        interview_duration = interview_duration
        location = location
        recruiter_id = recruiter_id
        job_description = job_description
        resume_text = resume_text
        experience_years = None
        required_skills = required_skills

        top_section = "\n".join(text.split("\n")[:30])
        # match_designation = re.search(
        #     r'(Senior|Lead|Software|Engineer|Developer|Manager|Analyst|Consultant|Architect)[A-Za-z\s]*',
        #     top_section, re.IGNORECASE
        # )
        # if match_designation:
        #     designation = match_designation.group(0).strip().title()

        # 1️⃣ Common patterns like "12 years", "12+ years", "over 10 years"
        # 1️⃣ Broad regex patterns
        exp_patterns = [
            # 12 years, 12+ years, 12 year, 12-year
            r'(\d{1,2}\s*[\-\+]?\s*(?:years?|yrs?|year)(?:\s*of\s*experience)?)',
            # over/around 10 years
            r'(?:over|around|approximately)\s*(\d{1,2})\s*(?:years?|yrs?)',
            # range like 10–12 years
            r'(\d{1,2})\s*[-–]\s*(\d{1,2})\s*(?:years?|yrs?)'
        ]

        for pattern in exp_patterns:
            exp_match = re.search(pattern, text, re.IGNORECASE)
            if exp_match:
                # If regex captures both start and end of range (like 10–12)
                if exp_match.lastindex and exp_match.lastindex > 1:
                    experience_years = f"{exp_match.group(1)}-{exp_match.group(2)} years"
                else:
                    experience_years = exp_match.group(1)
                break

        # 2️⃣ Infer from employment year spans (e.g., 2011–2023)
        if not experience_years:
            year_spans = re.findall(r'(20\d{2})\s*[-–]\s*(20\d{2}|present|current)', text, re.IGNORECASE)
            if year_spans:
                total_months = 0
                current_year = datetime.now().year
                for start, end in year_spans:
                    end_year = current_year if end.lower() in ["present", "current"] else int(end)
                    total_months += (end_year - int(start)) * 12
                years = round(total_months / 12)
                if years > 0:
                    experience_years = f"{years} years"

        # 3️⃣ Search lines mentioning "experience"
        if not experience_years:
            lines = [l.strip() for l in text.split("\n") if "experience" in l.lower()]
            for line in lines:
                match = re.search(r'(\d{1,2}\s*[\-\+]?\s*(?:years?|yrs?|year))', line, re.IGNORECASE)
                if match:
                    experience_years = match.group(1).replace("+", "").strip()
                    break

        clean_name = re.sub(r'\s+', ' ', name).strip() if name else None
        clean_email = contact["email"].strip() if contact["email"] else None
        clean_phone = re.sub(r'\s+', '', contact["phone"]).strip() if contact["phone"] else None
        # clean_designation = re.sub(r'\s+', ' ', designation).strip() if designation else None
        # 4️⃣ Normalize experience string
        clean_experience = (
            re.sub(r'[^0-9\-–a-zA-Z\s]', '', experience_years).replace('year', 'years').strip()
            if experience_years else None
        )

        job_info = {
            "job_title": job_title,
            "job_description": job_description,
            "required_skills": (
                required_skills.split(",")
            )
        }

        db = SessionLocal()

        # ✅ Hash the password before saving
        hashed_password = pwd_context.hash(password)

        candidate = InterviewCandidateDetails(
            meeting_id=meeting_id,
            password=hashed_password,
            profile_id=profile_id,  # or generate if you have logic
            submission_id=submission_id,
            profile_name=profile_name,
            profile_email=profile_email,
            cell_phone=mobile,
            job_title=job_title,
            job_description=clean_utf8(job_description),
            resume_text=clean_utf8(resume_text),
            required_skills=clean_utf8(required_skills),
            profile_skills=profile_skills_str,
            profile_exp=experience_years,
            interview_date=datetime.strptime(interview_date, "%Y-%m-%d %H:%M:%S"),
            interview_location=clean_utf8(location),
            interview_duration=str(interview_duration),
            recruiter_id=recruiter_id,
            created_date=date.today(),
            modify_date=date.today(),
            login_status=0
        )

        db.add(candidate)
        db.commit()
        db.refresh(candidate)

        password_info = CandidatePassword(
            candidate_id=candidate.id,
            password=password,
            created_at=date.today(),
        )

        db.add(password_info)
        db.commit()
        db.refresh(password_info)
        db.close()

        return JSONResponse(content={
            "status": "success",
            "data": {
                "candidate": {
                    "meeting_id": meeting_id,
                    "password": password,
                    "profile_name": profile_name,
                    "job_title": job_title,
                    "profile_email": profile_email,
                    "mobile": mobile,
                    "interview_date": interview_date,
                    "interview_duration": interview_duration,
                    "location": location,
                    "recruiter_id": recruiter_id,
                    "resume_name": clean_name,
                    "resume_email": clean_email,
                    "resume_phone": clean_phone,
                    "experience": clean_experience,
                    "skills": profile_skills_str,
                    "resume_text": resume_text
                },
                "job_info": job_info
            }
        })

    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)})
    # finally:
    #     db.close()
