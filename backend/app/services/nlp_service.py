from textblob import TextBlob

# Sentiment function
def analyze_sentiment(text: str) -> float:
    return TextBlob(text).sentiment.polarity


# Content classification
CATEGORIES = {
    "Motivational": ["believe", "success", "hard work", "consistent", "focus"],
    "Educational": ["how", "tips", "learn", "guide", "coding", "routine"],
    "Entertainment": ["vlog", "fun", "random", "thoughts", "2 AM"],
    "Promotional": ["buy", "sale", "offer", "product", "link in bio"]
}

def classify_content(text: str) -> str:
    text = text.lower()
    for category, keywords in CATEGORIES.items():
        for word in keywords:
            if word in text:
                return category
    return "Other"