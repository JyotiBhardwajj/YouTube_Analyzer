from googleapiclient.discovery import build
from app.config import YOUTUBE_API_KEY
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import re
import json
from datetime import datetime
try:
    from youtube_transcript_api import YouTubeTranscriptApi
except Exception:
    YouTubeTranscriptApi = None
try:
    import whisper
except Exception:
    whisper = None
try:
    import yt_dlp
except Exception:
    yt_dlp = None
try:
    import requests
    from PIL import Image
    from io import BytesIO
except Exception:
    requests = None
    Image = None
    BytesIO = None
try:
    from transformers import CLIPModel, CLIPProcessor
except Exception:
    CLIPModel = None
    CLIPProcessor = None

youtube = build(
    "youtube",
    "v3",
    developerKey=YOUTUBE_API_KEY
)

_clip_model = None
_clip_processor = None
_whisper_model = None

def _load_clip():
    global _clip_model, _clip_processor
    if _clip_model is None and CLIPModel and CLIPProcessor:
        _clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        _clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    return _clip_model, _clip_processor

def _load_whisper():
    global _whisper_model
    if _whisper_model is None and whisper:
        _whisper_model = whisper.load_model("base")
    return _whisper_model

def parse_published_at(value: str | None):
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except Exception:
        return None

def get_transcript_text(video_id: str):
    if not video_id:
        return None
    if YouTubeTranscriptApi:
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            return " ".join([t.get("text", "") for t in transcript]).strip() or None
        except Exception:
            pass
    if whisper and yt_dlp:
        try:
            ydl_opts = {
                "format": "bestaudio/best",
                "quiet": True,
                "outtmpl": "%(id)s.%(ext)s"
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
                filename = ydl.prepare_filename(info)
            model = _load_whisper()
            if not model:
                return None
            result = model.transcribe(filename)
            text = result.get("text", "").strip() or None
            try:
                import os
                if filename and os.path.exists(filename):
                    os.remove(filename)
            except Exception:
                pass
            return text
        except Exception:
            return None
    return None

def compute_thumbnail_brightness(url: str | None):
    if not url or not requests or not Image:
        return None
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("L")
        pixels = list(img.getdata())
        if not pixels:
            return None
        return round(sum(pixels) / len(pixels) / 255, 4)
    except Exception:
        return None

def compute_thumbnail_embedding(url: str | None):
    if not url or not requests or not Image:
        return None
    model, processor = _load_clip()
    if not model or not processor:
        return None
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        image = Image.open(BytesIO(resp.content)).convert("RGB")
        inputs = processor(images=image, return_tensors="pt")
        outputs = model.get_image_features(**inputs)
        embedding = outputs[0].tolist()
        return json.dumps(embedding)
    except Exception:
        return None

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

        thumbnails = snippet.get("thumbnails", {}) or {}
        thumb = (
            thumbnails.get("high")
            or thumbnails.get("medium")
            or thumbnails.get("default")
            or {}
        )
        thumb_url = thumb.get("url")
        transcript = get_transcript_text(item["id"])
        thumbnail_brightness = compute_thumbnail_brightness(thumb_url)
        thumbnail_embedding = compute_thumbnail_embedding(thumb_url)

        videos.append({
            "video_id": item["id"],
            "title": snippet["title"],
            "description": snippet["description"],
            "published_at": snippet["publishedAt"],
            "transcript": transcript,
            "thumbnail_url": thumb_url,
            "thumbnail_brightness": thumbnail_brightness,
            "thumbnail_embedding": thumbnail_embedding,
            "views": views,
            "likes": likes,
            "comments": comments,
            "engagement_rate": engagement_rate
        })

    return videos


def fetch_trending_videos_by_query(
    query: str,
    max_results: int = 6,
    region_code: str | None = "US"
):
    """
    Fetch trending videos by query (niche keywords) using YouTube search.
    """
    if not query:
        return []

    request_kwargs = {
        "part": "id",
        "q": query,
        "maxResults": max_results,
        "order": "viewCount",
        "type": "video",
        "safeSearch": "none",
    }
    if region_code:
        request_kwargs["regionCode"] = region_code

    try:
        search_request = youtube.search().list(**request_kwargs)
        search_response = search_request.execute()
    except Exception as e:
        print("YouTube API error (search):", e)
        return []

    video_ids = [
        item["id"]["videoId"]
        for item in search_response.get("items", [])
        if item.get("id", {}).get("videoId")
    ]

    if not video_ids:
        return []

    try:
        video_request = youtube.videos().list(
            part="snippet,statistics",
            id=",".join(video_ids)
        )
        video_response = video_request.execute()
    except Exception as e:
        print("YouTube API error (videos):", e)
        return []

    videos = []
    for item in video_response.get("items", []):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})

        videos.append({
            "title": snippet.get("title"),
            "channel": snippet.get("channelTitle"),
            "published_at": snippet.get("publishedAt"),
            "views": int(stats.get("viewCount", 0))
        })

    return videos
