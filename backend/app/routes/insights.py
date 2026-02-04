from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.database import get_db
from app.models.analysis import Video, AnalysisRun
from app.models.user import User
from app.youtube.youtube_fetch import fetch_trending_videos_by_query

router = APIRouter(prefix="/analysis", tags=["Insights"])

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for",
    "with", "your", "you", "my", "our", "is", "are", "was", "were",
    "how", "why", "what", "this", "that", "these", "those", "from",
    "by", "at", "as", "it", "be", "will", "vs", "ft", "feat"
}


def extract_topics(videos, limit=8):
    scores = {}
    for v in videos:
        title = (v.title or "").lower()
        words = [
            w.strip(".,!?()[]{}\"'").lower()
            for w in title.split()
        ]
        for w in words:
            if len(w) < 3 or w in STOPWORDS:
                continue
            scores[w] = scores.get(w, 0) + max(v.engagement_rate, 0)

    ranked = sorted(
        scores.items(), key=lambda x: x[1], reverse=True
    )
    return [w for w, _ in ranked[:limit]]


def build_niche_query(competitor_topics, own_topics, limit=5):
    pool = []
    for t in competitor_topics + own_topics:
        if t not in pool:
            pool.append(t)
        if len(pool) >= limit:
            break
    return " ".join(pool)

@router.get("/{analysis_id}/insights")
def generate_insights(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    current_analysis = db.query(AnalysisRun).filter(
        AnalysisRun.id == analysis_id,
        AnalysisRun.user_id == current_user.id
    ).first()

    if not current_analysis:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found"
        )
    base_query = db.query(Video).join(AnalysisRun).filter(
        Video.analysis_id == analysis_id,
        AnalysisRun.user_id == current_user.id
    )

    own_videos = base_query.filter(Video.source == "own").all()
    competitor_videos = base_query.filter(
        Video.source == "competitor"
    ).all()

    if not own_videos:
        raise HTTPException(
            status_code=404,
            detail="No videos found for this analysis"
        )

    total_videos = len(own_videos)

    avg_engagement = (
        sum(v.engagement_rate for v in own_videos) / total_videos
    )

    high_performers = [
        v for v in own_videos if v.engagement_rate > avg_engagement
    ]

    low_performers = [
        v for v in own_videos if v.engagement_rate < avg_engagement * 0.6
    ]

    sorted_own = sorted(
        own_videos, key=lambda x: x.engagement_rate, reverse=True
    )

    top_3 = sorted_own[:3]
    remaining_for_bottom = [
        v for v in sorted_own if v not in top_3
    ]
    bottom_3 = remaining_for_bottom[-3:] if remaining_for_bottom else []

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

    # Competitor topic gaps + suggestions
    competitor_topics = extract_topics(competitor_videos, limit=8)
    own_topics = extract_topics(own_videos, limit=8)
    topic_gaps = [
        t for t in competitor_topics if t not in own_topics
    ][:5]

    hashtag_suggestions = [
        f"#{t.replace(' ', '')}" for t in competitor_topics[:6]
    ]

    caption_suggestions = [
        f"{t.title()} in 60 seconds - here's what matters."
        for t in competitor_topics[:3]
    ]

    audio_suggestions = [
        f"Use trending audio related to '{t.title()}'."
        for t in competitor_topics[:3]
    ]

    # Growth rating based on previous analysis
    previous = (
        db.query(AnalysisRun)
        .filter(
            AnalysisRun.user_id == current_user.id,
            AnalysisRun.analyzed_at < current_analysis.analyzed_at
        )
        .order_by(AnalysisRun.analyzed_at.desc())
        .first()
    )

    previous_avg = None
    if previous:
        prev_videos = db.query(Video).filter(
            Video.analysis_id == previous.id,
            Video.source == "own"
        ).all()
        if prev_videos:
            previous_avg = sum(
                v.engagement_rate for v in prev_videos
            ) / len(prev_videos)

    growth_delta = (
        round(avg_engagement - previous_avg, 4)
        if previous_avg is not None
        else None
    )

    if growth_delta is None:
        growth_rating = "No baseline yet"
    elif growth_delta >= 0.005:
        growth_rating = "Strong growth"
    elif growth_delta >= 0.001:
        growth_rating = "Positive growth"
    elif growth_delta > -0.001:
        growth_rating = "Flat"
    else:
        growth_rating = "Needs improvement"

    # Goal-based tips
    user = db.query(User).filter(User.id == current_user.id).first()
    goal = user.goal if user else None
    goal_tips = []

    if goal == "Grow engagement":
        if avg_engagement < 0.03:
            goal_tips.append(
                "Strengthen the first 5 seconds with a clear hook."
            )
        if topic_gaps:
            goal_tips.append(
                f"Test content around '{topic_gaps[0]}' where competitors lead."
            )
    elif goal == "Beat competitors" and topic_gaps:
        goal_tips.append(
            f"Publish 2 videos around '{topic_gaps[0]}' with stronger hooks."
        )
    elif goal == "Understand what works":
        goal_tips.append(
            "Replicate formats from your top-performing topics."
        )

    competitor_avg_engagement = (
        sum(v.engagement_rate for v in competitor_videos) /
        len(competitor_videos)
        if competitor_videos else 0
    )

    niche_query = build_niche_query(
        competitor_topics, own_topics, limit=5
    )
    trending_videos = fetch_trending_videos_by_query(
        niche_query, max_results=6, region_code="US"
    )

    return {
        "analysis_id": analysis_id,
        "total_videos": total_videos,
        "average_engagement": round(avg_engagement, 4),
        "competitor_total_videos": len(competitor_videos),
        "competitor_average_engagement": round(
            competitor_avg_engagement, 4
        ),
        "engagement_gap": round(
            competitor_avg_engagement - avg_engagement, 4
        ),
        "competitor_top_topics": competitor_topics,
        "competitor_topic_gaps": topic_gaps,
        "hashtag_suggestions": hashtag_suggestions,
        "caption_suggestions": caption_suggestions,
        "audio_suggestions": audio_suggestions,
        "goal": goal,
        "goal_tips": goal_tips,
        "growth_delta": growth_delta,
        "growth_rating": growth_rating,
        "trending_ideas": trending_videos,
        "niche_query": niche_query,
        "high_performing_videos": [
            {
                "title": v.title,
                "engagement_rate": round(v.engagement_rate, 4)
            }
            for v in top_3
        ],
        "low_performing_videos": [
            {
                "title": v.title,
                "engagement_rate": round(v.engagement_rate, 4)
            }
            for v in bottom_3
        ],
        "insights": insights,
        "recommendations": recommendations
    }
