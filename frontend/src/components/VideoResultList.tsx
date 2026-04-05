import type { VideoPayloadItem } from "../api/types";
import { resolveThumbnailSrc } from "../lib/thumbnailUrl";

export interface RunStats {
  video: number;
  delivered: number;
}

type Props = {
  items: VideoPayloadItem[];
  payloadParseError: string | null;
  completedStats: RunStats | null;
  /** When false, still show header/warnings but hide empty "no items" if we're in loading state */
  showEmptyMessage?: boolean;
  className?: string;
};

export function VideoResultList({
  items,
  payloadParseError,
  completedStats,
  showEmptyMessage = true,
  className = "",
}: Props) {
  return (
    <div className={className}>
      <h2 className="mb-3 text-sm font-semibold text-slate-800">
        Results ({items.length} in parsed payload
        {completedStats != null
          ? ` · run reports ${completedStats.video} videos / ${completedStats.delivered} delivered`
          : ""}
        )
      </h2>
      {payloadParseError &&
        completedStats != null &&
        completedStats.video > 0 &&
        items.length === 0 && (
          <div
            className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
            role="status"
          >
            <p className="font-medium">Could not show results in the UI</p>
            <p className="mt-1 text-amber-900/90">{payloadParseError}</p>
            <p className="mt-2 text-xs text-amber-800/80">
              The run still succeeded (see counts above). Inspect the full JSON via{" "}
              <code className="rounded bg-amber-100/80 px-1">GET /runs/&lt;id&gt;</code> in{" "}
              <code className="rounded bg-amber-100/80 px-1">/docs</code>, or raise{" "}
              <code className="rounded bg-amber-100/80 px-1">PAYLOAD_PREVIEW_MAX_CHARS</code> on the
              API and run again.
            </p>
          </div>
        )}
      {items.length === 0 && !(payloadParseError && (completedStats?.video ?? 0) > 0) ? (
        showEmptyMessage ? (
          <p className="text-sm text-slate-500">No video items in this run.</p>
        ) : null
      ) : items.length > 0 ? (
        <ul className="space-y-4">
          {items.map((it, i) => (
            <li
              key={`${it.instagram_shortcode ?? i}-${i}`}
              className="flex gap-3 rounded-xl border border-slate-100 bg-slate-50/50 p-3"
            >
              {it.thumbnail_url ? (
                <img
                  src={resolveThumbnailSrc(it.thumbnail_url) ?? it.thumbnail_url}
                  alt=""
                  className="h-20 w-20 shrink-0 rounded-lg object-cover"
                />
              ) : (
                <div className="h-20 w-20 shrink-0 rounded-lg bg-slate-200" />
              )}
              <div className="min-w-0 flex-1">
                <p className="text-xs text-slate-500">
                  @{it.author_username ?? "unknown"}{" "}
                  {it.instagram_shortcode && `· ${it.instagram_shortcode}`}
                </p>
                <p className="mt-1 line-clamp-2 text-sm text-slate-800">
                  {it.caption || "(no caption)"}
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {it.permalink && (
                    <a
                      href={it.permalink}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs font-medium text-indigo-600 hover:underline"
                    >
                      Open post
                    </a>
                  )}
                  {it.video_url && (
                    <a
                      href={it.video_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs font-medium text-indigo-600 hover:underline"
                    >
                      Video
                    </a>
                  )}
                  {it.cdn_video_url && (
                    <a
                      href={it.cdn_video_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs font-medium text-slate-500 hover:underline"
                    >
                      Original CDN
                    </a>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
