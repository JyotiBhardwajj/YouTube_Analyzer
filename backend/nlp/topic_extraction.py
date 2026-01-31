import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from nltk.corpus import stopwords

STOPWORDS = set(stopwords.words("english"))

def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[^a-z\s]", "", text)
    words = [w for w in text.split() if w not in STOPWORDS]
    return " ".join(words)

def extract_topics(df, num_topics=5):
    # Combine title + description
    df["content"] = df["title"] + " " + df["description"]
    df["clean_content"] = df["content"].apply(clean_text)

    vectorizer = TfidfVectorizer(max_df=0.9, min_df=2)
    X = vectorizer.fit_transform(df["clean_content"])

    kmeans = KMeans(n_clusters=num_topics, random_state=42)
    df["topic_id"] = kmeans.fit_predict(X)

    # Get top keywords per topic
    terms = vectorizer.get_feature_names_out()
    topic_keywords = {}

    for i in range(num_topics):
        center = kmeans.cluster_centers_[i]
        top_terms = [terms[ind] for ind in center.argsort()[-5:]]
        topic_keywords[i] = ", ".join(top_terms)

    df["topic"] = df["topic_id"].map(topic_keywords)
    return df

def topic_engagement_analysis(df):
    df["engagement_score"] = (
        df["likes"] + 2 * df["comments"]
    ) / df["views"].replace(0, 1)

    summary = (
        df.groupby("topic")
        .agg(
            video_count=("video_id", "count"),
            avg_views=("views", "mean"),
            avg_likes=("likes", "mean"),
            avg_comments=("comments", "mean"),
            avg_engagement=("engagement_score", "mean"),
        )
        .reset_index()
        .sort_values(by="avg_engagement", ascending=False)
    )

    return summary

if __name__ == "__main__":
    df = pd.read_csv("../youtube/youtube_competitor_data.csv")


    df_with_topics = extract_topics(df, num_topics=5)
    df_with_topics["engagement_score"] = (
    df_with_topics["likes"] + 2 * df_with_topics["comments"]
) / df_with_topics["views"].replace(0, 1)

    df_with_topics.to_csv("youtube_with_topics.csv", index=False)

    topic_summary = topic_engagement_analysis(df_with_topics)

    topic_summary.to_csv("topics_with_engagement.csv", index=False)

    print("✅ Topics extracted successfully!")
    print(topic_summary)
