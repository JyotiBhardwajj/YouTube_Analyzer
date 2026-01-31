from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

@router.post("/complete")
def complete_onboarding(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == current_user.id).first()
    user.onboarding_complete = True
    db.commit()

    return {"message": "Onboarding completed"}
