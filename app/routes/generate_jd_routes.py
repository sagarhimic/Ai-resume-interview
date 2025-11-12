from fastapi import APIRouter
from app.controllers.generate_jd import router as jd_router

router = APIRouter()
router.include_router(jd_router)
