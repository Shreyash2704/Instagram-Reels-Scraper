from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from apify_client import ApifyClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.integrations.apify.aimscrape_provider import AimscrapeInstagramProvider
from app.integrations.apify.normalize import normalize_item
from app.models.delivered_item import DeliveredItem
from app.models.run import Run, RunStatus
from app.models.source import Source
from app.schemas.pipeline import VideoPayloadItem
from app.services.destination_client import post_payload
from app.services.media_storage import attach_stored_media

log = logging.getLogger(__name__)


def _rewrite_video_urls_for_local_public(items: list[VideoPayloadItem], settings: Settings) -> None:
    """Shorten payload by pointing video_url at this API's /media mount; keep CDN in cdn_video_url."""
    if settings.media_storage != "local":
        return
    base = settings.media_public_base_url.rstrip("/")
    for m in items:
        if not m.stored_path or not m.video_url:
            continue
        m.cdn_video_url = m.video_url
        m.video_url = f"{base}/media/{m.stored_path.lstrip('/')}"


def execute_run(db: Session, run_id: int, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    run = db.get(Run, run_id)
    if run is None:
        log.error("Run %s not found", run_id)
        return

    source = db.get(Source, run.source_id)
    if source is None:
        run.status = RunStatus.failed
        run.error_message = "Source not found"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        return

    if not settings.apify_token.strip():
        run.status = RunStatus.failed
        run.error_message = "APIFY_TOKEN is not configured"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        return

    if settings.media_storage == "s3" and not settings.s3_bucket.strip():
        run.status = RunStatus.failed
        run.error_message = "S3_BUCKET is not configured for media_storage=s3"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        return

    provider = AimscrapeInstagramProvider()
    run_input = provider.build_run_input(source, settings.max_results_per_query)
    actor_id = settings.apify_actor_id.strip() or provider.actor_id()

    run.status = RunStatus.running
    run.started_at = datetime.now(timezone.utc)
    run.error_message = None
    db.commit()

    raw_items: list[dict[str, Any]] = []
    try:
        log.info("[apify] starting actor=%s run_id=%s", actor_id, run_id)
        client = ApifyClient(settings.apify_token)
        call_result = client.actor(actor_id).call(
            run_input=run_input,
            wait_secs=settings.apify_timeout_secs,
        )
        dataset_id = call_result.get("defaultDatasetId")
        run.apify_dataset_id = dataset_id
        db.commit()

        if dataset_id:
            for item in client.dataset(dataset_id).iterate_items():
                if isinstance(item, dict):
                    raw_items.append(item)
    except Exception as e:
        log.exception("[apify] run failed")
        run.status = RunStatus.failed
        run.error_message = str(e)[:2000]
        run.finished_at = datetime.now(timezone.utc)
        run.item_count = len(raw_items)
        db.commit()
        return

    run.item_count = len(raw_items)
    normalized: list[VideoPayloadItem] = []
    for raw in raw_items:
        n = normalize_item(raw, source)
        if n is not None:
            normalized.append(n)

    run.video_count = len(normalized)

    if settings.dedupe_enabled:
        filtered = []
        for n in normalized:
            mid = n.instagram_media_id or n.instagram_shortcode or ""
            if not mid:
                filtered.append(n)
                continue
            exists = (
                db.query(DeliveredItem)
                .filter(
                    DeliveredItem.source_id == source.id,
                    DeliveredItem.media_id == mid,
                )
                .first()
            )
            if exists is None:
                filtered.append(n)
        normalized = filtered

    if settings.media_storage in ("local", "s3"):
        download_errors = attach_stored_media(db, run, normalized, settings)
        if download_errors and settings.pipeline_fail_closed:
            run.status = RunStatus.failed
            run.error_message = "; ".join(download_errors)[:2000]
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            log.warning("[media] aborting run=%s due to download errors", run_id)
            return

    _rewrite_video_urls_for_local_public(normalized, settings)

    payload = [m.model_dump(mode="json") for m in normalized]
    run.delivered_count = len(payload)

    cap = settings.payload_preview_max_chars
    preview = json.dumps(payload, default=str)[:cap]
    run.payload_preview = preview

    dest_code, dest_err = post_payload(settings, payload)
    run.destination_status_code = dest_code

    if settings.destination_url.strip() and dest_err:
        if settings.pipeline_fail_closed:
            run.status = RunStatus.failed
            run.error_message = f"Destination error: {dest_err}"[:2000]
        else:
            run.status = RunStatus.completed
            run.error_message = f"Delivered with destination warning: {dest_err}"[:2000]
    else:
        run.status = RunStatus.completed
        run.error_message = None

    if run.status == RunStatus.completed and settings.dedupe_enabled and payload:
        for m in normalized:
            mid = m.instagram_media_id or m.instagram_shortcode
            if not mid:
                continue
            mid_s = str(mid)
            exists = (
                db.query(DeliveredItem)
                .filter(
                    DeliveredItem.source_id == source.id,
                    DeliveredItem.media_id == mid_s,
                )
                .first()
            )
            if exists is None:
                db.add(
                    DeliveredItem(
                        source_id=source.id,
                        media_id=mid_s,
                        first_run_id=run.id,
                    )
                )

    run.finished_at = datetime.now(timezone.utc)
    db.commit()
    log.info(
        "[normalize] run=%s items=%s videos=%s delivered=%s",
        run_id,
        run.item_count,
        run.video_count,
        run.delivered_count,
    )
