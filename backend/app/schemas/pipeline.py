from pydantic import BaseModel, Field


class VideoPayloadItem(BaseModel):
    source_type: str
    source_value: str
    instagram_shortcode: str | None = None
    instagram_media_id: str | None = None
    permalink: str | None = None
    video_url: str | None = None
    cdn_video_url: str | None = Field(
        default=None,
        description="Original Instagram CDN URL when video_url was rewritten to a local /media/... link",
    )
    thumbnail_url: str | None = None
    caption: str | None = None
    taken_at: str | None = None
    author_username: str | None = None
    is_video: bool = False
    raw_excerpt: str | None = Field(default=None, description="Truncated raw JSON for debugging")
    stored_path: str | None = Field(
        default=None,
        description="Relative path under media root (local) or same layout before S3 upload",
    )
    stored_url: str | None = Field(
        default=None,
        description="s3://bucket/key when uploaded to S3; optional public HTTPS if configured",
    )
