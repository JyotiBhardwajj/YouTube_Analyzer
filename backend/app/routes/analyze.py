from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.youtube.youtube_fetch import fetch_channel_videos
from app.database import get_db
from app.models.analysis import AnalysisRun, Video
from app.dependencies.auth import get_current_user


router = APIRouter(prefix="/analyze", tags=["analyze"])
from app.models.user import User
 # or wherever you get user


@router.post("/youtube")
def analyze_youtube(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    channel_url = data.get("channel_url")
    if not channel_url:
        raise HTTPException(status_code=400, detail="Channel URL required")

    videos_data = fetch_channel_videos(channel_url)


    analysis = AnalysisRun(
        channel_url=channel_url,
        user_id=current_user.id
     )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)


    for v in videos_data:
        video = Video(
            analysis_id=analysis.id,
            video_id=v["video_id"],
            title=v["title"],
            views=v["views"],
            likes=v["likes"],
            comments=v["comments"],
            engagement_rate=v["engagement_rate"],
            source="own"
        )
        db.add(video)

    db.commit()

    return {
        "analysis_id": analysis.id,
        "total_videos": len(videos_data)
    }


@router.get("/analysis/{analysis_id}/summary")
def get_analysis_summary(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user) 
):
    analysis = db.query(AnalysisRun).filter(
        AnalysisRun.id == analysis_id,
        AnalysisRun.user_id == current_user.id  # ⬅️ USER FILTER
    ).first()


    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    videos = db.query(Video).filter(
        Video.analysis_id == analysis_id
    ).all()

    if not videos:
        raise HTTPException(status_code=404, detail="No videos found")

    total = len(videos)
    avg_views = sum(v.views for v in videos) / total
    avg_engagement = sum(v.engagement_rate for v in videos) / total

    sorted_videos = sorted(
        videos,
        key=lambda x: x.engagement_rate,
        reverse=True
    )

    return {
        "analysis_id": analysis_id,
        "total_videos": total,
        "avg_views": round(avg_views, 2),
        "avg_engagement": round(avg_engagement, 4),
        "top_videos": [
            {
                "title": v.title,
                "engagement_rate": v.engagement_rate
            } for v in sorted_videos[:2]
        ],
        "low_videos": [
            {
                "title": v.title,
                "engagement_rate": v.engagement_rate
            } for v in sorted_videos[-1:]
        ]
    }

@router.get("/analysis/latest")
def get_latest_analysis(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    latest = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.user_id == current_user.id)
        .order_by(AnalysisRun.analyzed_at.desc())
        .first()
    )

    if not latest:
        raise HTTPException(status_code=404, detail="No analysis found")

    return {
        "analysis_id": latest.id,
        "channel_url": latest.channel_url,
        "created_at": latest.analyzed_at,
    }

@router.get("/analysis/history")
def get_analysis_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    analyses = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.user_id == current_user.id)
        .order_by(AnalysisRun.analyzed_at.desc())
        .all()
    )

    if not analyses:
        return []

    return [
        {
            "analysis_id": a.id,
            "channel_url": a.channel_url,
            "created_at": a.analyzed_at,
        }
        for a in analyses
    ]