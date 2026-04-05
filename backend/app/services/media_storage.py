from __future__ import annotations

import logging
import re
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.run import Run
from app.models.run_media_item import RunMediaItem
from app.schemas.pipeline import VideoPayloadItem

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (compatible; VideoselzPipeline/1.0; +https://example.invalid) "
    "AppleWebKit/537.36 (KHTML, like Gecko)"
)


def _safe_filename(item: VideoPayloadItem) -> str:
    base = item.instagram_shortcode or item.instagram_media_id or "video"
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", str(base))[:120]
    return base or "video"


def download_to_local_file(url: str, dest: Path, settings: Settings) -> int:
    """Stream download to ``dest``. Returns byte size. Raises on error or size cap."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    headers = {"User-Agent": USER_AGENT}
    timeout = httpx.Timeout(settings.download_timeout_sec, connect=30.0)
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            with open(dest, "wb") as out:
                for chunk in response.iter_bytes(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > settings.max_bytes_per_video:
                        raise OSError("max_bytes_per_video exceeded")
                    out.write(chunk)
    return total


def upload_file_to_s3(local_path: Path, key: str, settings: Settings) -> None:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    session = boto3.session.Session(
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
        region_name=settings.s3_region,
    )
    client = session.client("s3")
    try:
        client.upload_file(str(local_path), settings.s3_bucket, key)
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(f"S3 upload failed: {e}") from e


def _s3_object_key(run_id: int, filename: str, settings: Settings) -> str:
    prefix = settings.s3_prefix.strip().strip("/")
    if prefix:
        return f"{prefix}/{run_id}/{filename}"
    return f"{run_id}/{filename}"


def attach_stored_media(
    db: Session,
    run: Run,
    items: list[VideoPayloadItem],
    settings: Settings,
) -> list[str]:
    """
    Download (and optionally upload) video files for each item with ``video_url``.
    Persists ``RunMediaItem`` rows and mutates ``items`` with ``stored_path`` / ``stored_url``.
    Returns human-readable error strings (empty if all succeeded).
    """
    errors: list[str] = []
    root = Path(settings.media_local_root).resolve()
    run_dir = root / str(run.id)

    for item in items:
        if not item.video_url:
            continue

        name = _safe_filename(item)
        filename = f"{name}.mp4"
        rel_path = f"{run.id}/{filename}"
        local_file = run_dir / filename

        mid = item.instagram_media_id or item.instagram_shortcode or name
        row = RunMediaItem(
            run_id=run.id,
            media_id=str(mid)[:256],
            video_source_url=item.video_url,
        )
        db.add(row)

        try:
            log.info("[media] downloading run=%s media=%s", run.id, mid)
            size = download_to_local_file(item.video_url, local_file, settings)
            row.size_bytes = size
            row.local_path = str(local_file)

            if settings.media_storage == "local":
                item.stored_path = rel_path
                item.stored_url = None
            elif settings.media_storage == "s3":
                key = _s3_object_key(run.id, filename, settings)
                upload_file_to_s3(local_file, key, settings)
                row.s3_key = key
                item.stored_path = rel_path
                item.stored_url = f"s3://{settings.s3_bucket}/{key}"
        except Exception as e:
            msg = str(e)[:800]
            row.error = msg
            err_label = f"{mid}: {msg}"
            errors.append(err_label)
            log.warning("[media] failed %s", err_label)

    db.flush()
    return errors
