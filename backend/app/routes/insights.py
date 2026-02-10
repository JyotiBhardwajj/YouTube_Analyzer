from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.database import get_db
from app.models.analysis import Video, AnalysisRun
from app.models.user import User
from app.youtube.youtube_fetch import fetch_trending_videos_by_query

import numpy as np
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, ParameterGrid
from sklearn.decomposition import PCA
try:
    from textblob import TextBlob
except Exception:
    TextBlob = None
try:
    from bertopic import BERTopic
except Exception:
    BERTopic = None
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans

router = APIRouter(prefix="/analysis", tags=["Insights"])

# Load embedding model once
model = SentenceTransformer("all-MiniLM-L6-v2")

def compute_sentiment(text: str):
    if not text or not TextBlob:
        return 0.0
    try:
        return float(TextBlob(text).sentiment.polarity)
    except Exception:
        return 0.0

def extract_text_signals(videos):
    texts = []
    for v in videos:
        parts = [v.title, getattr(v, "description", None), getattr(v, "transcript", None)]
        combined = " ".join([p for p in parts if p]).strip()
        if combined:
            texts.append(combined)
    return texts

def extract_transcript_signals(videos):
    return [getattr(v, "transcript", None) for v in videos if getattr(v, "transcript", None)]

def extract_thumbnail_signals(videos):
    return [
        getattr(v, "thumbnail_brightness", None)
        for v in videos
        if getattr(v, "thumbnail_brightness", None) is not None
    ]


# 🔹 Topic extraction using embeddings + clustering
def extract_topics(videos, n_clusters=5):
    texts = extract_text_signals(videos)
    if not texts:
        return []

    embeddings = model.encode(texts)
    kmeans = KMeans(n_clusters=min(n_clusters, len(texts)), random_state=42)
    labels = kmeans.fit_predict(embeddings)

    clusters = {}
    for i, label in enumerate(labels):
        clusters.setdefault(label, []).append(texts[i])

    # Representative topic = first title in each cluster
    topics = [texts[0] for texts in clusters.values()]
    return topics


# 🔹 Engagement prediction model (richer features + CV)
def build_feature_matrix(videos):
    texts = extract_text_signals(videos)
    if not texts:
        return None, None

    embeddings = model.encode(texts)
    n_samples = len(embeddings)

    pca_dims = 8 if n_samples >= 5 else min(2, n_samples)
    if pca_dims >= 2:
        pca = PCA(n_components=pca_dims, random_state=42)
        reduced = pca.fit_transform(embeddings)
    else:
        reduced = np.zeros((n_samples, 1))

    k_clusters = min(5, n_samples)
    if k_clusters >= 2:
        kmeans = KMeans(n_clusters=k_clusters, random_state=42)
        cluster_ids = kmeans.fit_predict(embeddings)
    else:
        cluster_ids = np.zeros(n_samples, dtype=int)

    rows = []
    y = []
    text_idx = 0
    for v in videos:
        parts = [v.title, getattr(v, "description", None), getattr(v, "transcript", None)]
        combined = " ".join([p for p in parts if p]).strip()
        if not combined:
            continue

        title_len = len(v.title or "")
        word_count = len((v.title or "").split())
        hour = v.published_at.hour if getattr(v, "published_at", None) else 0
        weekday = v.published_at.weekday() if getattr(v, "published_at", None) else 0
        transcript_sentiment = compute_sentiment(getattr(v, "transcript", "") or "")
        thumb_brightness = getattr(v, "thumbnail_brightness", None)
        thumb_brightness = thumb_brightness if thumb_brightness is not None else 0.0

        emb_features = reduced[text_idx].tolist()
        cluster_id = int(cluster_ids[text_idx])

        rows.append([
            title_len,
            word_count,
            hour,
            weekday,
            transcript_sentiment,
            thumb_brightness,
            cluster_id,
            *emb_features
        ])
        y.append(v.engagement_rate)
        text_idx += 1

    if not rows:
        return None, None

    return np.array(rows, dtype=float), np.array(y, dtype=float)

def train_engagement_model(videos):
    if not videos or len(videos) < 5:
        return None, None

    X, y = build_feature_matrix(videos)
    if X is None:
        return None, None

    n_samples = len(y)
    n_splits = 3 if n_samples >= 6 else 2
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)

    param_grid = {
        "learning_rate": [0.05, 0.1],
        "max_depth": [3, 5],
        "n_estimators": [100, 200]
    }

    best = None
    for params in ParameterGrid(param_grid):
        r2_scores = []
        mae_scores = []
        rmse_scores = []

        for train_idx, test_idx in kf.split(X):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            model = XGBRegressor(
                learning_rate=params["learning_rate"],
                max_depth=params["max_depth"],
                n_estimators=params["n_estimators"],
                random_state=42
            )
            model.fit(X_train, y_train)
            preds = model.predict(X_test)

            mae_scores.append(mean_absolute_error(y_test, preds))
            rmse_scores.append(mean_squared_error(y_test, preds) ** 0.5)
            if len(y_test) >= 2:
                r2_scores.append(r2_score(y_test, preds))

        avg_r2 = float(np.mean(r2_scores)) if r2_scores else None
        avg_mae = float(np.mean(mae_scores))
        avg_rmse = float(np.mean(rmse_scores))

        candidate = {
            "params": params,
            "r2": avg_r2,
            "mae": avg_mae,
            "rmse": avg_rmse
        }

        if best is None:
            best = candidate
        else:
            if candidate["r2"] is not None and best["r2"] is not None:
                if candidate["r2"] > best["r2"]:
                    best = candidate
            elif candidate["r2"] is not None and best["r2"] is None:
                best = candidate
            elif candidate["r2"] is None and best["r2"] is None:
                if candidate["rmse"] < best["rmse"]:
                    best = candidate

    if best is None:
        return None, None

    r2 = best["r2"]
    if r2 is None:
        confidence_label = "Low Confidence"
    elif r2 >= 0.5:
        confidence_label = "High Confidence"
    elif r2 >= 0.2:
        confidence_label = "Medium Confidence"
    else:
        confidence_label = "Low Confidence"

    metrics = {
        "r2": round(r2, 4) if r2 is not None else None,
        "mae": round(best["mae"], 4),
        "rmse": round(best["rmse"], 4),
        "confidence_label": confidence_label,
        "cv_folds": n_splits,
        "best_params": best["params"]
    }

    return None, metrics


# 🔹 Build query for trending video suggestions
def build_niche_query(competitor_topics, own_topics, limit=5):
    pool = []
    for t in competitor_topics + own_topics:
        if not t:
            continue
        if t not in pool:
            pool.append(t)
        if len(pool) >= limit:
            break
    return " ".join(pool).strip()

def extract_trending_terms(videos, limit=8):
    scores = {}
    for v in videos:
        title = (v.title or "").lower()
        words = [
            w.strip(".,!?()[]{}\"'").lower()
            for w in title.split()
        ]
        for w in words:
            if len(w) < 3:
                continue
            scores[w] = scores.get(w, 0) + max(v.engagement_rate, 0)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in ranked[:limit]]

def get_bertopic_topics(texts, top_n=6):
    if not texts:
        return []

    if BERTopic is None:
        return []

    topic_model = BERTopic(verbose=False)
    topics, _ = topic_model.fit_transform(texts)

    counts = {}
    for t in topics:
        if t == -1:
            continue
        counts[t] = counts.get(t, 0) + 1

    ranked_topics = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    labels = []
    for topic_id, _ in ranked_topics[:top_n]:
        words = topic_model.get_topic(topic_id) or []
        top_words = [w for w, _ in words[:3]]
        if top_words:
            labels.append(" ".join(top_words))

    return labels

def jaccard_distance(a, b):
    set_a = set(a or [])
    set_b = set(b or [])
    if not set_a and not set_b:
        return None
    union = set_a | set_b
    intersection = set_a & set_b
    return 1 - (len(intersection) / len(union))

def novelty_score(current, previous):
    current_set = set(current or [])
    if not current_set:
        return None
    previous_set = set(previous or [])
    unseen = current_set - previous_set
    return len(unseen) / len(current_set)

def _clean_word(word: str) -> str:
    return "".join(ch for ch in word.lower() if ch.isalnum())

def build_hashtag_suggestions(topics, limit=12):
    if not topics:
        return []

    tags = []
    seen = set()
    for topic in topics:
        if not topic:
            continue
        for raw in topic.replace(",", " ").split():
            word = _clean_word(raw)
            if len(word) < 3:
                continue
            tag = f"#{word}"
            if tag in seen:
                continue
            seen.add(tag)
            tags.append(tag)
            if len(tags) >= limit:
                return tags

    for tag in ["#content", "#creator", "#shorts", "#growth"]:
        if len(tags) >= limit:
            break
        if tag not in seen:
            tags.append(tag)
            seen.add(tag)

    return tags

def build_caption_suggestions(topics, limit=6):
    if not topics:
        return []

    captions = []
    for topic in topics[:max(1, limit // 2)]:
        if not topic:
            continue
        clean = topic.split(",")[0].strip()
        if not clean:
            continue
        captions.extend([
            f"Most people misunderstand {clean}. Here is the truth.",
            f"If {clean} feels confusing, watch this.",
            f"{clean} explained simply.",
        ])
        if len(captions) >= limit:
            break

    return captions[:limit]


@router.get("/{analysis_id}/insights")
def generate_insights(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    region: Optional[str] = "US"
):
    current_analysis = db.query(AnalysisRun).filter(
        AnalysisRun.id == analysis_id,
        AnalysisRun.user_id == current_user.id
    ).first()

    if not current_analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    base_query = db.query(Video).join(AnalysisRun).filter(
        Video.analysis_id == analysis_id,
        AnalysisRun.user_id == current_user.id
    )

    own_videos = base_query.filter(Video.source == "own").all()
    competitor_videos = base_query.filter(Video.source == "competitor").all()

    if not own_videos:
        raise HTTPException(status_code=404, detail="No videos found for this analysis")

    total_videos = len(own_videos)
    avg_engagement = sum(v.engagement_rate for v in own_videos) / total_videos

    # High/low performers
    high_performers = [v for v in own_videos if v.engagement_rate > avg_engagement]
    low_performers = [v for v in own_videos if v.engagement_rate < avg_engagement * 0.6]

    sorted_own = sorted(own_videos, key=lambda x: x.engagement_rate, reverse=True)
    top_3 = sorted_own[:3]
    remaining_for_bottom = [v for v in sorted_own if v not in top_3]
    bottom_3 = remaining_for_bottom[-3:] if remaining_for_bottom else []

    insights = []
    if high_performers:
        insights.append("Videos with concise titles and clear topics perform better.")
    if low_performers:
        insights.append("Some videos have significantly lower engagement. Avoid generic titles and weak hooks.")
    insights.append("Maintaining consistency in topic and format improves engagement over time.")

    recommendations = []
    if avg_engagement < 0.03:
        recommendations.append("Focus on stronger hooks in the first 5 seconds of videos.")
    if len(high_performers) >= 3:
        recommendations.append("Double down on topics similar to your top-performing videos.")
    if len(low_performers) >= 2:
        recommendations.append("Rework or avoid content styles seen in low-performing videos.")

    # 🔹 Competitor topics + gaps
    competitor_topics = extract_topics(competitor_videos, n_clusters=5)
    own_topics = extract_topics(own_videos, n_clusters=5)
    topic_gaps = [t for t in competitor_topics if t not in own_topics][:5]

    # 🔹 Engagement prediction for competitor-only topics
    model, model_evaluation = train_engagement_model(own_videos)
    predicted_opportunities = []
    if model_evaluation and topic_gaps:
        for t in topic_gaps:
            title_len = len(t)
            word_count = len(t.split())
            predicted_opportunities.append({
                "topic": t,
                "predicted_engagement": None
            })

    # Competitor engagement stats
    competitor_avg_engagement = (
        sum(v.engagement_rate for v in competitor_videos) / len(competitor_videos)
        if competitor_videos else 0
    )

    trending_own_topics = extract_trending_terms(own_videos, limit=8)
    niche_query = build_niche_query(trending_own_topics, [], limit=5)
    if not niche_query:
        fallback_titles = [v.title for v in top_3 if v.title]
        niche_query = " ".join(fallback_titles).strip()

    region_code = None if (region and region.upper() == "GLOBAL") else region

    trending_videos = fetch_trending_videos_by_query(
        niche_query, max_results=6, region_code=region_code
    )

    topic_seed = topic_gaps or competitor_topics or own_topics
    hashtag_suggestions = build_hashtag_suggestions(topic_seed, limit=12)
    caption_suggestions = build_caption_suggestions(topic_seed, limit=6)

    text_signals = extract_text_signals(own_videos)
    transcript_signals = extract_transcript_signals(own_videos)
    thumbnail_signals = extract_thumbnail_signals(own_videos)
    text_active = len(text_signals) > 0
    transcript_active = len(transcript_signals) > 0
    thumbnail_active = len(thumbnail_signals) > 0

    if text_active and transcript_active and thumbnail_active:
        multimodal_summary = "We analyzed titles, descriptions, transcripts, and thumbnails."
    elif text_active and transcript_active:
        multimodal_summary = "We analyzed titles, descriptions, and transcripts. Thumbnails are not connected yet."
    elif text_active and thumbnail_active:
        multimodal_summary = "We analyzed titles, descriptions, and thumbnails. Transcripts are not connected yet."
    elif text_active:
        multimodal_summary = "We analyzed titles and descriptions. Add transcripts or thumbnails for deeper insights."
    else:
        multimodal_summary = "No multimodal signals are available yet."

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
    prev_videos = None
    if previous:
        prev_videos = db.query(Video).filter(
            Video.analysis_id == previous.id,
            Video.source == "own"
        ).all()
        if prev_videos:
            previous_avg = sum(v.engagement_rate for v in prev_videos) / len(prev_videos)

    growth_delta = (
        round(avg_engagement - previous_avg, 4)
        if previous_avg is not None else None
    )

    trend_velocity = None
    if previous and previous_avg is not None:
        delta_days = (current_analysis.analyzed_at - previous.analyzed_at).days
        if delta_days <= 0:
            delta_days = 1
        trend_velocity = round((avg_engagement - previous_avg) / delta_days, 6)

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
            goal_tips.append("Strengthen the first 5 seconds with a clear hook.")
        if topic_gaps:
            goal_tips.append(f"Test content around '{topic_gaps[0]}' where competitors lead.")
    elif goal == "Beat competitors" and topic_gaps:
        goal_tips.append(f"Publish 2 videos around '{topic_gaps[0]}' with stronger hooks.")
    elif goal == "Understand what works":
        goal_tips.append("Replicate formats from your top-performing topics.")

    # Topic modeling (BERTopic + drift + novelty)
    own_texts = extract_text_signals(own_videos)
    competitor_texts = extract_text_signals(competitor_videos)
    bertopic_own = get_bertopic_topics(own_texts, top_n=6)
    bertopic_competitor = get_bertopic_topics(competitor_texts, top_n=6)

    if not bertopic_own:
        bertopic_own = extract_trending_terms(own_videos, limit=6)
    if not bertopic_competitor:
        bertopic_competitor = extract_trending_terms(competitor_videos, limit=6)

    previous_own_topics = None
    if prev_videos:
        previous_own_topics = extract_trending_terms(prev_videos, limit=6)

    drift = jaccard_distance(bertopic_own, previous_own_topics)
    novelty = novelty_score(bertopic_own, previous_own_topics)

    return {
        "analysis_id": analysis_id,
        "total_videos": total_videos,
        "average_engagement": round(avg_engagement, 4),
        "competitor_total_videos": len(competitor_videos),
        "competitor_average_engagement": round(competitor_avg_engagement, 4),
        "engagement_gap": round(competitor_avg_engagement - avg_engagement, 4),
        "competitor_topic_gaps": topic_gaps,
        "predicted_opportunities": predicted_opportunities,
        "model_score": model_evaluation["r2"] if model_evaluation else None,
        "model_evaluation": model_evaluation,
        "recommendations": recommendations,
        "goal": goal,
        "goal_tips": goal_tips,
        "growth_delta": growth_delta,
        "growth_rating": growth_rating,
        "trend_velocity": trend_velocity,
        "trending_ideas": trending_videos,
        "niche_query": niche_query,
        "hashtag_suggestions": hashtag_suggestions,
        "caption_suggestions": caption_suggestions,
        "topic_modeling": {
            "model_used": "bertopic" if BERTopic is not None else "fallback_keywords",
            "own_topics": bertopic_own,
            "competitor_topics": bertopic_competitor,
            "drift_score": drift,
            "novelty_score": novelty
        },
        "multimodal_signals": {
            "text": {
                "available": text_active,
                "notes": "Titles and descriptions analyzed." if text_active else "No text data available yet."
            },
            "thumbnail": {
                "available": thumbnail_active,
                "notes": "Thumbnails analyzed." if thumbnail_active else "Thumbnail analysis not connected yet."
            },
            "transcript": {
                "available": transcript_active,
                "notes": "Transcripts analyzed." if transcript_active else "Transcripts not connected yet."
            },
            "summary": multimodal_summary
        },
        "high_performing_videos": [
            {"title": v.title, "engagement_rate": round(v.engagement_rate, 4)}
            for v in top_3
        ],
        "low_performing_videos": [
            {"title": v.title, "engagement_rate": round(v.engagement_rate, 4)}
            for v in bottom_3
        ],
        "insights": insights,
    }
