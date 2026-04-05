/**
 * Instagram CDN thumbnails often fail in <img> from localhost (hotlink / Referer rules).
 * When VITE_API_BASE_URL is set, route those through GET /proxy/cdn-image on the API.
 */
function isAllowlistedCdnHost(hostname: string): boolean {
  const h = hostname.toLowerCase();
  if (h === "cdninstagram.com" || h.endsWith(".cdninstagram.com")) return true;
  if (h === "fbcdn.net" || h.endsWith(".fbcdn.net")) return true;
  if (h === "instagram.com" || h.endsWith(".instagram.com")) return true;
  return false;
}

export function resolveThumbnailSrc(url: string | null | undefined): string | undefined {
  const u = url?.trim();
  if (!u) return undefined;

  const apiBase = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
  if (!apiBase) return u;

  try {
    const { hostname } = new URL(u);
    if (!isAllowlistedCdnHost(hostname)) return u;
  } catch {
    return u;
  }

  return `${apiBase}/proxy/cdn-image?url=${encodeURIComponent(u)}`;
}
