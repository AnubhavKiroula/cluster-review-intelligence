// Client for the Python API (cri.server). Only the explorer's live classification
// uses it; every other page reads the static snapshot, so the site works without it.

// Baked in at build time (static export): rebuild after changing it.
export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(
  /\/+$/,
  "",
);
const TIMEOUT_MS = 15000;

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

function detail(body: unknown): string {
  const d = (body as { detail?: unknown })?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d))
    return d.map((e: { loc?: unknown[]; msg?: string }) => `${e.loc?.slice(-1)}: ${e.msg}`).join("; ");
  return "request failed";
}

export async function postApi<T>(path: string, body: unknown): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const r = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: ctrl.signal,
    });
    const json = await r.json().catch(() => null);
    if (!r.ok) throw new ApiError(r.status, detail(json));
    return json as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if (ctrl.signal.aborted) throw new ApiError(0, "the API did not answer in time");
    throw new ApiError(0, e instanceof Error ? e.message : String(e));
  } finally {
    clearTimeout(timer);
  }
}

export interface ClassifyResponse {
  backend: string;
  mentions: { aspect: string; sentiment: number; sentence: string }[];
}
