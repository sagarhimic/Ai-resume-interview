"""
Recruiter resume parser controller

Provides utilities to parse resume files found in the repository `uploads/` folder
and extract common fields (name, email, phone, skills, education, experience_years)
along with the full extracted text. This module is intentionally lightweight and
does not require a web framework to run; controllers/routes can import and call
`parse_all_uploads()` or `parse_file(path)`.

Supported file types: PDF, DOCX, TXT. For images (png/jpg) OCR will be attempted
only if `pytesseract` is installed; otherwise images are skipped with a warning.

Example usage:
    from app.controllers.recruiter.resume_parser_recruiter import parse_all_uploads
    results = parse_all_uploads()

"""
from pathlib import Path
import re
import os
from typing import List, Dict, Optional

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

try:
    from docx import Document
except Exception:
    Document = None

try:
    import pytesseract
    from PIL import Image
except Exception:
    pytesseract = None
    Image = None


UPLOADS_DIR = Path(__file__).resolve().parents[3] / "uploads"


def _read_pdf(path: Path) -> str:
    if PdfReader is None:
        return ""
    try:
        reader = PdfReader(str(path))
        text = []
        for p in reader.pages:
            try:
                text.append(p.extract_text() or "")
            except Exception:
                # best-effort per page
                continue
        return "\n".join(text)
    except Exception:
        return ""


def _read_docx(path: Path) -> str:
    if Document is None:
        return ""
    try:
        doc = Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text]
        return "\n".join(paragraphs)
    except Exception:
        return ""


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        try:
            return path.read_text(encoding="latin-1", errors="ignore")
        except Exception:
            return ""


def _read_image(path: Path) -> str:
    if pytesseract is None or Image is None:
        return ""
    try:
        img = Image.open(str(path))
        return pytesseract.image_to_string(img)
    except Exception:
        return ""


EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+?\d{1,3}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}")
YEARS_RE = re.compile(r"(\d+)\+?\s*(?:years|yrs|yr|years of experience|experience)", re.I)

SKILLS_CANDIDATES = [
    "python", "java", "c++", "c#", "sql", "javascript", "react", "node", "django",
    "flask", "pandas", "numpy", "tensorflow", "pytorch", "aws", "azure", "gcp",
    "docker", "kubernetes", "ml", "machine learning", "nlp", "computer vision",
]

EDUCATION_KEYWORDS = [
    "bachelor", "b\.e", "b\.tech", "bsc", "msc", "master", "m\.tech", "mba", "phd",
]


def extract_basic_fields(text: str) -> Dict[str, Optional[str]]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    joined = "\n".join(lines)

    # email
    email = EMAIL_RE.search(joined)
    email = email.group(0) if email else None

    # phone
    phone = PHONE_RE.search(joined)
    phone = phone.group(0) if phone else None

    # experience years
    exp = YEARS_RE.search(joined)
    experience_years = int(exp.group(1)) if exp else None

    # name heuristic: first reasonable line that is not email/phone
    name = None
    for ln in lines[:6]:
        if email and email in ln:
            continue
        if phone and phone in ln:
            continue
        # skip lines with common resume headings
        if any(h.lower() in ln.lower() for h in ("resume", "curriculum", "summary", "profile")):
            continue
        # accept if contains 2-4 words and mostly letters
        tokens = [t for t in ln.split() if re.search(r"[A-Za-z]", t)]
        if 1 < len(tokens) <= 4 and all(len(t) < 30 for t in tokens):
            name = ln
            break

    # skills
    skills_found = []
    low = joined.lower()
    for s in SKILLS_CANDIDATES:
        if s in low and s not in skills_found:
            skills_found.append(s)

    # education
    education_found = []
    for k in EDUCATION_KEYWORDS:
        if k in low and k not in education_found:
            education_found.append(k)

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "experience_years": experience_years,
        "skills": skills_found or None,
        "education": education_found or None,
    }


def parse_file(path: str) -> Dict[str, Optional[object]]:
    p = Path(path)
    if not p.exists():
        return {"error": "file not found", "path": str(p)}

    suffix = p.suffix.lower()
    text = ""
    if suffix == ".pdf":
        text = _read_pdf(p)
    elif suffix in (".docx",):
        text = _read_docx(p)
    elif suffix in (".txt", ".md"):
        text = _read_text(p)
    elif suffix in (".png", ".jpg", ".jpeg", ".tiff"):
        text = _read_image(p)
    else:
        # try reading as text fallback
        text = _read_text(p)

    fields = extract_basic_fields(text)
    return {
        "filename": p.name,
        "path": str(p),
        "full_text": text,
        "fields": fields,
    }


def parse_all_uploads(limit: Optional[int] = None) -> List[Dict]:
    results = []
    if not UPLOADS_DIR.exists():
        return results

    files = sorted([p for p in UPLOADS_DIR.iterdir() if p.is_file()], key=lambda x: x.name)
    if limit:
        files = files[:limit]

    for f in files:
        try:
            res = parse_file(str(f))
            results.append(res)
        except Exception as e:
            results.append({"filename": f.name, "error": str(e)})

    return results


if __name__ == "__main__":
    # quick local runner for manual testing
    out = parse_all_uploads()
    import json
    print(json.dumps(out, indent=2))
