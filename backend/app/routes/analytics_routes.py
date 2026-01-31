from fastapi import APIRouter
import pandas as pd

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/topics")
def get_topics():
    df = pd.read_csv("nlp/topics_with_engagement.csv")
    return df.to_dict(orient="records")


@router.get("/trends")
def get_trends():
    df = pd.read_csv("analytics/topic_trends.csv")
    return df.to_dict(orient="records")


@router.get("/competitor-gap")
def get_competitor_gap():
    df = pd.read_csv("analytics/topic_gap_analysis.csv")
    return df.to_dict(orient="records")


@router.get("/content-patterns")
def get_content_patterns():
    hashtags = pd.read_csv("analytics/hashtag_patterns.csv")
    captions = pd.read_csv("analytics/caption_style_patterns.csv")

    return {
        "hashtags": hashtags.to_dict(orient="records"),
        "captions": captions.to_dict(orient="records")
    }
