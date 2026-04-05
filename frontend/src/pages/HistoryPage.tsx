import { useCallback, useEffect, useState } from "react";
import * as api from "../api/client";
import type { RunRead, SourceRead } from "../api/types";
import { VideoResultList } from "../components/VideoResultList";
import { parsePayloadPreview } from "../lib/payload";

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export function HistoryPage() {
  const [sources, setSources] = useState<SourceRead[]>([]);
  const [runs, setRuns] = useState<RunRead[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<number | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

  const loadSources = useCallback(async () => {
    if (!baseUrl) return;
    const { items } = await api.listSources();
    setSources(items);
  }, [baseUrl]);

  const loadRunsForSource = useCallback(
    async (sourceId: number) => {
      if (!baseUrl) return;
      const { items } = await api.listRuns(sourceId);
      setRuns(items);
    },
    [baseUrl],
  );

  const refresh = useCallback(async () => {
    setError(null);
    if (!baseUrl) {
      setError("Set VITE_API_BASE_URL in frontend/.env (e.g. http://127.0.0.1:8000)");
      return;
    }
    setLoading(true);
    try {
      await loadSources();
      if (selectedSourceId != null) {
        await loadRunsForSource(selectedSourceId);
      } else {
        setRuns([]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load history");
    } finally {
      setLoading(false);
    }
  }, [baseUrl, loadSources, loadRunsForSource, selectedSourceId]);

  useEffect(() => {
    if (!baseUrl) {
      setError("Set VITE_API_BASE_URL in frontend/.env (e.g. http://127.0.0.1:8000)");
      return;
    }
    setLoading(true);
    setError(null);
    void loadSources()
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load sources"))
      .finally(() => setLoading(false));
  }, [baseUrl, loadSources]);

  useEffect(() => {
    if (selectedSourceId == null) {
      setRuns([]);
      setSelectedRunId(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      setError(null);
      try {
        const { items } = await api.listRuns(selectedSourceId);
        if (!cancelled) {
          setRuns(items);
          setSelectedRunId(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load runs");
          setRuns([]);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedSourceId]);

  const selectedRun = runs.find((r) => r.id === selectedRunId) ?? null;
  const parsed =
    selectedRun?.status === "completed"
      ? parsePayloadPreview(selectedRun.payload_preview)
      : null;

  return (
    <div className="bg-slate-100 px-4 py-10 text-slate-900">
      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-800">History</h1>
            <p className="mt-1 text-sm text-slate-500">
              Browse sources, their runs, and saved payload previews.
            </p>
          </div>
          <button
            type="button"
            disabled={loading}
            onClick={() => void refresh()}
            className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-800 shadow-sm transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
          >
            Refresh
          </button>
        </div>

        {error && (
          <div
            className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
            role="alert"
          >
            {error}
          </div>
        )}

        <div className="grid gap-4 lg:grid-cols-3">
          <section className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm">
            <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-400">
              Sources
            </h2>
            {sources.length === 0 && !loading ? (
              <p className="text-sm text-slate-500">No sources yet. Use Find media to add one.</p>
            ) : (
              <ul className="max-h-[min(24rem,50vh)] space-y-1 overflow-y-auto lg:max-h-[70vh]">
                {sources.map((s) => (
                  <li key={s.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedSourceId(s.id)}
                      className={`w-full rounded-xl px-3 py-2.5 text-left text-sm transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${
                        selectedSourceId === s.id
                          ? "bg-indigo-50 text-indigo-950 ring-1 ring-indigo-200"
                          : "text-slate-800 hover:bg-slate-50"
                      }`}
                    >
                      <span className="font-mono text-xs text-slate-500">#{s.id}</span>{" "}
                      <span className="font-medium">{s.type}</span>
                      <span className="mt-0.5 block truncate text-slate-600">{s.value}</span>
                      {s.created_at && (
                        <span className="mt-1 block text-xs text-slate-400">
                          Added {formatWhen(s.created_at)}
                        </span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h2 className="text-xs font-medium uppercase tracking-wide text-slate-400">Runs</h2>
              <span
                className="text-xs text-slate-400"
                title="The API returns at most 200 runs per request (newest first)."
              >
                ≤200 runs
              </span>
            </div>
            {selectedSourceId == null ? (
              <p className="text-sm text-slate-500">Select a source to see its runs.</p>
            ) : runs.length === 0 && !loading ? (
              <p className="text-sm text-slate-500">No runs for this source yet.</p>
            ) : (
              <ul className="max-h-[min(24rem,50vh)] space-y-1 overflow-y-auto lg:max-h-[70vh]">
                {runs.map((r) => (
                  <li key={r.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedRunId(r.id)}
                      className={`w-full rounded-xl px-3 py-2.5 text-left text-sm transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${
                        selectedRunId === r.id
                          ? "bg-indigo-50 text-indigo-950 ring-1 ring-indigo-200"
                          : "text-slate-800 hover:bg-slate-50"
                      }`}
                    >
                      <span className="font-mono text-xs text-slate-500">#{r.id}</span>{" "}
                      <span
                        className={`font-medium ${
                          r.status === "completed"
                            ? "text-emerald-700"
                            : r.status === "failed"
                              ? "text-red-700"
                              : "text-amber-700"
                        }`}
                      >
                        {r.status}
                      </span>
                      <span className="mt-0.5 block text-xs text-slate-500">
                        videos {r.video_count} · delivered {r.delivered_count}
                      </span>
                      {r.finished_at && (
                        <span className="mt-1 block text-xs text-slate-400">
                          {formatWhen(r.finished_at)}
                        </span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm lg:min-h-[12rem]">
            <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-400">
              Posts
            </h2>
            {selectedRunId == null || selectedRun == null ? (
              <p className="text-sm text-slate-500">Select a run to view its payload preview.</p>
            ) : selectedRun.status !== "completed" ? (
              <div className="rounded-xl border border-slate-100 bg-slate-50/80 p-4 text-sm text-slate-700">
                <p>
                  <span className="font-medium text-slate-800">Status:</span> {selectedRun.status}
                </p>
                {selectedRun.error_message && (
                  <p className="mt-2 text-red-800">{selectedRun.error_message}</p>
                )}
                {!selectedRun.error_message && selectedRun.status === "running" && (
                  <p className="mt-2 text-slate-500">Run in progress; refresh runs when it finishes.</p>
                )}
              </div>
            ) : parsed != null ? (
              <div className="max-h-[min(32rem,60vh)] overflow-y-auto lg:max-h-[70vh]">
                <VideoResultList
                  items={parsed.items}
                  payloadParseError={parsed.parseError}
                  completedStats={{
                    video: selectedRun.video_count,
                    delivered: selectedRun.delivered_count,
                  }}
                />
              </div>
            ) : null}
          </section>
        </div>
      </div>
    </div>
  );
}
