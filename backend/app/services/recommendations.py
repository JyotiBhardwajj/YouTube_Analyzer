def generate_recommendation(goal: str, best: str | None, worst: str | None) -> str:
    # 🔒 SAFETY CHECK
    if best is None or worst is None:
        return "Post more consistently and experiment with different content formats to understand what works best for your audience."

    best = best.lower()
    worst = worst.lower()

    if goal == "grow_faster":
        return (
            f"To support faster growth, increase the frequency of "
            f"{best} content and reduce {worst} posts."
        )

    if goal == "improve_engagement":
        return (
            f"To improve engagement quality, focus more on "
            f"{best} content and limit {worst} formats."
        )

    if goal == "be_consistent":
        return (
            f"To improve consistency, maintain a regular posting schedule "
            f"while prioritizing {best} content."
        )

    return "Continue experimenting with different content formats."
