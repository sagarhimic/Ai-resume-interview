import pdfplumber
import docx
import re
import io


def extract_resume_text(file_stream, ext):
    """Main function to extract text based on file type."""

    if ext == "pdf":
        return extract_pdf_text(file_stream)
    elif ext == "docx":
        return extract_docx_text(file_stream)
    elif ext == "txt":
        return file_stream.read().decode("utf-8", errors="ignore")
    else:
        return ""


def extract_pdf_text(file_stream):
    text = ""
    with pdfplumber.open(file_stream) as pdf:
        for page in pdf.pages:
            try:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            except:
                continue
    return text


def extract_docx_text(file_stream):
    doc = docx.Document(file_stream)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])


def extract_skills(text):
    skills_keywords = [
        "python", "java", "php", "mysql", "javascript", "react", "angular",
        "node", "fastapi", "django", "api", "html", "css", "laravel",
        "git", "docker", "aws", "linux"
    ]

    found = []
    text_lower = text.lower()

    for s in skills_keywords:
        if s in text_lower:
            found.append(s.capitalize())

    return ", ".join(sorted(set(found)))


def extract_experience(text):
    exp_patterns = [
        r"(\d+)\+?\s*years",
        r"(\d+)\s*yrs",
        r"experience\s*[:\-]?\s*(\d+)"
    ]

    for pattern in exp_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

    return "0"
