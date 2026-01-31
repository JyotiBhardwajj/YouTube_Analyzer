from app.models.post import Post
from app.services.engagement import calculate_engagement

def analyze_engagement(posts: list[Post]) -> dict:
    # 🔒 SAFETY CHECK
    if not posts:
        return {
            "average_engagement": 0,
            "best_post": None,
            "worst_post": None,
            "all_posts": []
        }

    engagement_scores = []

    for post in posts:
        score = calculate_engagement(post)
        engagement_scores.append({
            "link": post.link,
            "engagement": score
        })

    avg_engagement = sum(
        item["engagement"] for item in engagement_scores
    ) / len(engagement_scores)

    best_post = max(engagement_scores, key=lambda x: x["engagement"])
    worst_post = min(engagement_scores, key=lambda x: x["engagement"])

    return {
        "average_engagement": round(avg_engagement, 2),
        "best_post": best_post,
        "worst_post": worst_post,
        "all_posts": engagement_scores
    }
