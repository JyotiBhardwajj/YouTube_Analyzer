from fastapi import APIRouter, UploadFile, File
import pandas as pd
from app.services.nlp_service import analyze_sentiment, classify_content

router = APIRouter()

@router.post("/analyze-csv")
async def analyze_csv(file: UploadFile = File(...)):
    # Read CSV into pandas
    df = pd.read_csv(file.file)

    # Required columns check
    required_cols = {"caption", "likes", "comments"}
    if not required_cols.issubset(df.columns):
        return {"error": "CSV must contain caption, likes, comments columns"}

    # Feature engineering
    df["engagement"] = df["likes"] + df["comments"]
    df["sentiment"] = df["caption"].apply(analyze_sentiment)
    df["content_type"] = df["caption"].apply(classify_content)

    # Insights
    top_posts = (
        df.sort_values(by="engagement", ascending=False)
        .head(3)[["caption", "engagement", "content_type"]]
        .to_dict(orient="records")
    )

    avg_by_type = (
        df.groupby("content_type")["engagement"]
        .mean()
        .round(0)
        .to_dict()
    )

    best_type = max(avg_by_type, key=avg_by_type.get)
    worst_type = min(avg_by_type, key=avg_by_type.get)

    recommendations = [
        f"Post more {best_type} content — it gets the highest engagement.",
        f"Reduce {worst_type} content — it performs the lowest."
    ]

    return {
        "total_posts": len(df),
        "top_posts": top_posts,
        "average_engagement_by_type": avg_by_type,
        "recommendations": recommendations
    }
