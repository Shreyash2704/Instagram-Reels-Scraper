import type {
  RunCreateResponse,
  RunRead,
  RunReadList,
  SourceRead,
  SourceReadList,
  SourceType,
} from "./types";

function getBase(): string {
  const b = import.meta.env.VITE_API_BASE_URL ?? "";
  return b.replace(/\/$/, "");
}

async function parseJson<T>(res: Response): Promise<T> {
  const text = await res.text();
  if (!res.ok) {
    let detail = text;
    try {
      const j = JSON.parse(text) as { detail?: string | unknown };
      if (typeof j?.detail === "string") detail = j.detail;
      else if (Array.isArray(j?.detail)) detail = JSON.stringify(j.detail);
    } catch {
      /* use raw text */
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  if (!text) return {} as T;
  return JSON.parse(text) as T;
}

export async function createSource(body: {
  type: SourceType;
  value: string;
}): Promise<SourceRead> {
  const res = await fetch(`${getBase()}/sources`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseJson<SourceRead>(res);
}

export async function startRun(sourceId: number): Promise<RunCreateResponse> {
  const res = await fetch(`${getBase()}/sources/${sourceId}/run`, {
    method: "POST",
  });
  return parseJson<RunCreateResponse>(res);
}

export async function getRun(runId: number): Promise<RunRead> {
  const res = await fetch(`${getBase()}/runs/${runId}`);
  return parseJson<RunRead>(res);
}

export async function listSources(): Promise<SourceReadList> {
  const res = await fetch(`${getBase()}/sources`);
  return parseJson<SourceReadList>(res);
}

export async function listRuns(sourceId?: number): Promise<RunReadList> {
  const q =
    sourceId != null && Number.isFinite(sourceId)
      ? `?source_id=${encodeURIComponent(String(sourceId))}`
      : "";
  const res = await fetch(`${getBase()}/runs${q}`);
  return parseJson<RunReadList>(res);
}
