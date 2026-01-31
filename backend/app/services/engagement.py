from app.models.post import Post

def calculate_engagement(post: Post) -> int:
    return post.likes + post.comments
