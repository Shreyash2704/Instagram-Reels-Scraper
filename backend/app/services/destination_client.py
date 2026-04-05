import logging
import time
from typing import Any

import httpx

from app.core.config import Settings

log = logging.getLogger(__name__)


def post_payload(
    settings: Settings,
    payload: list[dict[str, Any]],
) -> tuple[int | None, str | None]:
    """POST JSON array to destination. Returns (status_code, error_message)."""
    url = (settings.destination_url or "").strip()
    if not url:
        log.info("[destination] DESTINATION_URL not set; skipping POST")
        return None, None

    last_err: str | None = None
    for attempt in range(max(1, settings.destination_retries)):
        try:
            with httpx.Client(timeout=60.0) as client:
                r = client.post(url, json=payload)
                code = r.status_code
                if 200 <= code < 300:
                    log.info("[destination] POST ok status=%s", code)
                    return code, None
                last_err = f"HTTP {code}: {r.text[:500]}"
        except Exception as e:
            last_err = str(e)
            log.warning("[destination] attempt %s failed: %s", attempt + 1, e)
        if attempt < settings.destination_retries - 1:
            time.sleep(settings.destination_retry_backoff_sec * (attempt + 1))

    log.error("[destination] all retries failed: %s", last_err)
    return None, last_err or "unknown error"
