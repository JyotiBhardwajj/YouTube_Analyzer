from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.analysis import AnalysisRun
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/history", tags=["history"])

@router.get("/")
def get_history(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return (
        db.query(AnalysisRun)
        .filter(AnalysisRun.user_id == current_user.id)
        .order_by(AnalysisRun.analyzed_at.desc())
        .all()
    )
