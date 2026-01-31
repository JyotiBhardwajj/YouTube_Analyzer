def category_engagement_metrics(analyzed_posts: list[dict]) -> dict:
    # 🔒 SAFETY CHECK
    if not analyzed_posts:
        return {
            "average_engagement_by_category": {},
            "best_category": None,
            "worst_category": None
        }

    category_data = {}

    for post in analyzed_posts:
        cat = post.get("primary_category")
        engagement = post.get("engagement")

        if cat is None or engagement is None:
            continue

        category_data.setdefault(cat, []).append(engagement)

    # 🔒 SAFETY CHECK
    if not category_data:
        return {
            "average_engagement_by_category": {},
            "best_category": None,
            "worst_category": None
        }

    category_avg = {
        cat: round(sum(values) / len(values), 2)
        for cat, values in category_data.items()
        if values
    }

    # 🔒 FINAL SAFETY
    if not category_avg:
        return {
            "average_engagement_by_category": {},
            "best_category": None,
            "worst_category": None
        }

    best_category = max(category_avg, key=category_avg.get)
    worst_category = min(category_avg, key=category_avg.get)

    return {
        "average_engagement_by_category": category_avg,
        "best_category": best_category,
        "worst_category": worst_category
    }
