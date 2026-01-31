import pandas as pd
import re

df = pd.read_csv("../nlp/youtube_with_topics.csv")

# ---------- HASHTAG ANALYSIS ----------

def extract_hashtags(text):
    if not isinstance(text, str):
        return []
    return re.findall(r"#\w+", text.lower())

df["hashtags"] = df["description"].apply(extract_hashtags)

hashtag_df = df.explode("hashtags")

hashtag_summary = (
    hashtag_df.groupby(["topic", "hashtags"])
    .agg(
        usage_count=("video_id", "count"),
        avg_engagement=("engagement_score", "mean")
    )
    .reset_index()
    .sort_values(by="avg_engagement", ascending=False)
)

hashtag_summary.to_csv("hashtag_patterns.csv", index=False)

# ---------- CAPTION STYLE ANALYSIS ----------

df["caption_length"] = df["title"].apply(lambda x: len(x.split()) if isinstance(x, str) else 0)
df["is_question"] = df["title"].apply(lambda x: "?" in x if isinstance(x, str) else False)

caption_summary = (
    df.groupby("topic")
    .agg(
        avg_caption_length=("caption_length", "mean"),
        question_ratio=("is_question", "mean"),
        avg_engagement=("engagement_score", "mean")
    )
    .reset_index()
)

caption_summary.to_csv("caption_style_patterns.csv", index=False)

# ---------- AUDIO / CONTENT STYLE (SIMULATED) ----------

# Using duration proxy via views/comments ratio
df["interaction_ratio"] = (df["comments"] + 1) / (df["views"] + 1)

audio_summary = (
    df.groupby("topic")
    .agg(
        avg_interaction_ratio=("interaction_ratio", "mean"),
        avg_engagement=("engagement_score", "mean")
    )
    .reset_index()
)

audio_summary.to_csv("audio_style_patterns.csv", index=False)

print("✅ Day 5: Content pattern analysis completed")
