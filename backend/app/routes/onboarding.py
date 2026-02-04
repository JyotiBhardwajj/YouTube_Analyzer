from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class OnboardingRequest(BaseModel):
    role: str
    goal: str


@router.post("/complete")
def complete_onboarding(
    data: OnboardingRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = data.role
    user.goal = data.goal
    user.onboarding_complete = True
    db.commit()

    return {"message": "Onboarding completed"}
