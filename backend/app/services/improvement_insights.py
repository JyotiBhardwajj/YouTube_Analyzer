def improvement_insight(engagement_by_category: dict, best: str | None, worst: str | None) -> str:
    # 🔒 SAFETY CHECK
    if not engagement_by_category or best is None or worst is None:
        return "Not enough data to calculate improvement insights yet."

    best_value = engagement_by_category.get(best)
    worst_value = engagement_by_category.get(worst)

    # 🔒 EXTRA SAFETY
    if best_value is None or worst_value is None or best_value == 0:
        return "Not enough data to calculate improvement insights yet."

    gap_percentage = round(
        ((best_value - worst_value) / best_value) * 100,
        2
    )

    return (
        f"{worst} content underperforms by "
        f"{gap_percentage}% compared to your best-performing content."
    )
