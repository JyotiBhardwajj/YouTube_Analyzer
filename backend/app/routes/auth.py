from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
import bcrypt
from app.utils.jwt import create_access_token


from app.database import SessionLocal
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


# =======================
# DB DEPENDENCY
# =======================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =======================
# SCHEMAS
# =======================
class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# =======================
# SIGNUP
# =======================
@router.post("/signup")
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    hashed_password = bcrypt.hashpw(
        data.password.encode(), bcrypt.gensalt()
    ).decode()

    user = User(
        name=data.name,
        email=data.email,
        password=hashed_password,
        onboarding_complete=False   # 🔥 IMPORTANT
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "User registered successfully",
        "user_id": user.id
    }


# =======================
# LOGIN
# =======================
@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not bcrypt.checkpw(
        data.password.encode(),
        user.password.encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"user_id": user.id})

    return {
        "token": token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "onboarding_complete": user.onboarding_complete
        }
    }
