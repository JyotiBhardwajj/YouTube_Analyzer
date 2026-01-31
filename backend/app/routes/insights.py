from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.database import get_db
from app.models.analysis import Video, AnalysisRun

router = APIRouter(prefix="/analysis", tags=["Insights"])


@router.get("/{analysis_id}/insights")
def generate_insights(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    videos = db.query(Video).join(AnalysisRun).filter(
    Video.analysis_id == analysis_id,
    AnalysisRun.user_id == current_user.id
   ).all()


    if not videos:
        raise HTTPException(
            status_code=404,
            detail="No videos found for this analysis"
        )

    total_videos = len(videos)

    avg_engagement = (
        sum(v.engagement_rate for v in videos) / total_videos
    )

    high_performers = [
        v for v in videos if v.engagement_rate > avg_engagement
    ]

    low_performers = [
        v for v in videos if v.engagement_rate < avg_engagement * 0.6
    ]

    insights = []

    # 🔹 Insight 1: Engagement pattern
    if high_performers:
        insights.append(
            "Videos with concise titles and clear topics perform better."
        )

    # 🔹 Insight 2: Low engagement warning
    if low_performers:
        insights.append(
            "Some videos have significantly lower engagement. "
            "Avoid generic titles and weak hooks."
        )

    # 🔹 Insight 3: Consistency
    insights.append(
        "Maintaining consistency in topic and format improves engagement over time."
    )

    # 🔹 Recommendations
    recommendations = []

    if avg_engagement < 0.03:
        recommendations.append(
            "Focus on stronger hooks in the first 5 seconds of videos."
        )

    if len(high_performers) >= 3:
        recommendations.append(
            "Double down on topics similar to your top-performing videos."
        )

    if len(low_performers) >= 2:
        recommendations.append(
            "Rework or avoid content styles seen in low-performing videos."
        )

    return {
        "analysis_id": analysis_id,
        "total_videos": total_videos,
        "average_engagement": round(avg_engagement, 4),
        "high_performing_videos": [
            {
                "title": v.title,
                "engagement_rate": round(v.engagement_rate, 4)
            }
            for v in high_performers[:3]
        ],
        "low_performing_videos": [
            {
                "title": v.title,
                "engagement_rate": round(v.engagement_rate, 4)
            }
            for v in low_performers[:2]
        ],
        "insights": insights,
        "recommendations": recommendations
    }
