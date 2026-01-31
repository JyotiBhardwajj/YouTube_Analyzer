import pandas as pd

def calculate_topic_trends(df):
    df["published_at"] = pd.to_datetime(df["published_at"])
    df["month"] = df["published_at"].dt.to_period("M")

    trend_data = (
        df.groupby(["topic", "month"])
        .agg(avg_engagement=("engagement_score", "mean"))
        .reset_index()
    )

    trend_summary = []

    for topic in trend_data["topic"].unique():
        topic_df = trend_data[trend_data["topic"] == topic].sort_values("month")

        if len(topic_df) >= 2:
            last = topic_df.iloc[-1]["avg_engagement"]
            prev = topic_df.iloc[-2]["avg_engagement"]
            trend = "up" if last > prev else "down"
        elif len(topic_df) == 1:
            last = topic_df.iloc[-1]["avg_engagement"]
            trend = "stable"
        else:
            last = None
            trend = "stable"

        trend_summary.append({
            "topic": topic,
            "trend": trend,
            "latest_engagement": last
        })

    return pd.DataFrame(trend_summary)


def generate_suggestions(trends_df):
    suggestions = []

    for _, row in trends_df.iterrows():
        if row["trend"] == "up":
            suggestions.append(
                f"Post more content on '{row['topic']}' — engagement is increasing."
            )
        elif row["trend"] == "down":
            suggestions.append(
                f"Reduce posting on '{row['topic']}' — engagement is declining."
            )

    return suggestions


if __name__ == "__main__":
    df = pd.read_csv("../nlp/youtube_with_topics.csv")

    trends = calculate_topic_trends(df)
    trends.to_csv("topic_trends.csv", index=False)

    suggestions = generate_suggestions(trends)

    print("📈 Topic Trends:")
    print(trends)

    print("\n💡 Content Suggestions:")
    for s in suggestions:
        print("-", s)
