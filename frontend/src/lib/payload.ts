import type { VideoPayloadItem } from "../api/types";

export function parsePayloadPreview(json: string | null): {
  items: VideoPayloadItem[];
  parseError: string | null;
} {
  if (!json?.trim()) return { items: [], parseError: null };
  try {
    const data = JSON.parse(json) as unknown;
    if (!Array.isArray(data)) {
      return { items: [], parseError: "Payload is not a JSON array." };
    }
    return { items: data as VideoPayloadItem[], parseError: null };
  } catch {
    return {
      items: [],
      parseError:
        "Could not parse payload_preview (JSON was cut off or invalid). On the API, raise PAYLOAD_PREVIEW_MAX_CHARS and re-run.",
    };
  }
}
