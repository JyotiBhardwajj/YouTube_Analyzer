from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.analysis import AnalysisRun, Video
from app.dependencies.auth import get_current_user


router = APIRouter(prefix="/analysis", tags=["dashboard"])

@router.get("/{analysis_id}/dashboard")
def get_dashboard_data(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)  # ✅ REQUIRED
):   
    # 1️⃣ Check analysis belongs to logged-in user

    analysis = db.query(AnalysisRun).filter(
        AnalysisRun.id == analysis_id,
        AnalysisRun.user_id == current_user.id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # 2️⃣ Fetch videos
    own_videos = db.query(Video).filter(
        Video.analysis_id == analysis_id,
        Video.source == "own"
    ).all()

    competitor_videos = db.query(Video).filter(
        Video.analysis_id == analysis_id,
        Video.source == "competitor"
    ).all()

    if not own_videos:
        raise HTTPException(
            status_code=404,
            detail="No own channel videos found"
        )

    # 3️⃣ Helpers
    def avg_engagement(videos):
        return (
            sum(v.engagement_rate for v in videos) / len(videos)
            if videos else 0
        )

    def avg_views(videos):
        return (
            sum(v.views for v in videos) / len(videos)
            if videos else 0
        )

    # 4️⃣ Sort
    own_sorted = sorted(
        own_videos,
        key=lambda x: x.engagement_rate,
        reverse=True
    )

    comp_sorted = sorted(
        competitor_videos,
        key=lambda x: x.engagement_rate,
        reverse=True
    )

    # 5️⃣ Dashboard response
    return {
        "analysis_id": analysis_id,

        "own": {
            "total_videos": len(own_videos),
            "avg_views": round(avg_views(own_videos), 2),
            "avg_engagement": round(avg_engagement(own_videos), 4),
            "best_videos": [
                {
                    "title": v.title,
                    "engagement_rate": v.engagement_rate
                } for v in own_sorted[:3]
            ],
            "worst_videos": [
                {
                    "title": v.title,
                    "engagement_rate": v.engagement_rate
                } for v in own_sorted[-3:]
            ],
        },

        "competitors": {
            "total_videos": len(competitor_videos),
            "avg_views": round(avg_views(competitor_videos), 2),
            "avg_engagement": round(avg_engagement(competitor_videos), 4),
        },

        "comparison": {
            "engagement_gap": round(
                avg_engagement(competitor_videos)
                - avg_engagement(own_videos),
                4
            )
        }
    }
