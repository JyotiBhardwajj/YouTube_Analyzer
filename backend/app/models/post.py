from pydantic import BaseModel
from datetime import datetime

class Post(BaseModel):
    link: str
    caption: str
    likes: int
    comments: int
    timestamp: datetime
