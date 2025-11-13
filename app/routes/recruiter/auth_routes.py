from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from datetime import timedelta
from app.config.database import get_db
from app.config.recruiter_auth import create_access_token, get_password_hash, verify_password
from app.models.user import User

router = APIRouter(tags=["Recruiter Authentication"])

# 🧩 Register New User
@router.post("/recruiter/register/")
def register_user(
    employee_id: int = Form(...),
    name: str = Form(None),
    email: str = Form(None),
    mobile: str = Form(None),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(User.employee_id == employee_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee ID already registered")

    hashed_pw = get_password_hash(password)
    new_user = User(
        employee_id=employee_id,
        name=name,
        email=email,
        mobile=mobile,
        password=hashed_pw
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"status": "success", "message": "User registered successfully"}

# 🧩 Login User & Get JWT Token
@router.post("/recruiter/login/")
def login_user(
    employee_id: int = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.employee_id == employee_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid Employee ID or password")

    if not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid Employee ID or password")

    token_data = {"sub": str(user.employee_id)}
    access_token = create_access_token(data=token_data)

    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "employee_id": user.employee_id,
            "name": user.name,
            "email": user.email
        }
    }
