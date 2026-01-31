def classify_content(caption: str) -> dict:
    text = caption.lower()

    # Educational
    if any(word in text for word in ["tip", "how", "guide", "learn"]):
        return {
            "primary": "Educational",
            "format": "Tips & How-To"
        }

    # Motivational
    if any(word in text for word in ["believe", "success", "motivation", "inspire"]):
        return {
            "primary": "Motivational",
            "format": "Inspirational"
        }

    # Promotional
    if any(word in text for word in ["buy", "offer", "sale", "link in bio", "discount"]):
        return {
            "primary": "Promotional",
            "format": "Hard CTA"
        }

    # Personal / Relatable
    if any(word in text for word in ["my life", "relatable", "me when", "daily"]):
        return {
            "primary": "Personal",
            "format": "Relatable"
        }

    # Opinion / Commentary
    if any(word in text for word in ["opinion", "thoughts", "hot take"]):
        return {
            "primary": "Opinion",
            "format": "Commentary"
        }

    # Default
    return {
        "primary": "Entertainment",
        "format": "General"
    }
