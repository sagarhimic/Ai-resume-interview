# Copilot Instructions for Ai-resume-interview
```markdown
# Copilot Instructions for Ai-resume-interview

## Project Overview
Lightweight Python service for resume screening, job-description generation, and automated interview flows.

## High-level Architecture
- `app/` — application code. Key folders:
	- `config/` — DB and auth helpers (`database.py`, `auth.py`, `recruiter_auth.py`).
	- `controllers/` — business logic. Recruiter helpers live in `controllers/recruiter/`.
	- `models/` — data objects representing candidates, interviews, answers, etc.
	- `routes/` — FastAPI-style route modules that wire controllers to HTTP endpoints.
- `uploads/` — repository-local upload storage (resumes uploaded here by UI or tests).

## New: Recruiter Resume Parser
- Controller: `app/controllers/recruiter/resume_parser_recruiter.py` (lightweight, importable).
- Purpose: read files from `uploads/` and extract both a full text dump and structured fields
	(name, email, phone, skills, education, experience_years) so recruiter flows can ingest
	resumes without `submission_id` or `profile_id` bookkeeping.
- Usage (example):

```py
from app.controllers.recruiter.resume_parser_recruiter import parse_all_uploads
results = parse_all_uploads()  # returns list of { filename, path, full_text, fields }
```

Notes on capabilities and limits:
- Supported file types out-of-the-box: `.pdf`, `.docx`, `.txt`.
- Image OCR (`.png`, `.jpg`) is attempted only if `pytesseract` + `Pillow` are installed —
	otherwise images are skipped (module falls back gracefully).
- Field extraction is heuristic-based (regexes and simple token matching). It is intentionally
	conservative — use downstream validation before persisting to canonical DB columns.

## Developer Workflows
- Run locally: `pip install -r requirements.txt` then `python app/main.py` (FastAPI/uvicorn apps
	may require `uvicorn app.main:app --reload`). Check `requirements.txt` for included libs.
- Important packages already present: `PyPDF2`, `python-docx`, `pandas`. Add `pytesseract` only
	if OCR is required for images.

## Patterns & Conventions (project-specific)
- Controllers are the canonical place for business logic — keep routes thin.
- Recruiter-specific helpers live in `app/controllers/recruiter/` and routes in
	`app/routes/recruiter/`.
- File uploads are stored in the repo-level `uploads/` folder for processing. The new parser
	expects files to already exist there and returns extracted text + fields.

## Integration Points to Inspect
- `app/config/database.py` — DB connection and session management.
- `app/config/recruiter_auth.py` — recruiter auth rules; follow its pattern when adding recruiter-only routes.
- `app/controllers/*` — example implementations for how to structure a controller that returns
	JSON-ready Python dicts (see `ai_analyze.py` and `generate_jd.py`).

## When You (the agent) Add Features
- Inspect the matching recruiter route in `app/routes/recruiter/` and wire new controller functions
	there. Keep routes responsible for request parsing/response only; heavy lifting belongs in controllers.
- If you need OCR for images, add `pytesseract` and `Pillow` to `requirements.txt` and document why.
- Keep persistent changes (DB writes) behind a model in `app/models/` and use transactions in
	`app/config/database.py`.

## Quick Examples (copyable)
- Parse all files in uploads (python REPL):

```sh
python -c "from app.controllers.recruiter.resume_parser_recruiter import parse_all_uploads; import json; print(json.dumps(parse_all_uploads(), indent=2))"
```

---
If any section is unclear or you want the parser wired to a FastAPI route (e.g. a recruiter-only
`POST /recruiter/parse-uploads`), tell me and I will add the route and minimal tests.

```
