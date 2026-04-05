import json
from typing import Any

from app.models.source import Source
from app.schemas.pipeline import VideoPayloadItem

RAW_MAX = 800


def normalize_item(raw: dict[str, Any], source: Source) -> VideoPayloadItem | None:
    """Return a payload item for video posts; skip non-video items without video_url."""
    is_video = bool(raw.get("is_video"))
    video_url = raw.get("video_url")
    if not is_video and not video_url:
        return None

    owner = raw.get("owner") or {}
    author = owner.get("username") if isinstance(owner, dict) else None

    raw_str = json.dumps(raw, default=str)[:RAW_MAX]

    return VideoPayloadItem(
        source_type=source.type.value,
        source_value=source.value,
        instagram_shortcode=raw.get("shortcode"),
        instagram_media_id=str(raw.get("id") or raw.get("pk") or "") or None,
        permalink=raw.get("url"),
        video_url=video_url if video_url else None,
        thumbnail_url=raw.get("image"),
        caption=raw.get("caption"),
        taken_at=raw.get("taken_at"),
        author_username=author,
        is_video=bool(is_video or video_url),
        raw_excerpt=raw_str,
    )
