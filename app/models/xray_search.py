# app/models/xray_search_model.py
from pydantic import BaseModel
from typing import Optional

class XRaySearchRequest(BaseModel):
    role: str
    location: str
    skills: Optional[str] = ""
    company: Optional[str] = ""
    min_exp: Optional[int] = 0
    max_exp: Optional[int] = 40
    pages: Optional[int] = 2
    page: int = 1 
    limit: int = 20
