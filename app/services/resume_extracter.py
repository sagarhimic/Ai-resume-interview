# resume_extracter.py
import io
import re
from typing import Optional

import pdfplumber
import docx

# Optional OCR libs (used only if pdfplumber finds no text)
try:
    from pdf2image import convert_from_bytes
    import pytesseract
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False


def _clean_text(text: str) -> str:
    """Normalize whitespace and remove PDF operator-like noise if present."""
    if not text:
        return ""
    # Remove sequences that look like raw PDF operators or long hex streams:
    text = re.sub(r"<[0-9A-Fa-f\s]{10,}>", " ", text)
    text = re.sub(r"\b(BT|ET|Td|Tf|TJ|Tj)\b", " ", text)
    # Replace multiple whitespace/newlines with single spaces/newlines
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n\s+\n", "\n\n", text)
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_resume_text(file_stream: io.BytesIO, ext: str) -> str:
    """Main function to extract text from pdf/docx/txt.
    file_stream should be a BytesIO (position may be at 0)."""
    ext = ext.lower()
    # ensure we can read from the start
    try:
        file_stream.seek(0)
    except Exception:
        pass

    if ext == "pdf":
        text = extract_pdf_text(file_stream)
        if text and text.strip():
            return _clean_text(text)

        # If pdfplumber couldn't extract text, attempt OCR fallback (if available)
        if OCR_AVAILABLE:
            try:
                # Seek again and get bytes
                file_stream.seek(0)
                img_pages = convert_from_bytes(file_stream.read())
                ocr_text = []
                for img in img_pages:
                    ocr_text.append(pytesseract.image_to_string(img))
                combined = "\n".join(ocr_text)
                return _clean_text(combined)
            except Exception:
                # final fallback: return empty string
                return ""
        else:
            return ""
    elif ext == "docx":
        return _clean_text(extract_docx_text(file_stream))
    elif ext == "txt":
        try:
            file_stream.seek(0)
            raw = file_stream.read()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="ignore")
            return _clean_text(raw)
        except Exception:
            return ""
    else:
        return ""


def extract_pdf_text(file_stream: io.BytesIO) -> str:
    """Extract text using pdfplumber. Returns empty string if no text found."""
    text_parts = []
    try:
        # Ensure stream at start
        file_stream.seek(0)
        with pdfplumber.open(file_stream) as pdf:
            for page in pdf.pages:
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception:
                    continue
    except Exception:
        return ""
    return "\n".join(text_parts)


def extract_docx_text(file_stream: io.BytesIO) -> str:
    """Extract text from docx files using python-docx."""
    try:
        file_stream.seek(0)
        doc = docx.Document(file_stream)
        paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
        return "\n".join(paragraphs)
    except Exception:
        return ""


def extract_skills(text: str) -> str:
    skills_keywords = [
        "python", "java", "php", "mysql", "javascript", "react", "angular",
        "node", "fastapi", "django", "api", "html", "css", "laravel",
        "git", "docker", "aws", "linux"
    ]
    if not text:
        return ""
    found = []
    text_lower = text.lower()
    for s in skills_keywords:
        if re.search(r"\b" + re.escape(s) + r"\b", text_lower):
            found.append(s.capitalize())
    return ", ".join(sorted(set(found)))


def extract_experience(text: str) -> str:
    if not text:
        return "0"
    patterns = [
        r"(\d+)\+?\s*[-]?\s*years?",        # "5 years" or "5+ years"
        r"(\d+)\s*yrs?\b",                  # "5 yrs"
        r"experience\s*[:\-]?\s*(\d+)"      # "experience: 5"
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return "0"
