from app.integrations.apify.normalize import normalize_item
from app.models.source import Source, SourceType


def test_normalize_skips_image_only() -> None:
    src = Source(id=1, type=SourceType.profile, value="test")
    raw = {"is_video": False, "shortcode": "abc", "url": "https://www.instagram.com/p/abc/"}
    assert normalize_item(raw, src) is None


def test_normalize_video() -> None:
    src = Source(id=1, type=SourceType.hashtag, value="cats")
    raw = {
        "is_video": True,
        "id": "123",
        "shortcode": "xyz",
        "url": "https://www.instagram.com/reel/xyz/",
        "video_url": "https://cdn.example/video.mp4",
        "image": "https://cdn.example/thumb.jpg",
        "caption": "hi",
        "taken_at": "2026-01-01T00:00:00Z",
        "owner": {"username": "author"},
    }
    out = normalize_item(raw, src)
    assert out is not None
    assert out.is_video is True
    assert out.instagram_media_id == "123"
    assert out.author_username == "author"
    assert out.source_type == "hashtag"
    assert out.source_value == "cats"
