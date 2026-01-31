from googleapiclient.discovery import build
from app.config import YOUTUBE_API_KEY
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import re

youtube = build(
    "youtube",
    "v3",
    developerKey=YOUTUBE_API_KEY
)

def extract_channel_id(channel_url: str):
    try:
        # Handle @username URLs
        match = re.search(r"youtube\.com/@([A-Za-z0-9_-]+)", channel_url)
        if match:
            handle = match.group(1)

            response = youtube.channels().list(
                part="id",
                forHandle=handle
            ).execute()

            items = response.get("items", [])
            if items:
                return items[0]["id"]

        # Handle direct channel ID URLs
        match = re.search(r"youtube\.com/channel/([A-Za-z0-9_-]+)", channel_url)
        if match:
            return match.group(1)

        return None

    except HttpError as e:
        print("YouTube API error:", e)
        return None

    except Exception as e:
        print("Unexpected error:", e)
        return None


# Initialize YouTube client once
# youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


# def extract_channel_id(channel_url: str):
#     """
#     Converts any YouTube channel URL (@handle or /channel/)
#     into a proper channel ID (UCxxxx).
#     """

#     # Case 1: already channel ID URL
#     if "/channel/" in channel_url:
#         return channel_url.split("/channel/")[-1].split("/")[0]

#     # Case 2: @handle URL (modern YouTube)
#     if "/@" in channel_url:
#         handle = channel_url.split("/@")[-1].split("/")[0]

#         search_request = youtube.search().list(
#             part="snippet",
#             q=handle,
#             type="channel",
#             maxResults=1
#         )
#         search_response = search_request.execute()

#         if not search_response["items"]:
#             return None

#         return search_response["items"][0]["snippet"]["channelId"]

#     return None


def fetch_channel_videos(channel_url: str, max_results: int = 10):
    """
    Fetches recent videos + real metrics from a YouTube channel.
    """

    channel_id = extract_channel_id(channel_url)

    if not channel_id:
        return []

    # Get recent video IDs
    search_request = youtube.search().list(
        part="id",
        channelId=channel_id,
        maxResults=max_results,
        order="date"
    )
    search_response = search_request.execute()

    video_ids = [
        item["id"]["videoId"]
        for item in search_response["items"]
        if item["id"]["kind"] == "youtube#video"
    ]

    if not video_ids:
        return []

    # Fetch full stats for videos
    video_request = youtube.videos().list(
        part="snippet,statistics",
        id=",".join(video_ids)
    )
    video_response = video_request.execute()

    videos = []

    for item in video_response["items"]:
        snippet = item["snippet"]
        stats = item["statistics"]

        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))

        engagement_rate = (
            round((likes + comments) / views, 4)
            if views > 0 else 0
        )

        videos.append({
            "video_id": item["id"],
            "title": snippet["title"],
            "description": snippet["description"],
            "published_at": snippet["publishedAt"],
            "views": views,
            "likes": likes,
            "comments": comments,
            "engagement_rate": engagement_rate
        })

    return videos
