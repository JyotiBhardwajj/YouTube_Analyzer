from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.youtube.youtube_fetch import fetch_channel_videos
from app.services.content_analysis import analyze_videos
from app.services.engagement_analysis import calculate_engagement

router = APIRouter(prefix="/analyze", tags=["analysis"])


class YouTubeAnalyzeRequest(BaseModel):
    channel_url: str


@router.post("/youtube")
def analyze_youtube_channel(data: YouTubeAnalyzeRequest):
    """
    1. Fetch videos from YouTube
    2. Analyze topics + engagement
    3. Return structured analysis
    """

    # STEP 1: Fetch YouTube data
    videos = fetch_channel_videos(data.channel_url)

    if not videos:
        raise HTTPException(status_code=400, detail="No videos found")

    # STEP 2: NLP + Topic analysis
    analyzed = analyze_videos(videos)

    # STEP 3: Engagement metrics
    insights = calculate_engagement(analyzed)

    return {
        "total_videos": len(videos),
        "top_topics": insights["top_topics"],
        "low_topics": insights["low_topics"],
        "engagement_summary": insights["summary"]
    }
