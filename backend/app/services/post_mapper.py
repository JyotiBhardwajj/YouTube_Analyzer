from datetime import datetime
from app.models.post import Post

def map_links_to_posts(links: list[str]) -> list[Post]:
    posts = []
    captions = [
        "5 tips to grow on Instagram",
        "Buy our new product now",
        "Believe in yourself and stay consistent"
    ]

    for i, link in enumerate(links):
        posts.append(
            Post(
                link=link,
                caption=captions[i % len(captions)],
                likes=500 + i * 100,
                comments=20 + i * 5,
                timestamp=datetime.now()
            )
        )

    return posts
