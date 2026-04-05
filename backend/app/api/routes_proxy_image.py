"""Proxy allowlisted Meta/Instagram CDN images for UI thumbnails.

Browsers often get blocked loading scontent-* URLs in <img> (referrer / hotlink rules).
Server-side fetch with an instagram.com Referer usually succeeds.
"""

from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

router = APIRouter(prefix="/proxy", tags=["proxy"])

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _cdn_host_allowed(host: str) -> bool:
    h = host.lower().split(":")[0]
    if h == "cdninstagram.com" or h.endswith(".cdninstagram.com"):
        return True
    if h == "fbcdn.net" or h.endswith(".fbcdn.net"):
        return True
    if h == "instagram.com" or h.endswith(".instagram.com"):
        return True
    return False


@router.get("/cdn-image")
async def proxy_cdn_image(
    url: str = Query(
        ...,
        max_length=16_384,
        description="Image URL; host must be *.cdninstagram.com, *.fbcdn.net, or *.instagram.com",
    ),
) -> Response:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(400, "only http(s) URLs are allowed")
    if not parsed.netloc or not _cdn_host_allowed(parsed.netloc):
        raise HTTPException(400, "URL host is not allowlisted for proxy")

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            r = await client.get(
                url,
                headers={
                    "User-Agent": _UA,
                    "Referer": "https://www.instagram.com/",
                    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                },
            )
    except httpx.RequestError as e:
        raise HTTPException(502, f"upstream fetch failed: {e!s}") from e

    if r.status_code >= 400:
        raise HTTPException(502, f"upstream returned HTTP {r.status_code}")

    ct = (r.headers.get("content-type") or "").split(";")[0].strip() or "application/octet-stream"
    if not ct.startswith("image/"):
        raise HTTPException(502, "upstream response is not an image")

    return Response(
        content=r.content,
        media_type=ct,
        headers={"Cache-Control": "public, max-age=86400"},
    )
