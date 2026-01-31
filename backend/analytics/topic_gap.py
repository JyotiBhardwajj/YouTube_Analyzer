import pandas as pd

# Load topic-tagged data
df = pd.read_csv("../nlp/youtube_with_topics.csv")

# Separate primary vs competitor data
primary_df = df[df["channel"] == "primary"]
competitor_df = df[df["channel"] != "primary"]

# Topics
primary_topics = set(primary_df["topic"].unique())
competitor_topics = set(competitor_df["topic"].unique())

# GAP = topics competitors have, you don't
gap_topics = competitor_topics - primary_topics

gap_df = competitor_df[competitor_df["topic"].isin(gap_topics)]

# Rank gap topics by engagement
gap_summary = (
    gap_df.groupby("topic")
    .agg(
        video_count=("video_id", "count"),
        avg_views=("views", "mean"),
        avg_engagement=("engagement_score", "mean")
    )
    .reset_index()
    .sort_values(by="avg_engagement", ascending=False)
)

# Save output
gap_summary.to_csv("topic_gap_analysis.csv", index=False)

print("🚨 TOPIC GAP ANALYSIS (Competitors post these, you don’t):")
print(gap_summary)
