from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])


class UserUpdateRequest(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    role: str | None = None
    goal: str | None = None
    weekly_summary_enabled: bool | None = None
    competitor_alerts_enabled: bool | None = None


@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "goal": user.goal,
        "weekly_summary_enabled": user.weekly_summary_enabled,
        "competitor_alerts_enabled": user.competitor_alerts_enabled,
    }


@router.put("/me")
def update_me(
    data: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.name is not None:
        user.name = data.name
    if data.email is not None:
        user.email = data.email
    if data.role is not None:
        user.role = data.role
    if data.goal is not None:
        user.goal = data.goal
    if data.weekly_summary_enabled is not None:
        user.weekly_summary_enabled = data.weekly_summary_enabled
    if data.competitor_alerts_enabled is not None:
        user.competitor_alerts_enabled = data.competitor_alerts_enabled

    db.commit()
    db.refresh(user)

    return {
        "message": "Settings updated",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "goal": user.goal,
            "weekly_summary_enabled": user.weekly_summary_enabled,
            "competitor_alerts_enabled": user.competitor_alerts_enabled,
        }
    }
