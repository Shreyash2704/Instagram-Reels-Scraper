import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "../api/client";
import { VideoResultList } from "../components/VideoResultList";
import { parsePayloadPreview } from "../lib/payload";
import type { SourceType, VideoPayloadItem } from "../api/types";

type TabId = "post" | "profile" | "mentions" | "hashtag";

const TAB_CONFIG: {
  id: TabId;
  label: string;
  sourceType: SourceType;
  placeholder: string;
  inputType: "url" | "text";
}[] = [
  {
    id: "post",
    label: "Post",
    sourceType: "post_url",
    placeholder: "https://www.instagram.com/...",
    inputType: "url",
  },
  {
    id: "profile",
    label: "Profile",
    sourceType: "profile",
    placeholder: "@ profile",
    inputType: "text",
  },
  {
    id: "mentions",
    label: "@ Profile mentions",
    sourceType: "profile_tagged",
    placeholder: "@ profile",
    inputType: "text",
  },
  {
    id: "hashtag",
    label: "# Hashtag",
    sourceType: "hashtag",
    placeholder: "# hashtag",
    inputType: "text",
  },
];

export function FindMediaPage() {
  const [activeTab, setActiveTab] = useState<TabId>("post");
  const [value, setValue] = useState("");
  const [consent, setConsent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<VideoPayloadItem[] | null>(null);
  const [payloadParseError, setPayloadParseError] = useState<string | null>(null);
  const [completedStats, setCompletedStats] = useState<{
    video: number;
    delivered: number;
  } | null>(null);
  const [runStatus, setRunStatus] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const activeRef = useRef(true);

  useEffect(() => {
    activeRef.current = true;
    return () => {
      activeRef.current = false;
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, []);

  const stopPoll = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const tab = TAB_CONFIG.find((t) => t.id === activeTab) ?? TAB_CONFIG[0];

  const handleFind = async () => {
    setError(null);
    setItems(null);
    setPayloadParseError(null);
    setCompletedStats(null);
    setRunStatus(null);
    stopPoll();

    const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
    if (!baseUrl) {
      setError("Set VITE_API_BASE_URL in frontend/.env (e.g. http://127.0.0.1:8000)");
      return;
    }

    if (!consent) return;
    const v = value.trim();
    if (!v) {
      setError("Enter a URL, username, or hashtag.");
      return;
    }

    setLoading(true);
    const doneRef = { current: false };
    try {
      const source = await api.createSource({ type: tab.sourceType, value: v });
      const { run_id } = await api.startRun(source.id);
      setRunStatus("pending");

      const tick = async () => {
        if (doneRef.current || !activeRef.current) return;
        try {
          const run = await api.getRun(run_id);
          setRunStatus(run.status);
          if (run.status === "completed") {
            doneRef.current = true;
            stopPoll();
            const parsed = parsePayloadPreview(run.payload_preview);
            setItems(parsed.items);
            setPayloadParseError(parsed.parseError);
            setCompletedStats({
              video: run.video_count,
              delivered: run.delivered_count,
            });
            setLoading(false);
          } else if (run.status === "failed") {
            doneRef.current = true;
            stopPoll();
            setError(run.error_message || "Run failed.");
            setLoading(false);
          }
        } catch (e) {
          doneRef.current = true;
          stopPoll();
          setError(e instanceof Error ? e.message : "Poll failed");
          setLoading(false);
        }
      };

      await tick();
      if (!doneRef.current && activeRef.current) {
        pollRef.current = setInterval(() => {
          void tick();
        }, 2000);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
      setLoading(false);
    }
  };

  const canSubmit = consent && value.trim().length > 0 && !loading;

  return (
    <div className="bg-slate-100 px-4 py-10 text-slate-900">
      <div className="mx-auto max-w-xl">
        <h1 className="mb-2 text-center text-2xl font-semibold tracking-tight text-slate-800">
          Find Instagram media
        </h1>
        <p className="mb-8 text-center text-sm text-slate-500">
          Public content only. Results depend on Apify and Instagram availability.
        </p>

        <div className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm">
          <p className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-400">
            Find by
          </p>
          <div
            className="mb-5 flex flex-wrap gap-1 rounded-xl bg-slate-100 p-1"
            role="tablist"
            aria-label="Search type"
          >
            {TAB_CONFIG.map((t) => (
              <button
                key={t.id}
                type="button"
                role="tab"
                aria-selected={activeTab === t.id}
                className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 ${
                  activeTab === t.id
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-600 hover:text-slate-900"
                }`}
                onClick={() => {
                  setActiveTab(t.id);
                  setValue("");
                  setError(null);
                  setItems(null);
                  setPayloadParseError(null);
                  setCompletedStats(null);
                }}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div className="flex gap-2">
            <input
              type={tab.inputType}
              name="query"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder={tab.placeholder}
              className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-400/30"
              disabled={loading}
              autoComplete="off"
            />
            <button
              type="button"
              disabled={!canSubmit}
              onClick={() => void handleFind()}
              className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-slate-800 px-4 py-3 text-sm font-medium text-white shadow-sm transition-colors hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
            >
              <svg
                className="h-4 w-4 opacity-80"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              Find media
            </button>
          </div>

          <label className="mt-5 flex cursor-pointer items-start gap-3 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              disabled={loading}
            />
            <span>
              I confirm that I have obtained the necessary permissions, copyrights, and
              authorizations.
            </span>
          </label>

          {runStatus && loading && (
            <p className="mt-4 text-center text-sm text-indigo-600">
              Status: {runStatus}…
            </p>
          )}

          {error && (
            <div
              className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
              role="alert"
            >
              {error}
            </div>
          )}

          {items !== null && !loading && (
            <div className="mt-6 border-t border-slate-100 pt-6">
              <VideoResultList
                items={items}
                payloadParseError={payloadParseError}
                completedStats={completedStats}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
