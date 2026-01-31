from app.models.post import Post
from app.services.engagement import calculate_engagement
from app.services.content_classifier import classify_content

def analyze_content(posts: list[Post]) -> list[dict]:
    analyzed = []

    for post in posts:
        category = classify_content(post.caption)
        engagement = calculate_engagement(post)

        analyzed.append({
            "link": post.link,
            "primary_category": category["primary"],
            "format": category["format"],
            "engagement": engagement
        })

    return analyzed
