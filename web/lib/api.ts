"use client";

// Typed client for the Python API (cri.server). The G5 snapshot pages do not use it,
// so they keep working without the API; the travel pages and live classify do.
import { useEffect, useState } from "react";

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

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  const outer = init.signal;
  outer?.addEventListener("abort", () => ctrl.abort());
  try {
    const r = await fetch(`${API_BASE}${path}`, { ...init, signal: ctrl.signal });
    const body = await r.json().catch(() => null);
    if (!r.ok) throw new ApiError(r.status, detail(body));
    return body as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if (ctrl.signal.aborted && !outer?.aborted) throw new ApiError(0, "the API did not answer in time");
    throw new ApiError(0, e instanceof Error ? e.message : String(e));
  } finally {
    clearTimeout(timer);
  }
}

export const postApi = <T>(path: string, body: unknown) =>
  apiFetch<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export function query(params: Record<string, string | number | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") q.set(k, String(v));
  return q.toString();
}

/** GET `path` whenever it changes; `null` means "not ready, don't fetch". */
export function useApi<T>(path: string | null): { data: T | null; error: string | null; loading: boolean } {
  const [state, setState] = useState<{ data: T | null; error: string | null; loading: boolean }>({
    data: null,
    error: null,
    loading: path !== null,
  });
  useEffect(() => {
    if (path === null) return;
    const ctrl = new AbortController();
    setState((s) => ({ ...s, loading: true, error: null }));
    apiFetch<T>(path, { signal: ctrl.signal })
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((e: ApiError) => {
        if (!ctrl.signal.aborted) setState({ data: null, error: e.message, loading: false });
      });
    return () => ctrl.abort();
  }, [path]);
  return state;
}

// --- response types (mirror cri.travel / cri.server) --------------------------------------
export type Basis = "fact" | "synthetic" | "assumption" | "derived" | "measured";
export type Category = "Low" | "Moderate" | "High" | "Very High";

export interface Evidence {
  label: string;
  value: number | string;
  basis: Basis;
  detail: string;
}

export interface DemandDay {
  day: string;
  index: number;
  category: Category;
  borderline: boolean;
  factors: Evidence[];
  notes: string[];
}

export interface TripDemand {
  destination: string;
  start: string;
  nights: number;
  mean_index: number;
  category: Category;
  days: DemandDay[];
}

export interface QuieterOption {
  start: string;
  offset_days: number;
  mean_index: number;
  category: Category;
  drop: number;
  avoids: string[];
}

export interface TripDemandResponse {
  trip: TripDemand;
  drivers: [string, number][];
  quieter: QuieterOption[];
}

export interface Alternative {
  destination: string;
  name: string;
  score: number;
  similarity: number;
  mean_index: number;
  category: Category;
  components: Evidence[];
  explanation: {
    why_origin_busy: string;
    why_similar: string;
    expected_crowd: string;
    trade_off: string;
    limitations: string;
  };
}

export interface AlternativesResponse {
  origin: string;
  origin_name: string;
  start: string;
  nights: number;
  origin_demand: TripDemand;
  alternatives: Alternative[];
  excluded: [string, string][];
}

export interface DestinationMeta {
  id: string;
  name: string;
  state: string;
  district: string;
  region: string;
  elevation_m: number;
  belt: boolean;
  budget: number;
  popularity: string;
  popularity_evidence: string;
  sensitivity: string;
  landscape: string[];
  tags: string[];
}

export interface Meta {
  is_synthetic: boolean;
  source_name: string;
  destinations: DestinationMeta[];
  origins: { id: string; name: string }[];
  properties: { id: string; destination: string; kind: string }[];
  interests: string[];
  seller_categories: Record<string, string>;
  holiday_coverage: { start: string; end: string };
  holidays: { date: string; name: string; source: string; url: string; moon_dependent: boolean }[];
  assumed_windows: { name: string; start: string; end: string; note: string }[];
  ceilings: Record<string, number>;
  road_factor: number;
  emission_factors: {
    mode: string;
    value: number;
    unit: string;
    per: string;
    note: string;
    source_title: string;
    url: string;
  }[];
  sources: { key: string; title: string; url: string }[];
}

export interface Feedback {
  aspect: string;
  mean: number | null;
  ci_low: number | null;
  ci_high: number | null;
  n: number;
  cluster_mean: number | null;
  flag: "lead" | "lag" | "on_par";
}

export interface StayProfile {
  property_id: string;
  destination: string;
  destination_name: string;
  kind: string;
  price_from: number;
  price_to: number;
  price_band: string;
  rooms: { category: string; count: number; price: number }[];
  total_rooms: number;
  amenities: string[];
  practices: { practice: string; status: "reported" | "not reported" }[];
  suitability: Evidence[];
  feedback: Feedback[];
  leads: string[];
  lags: string[];
  consistency: Evidence;
  note: string;
}

export interface Insight {
  kind: string;
  priority: "high" | "medium" | "low";
  title: string;
  why: string;
  evidence: Evidence[];
  period: string | null;
}

export interface ProviderResponse {
  profile: StayProfile;
  insights: Insight[];
}

export interface Seller {
  id: string;
  name: string;
  destination: string;
  category: string;
  offering: string;
  price: string;
  verification: string;
}

export interface Opportunity {
  category: string;
  label: string;
  score: number;
  sellers_listed: number;
  under_served: boolean;
  evidence: Evidence;
}

export interface PressureRow {
  destination: string;
  name: string;
  region: string;
  state: string;
  mean_index: number;
  peak_day: string;
  peak_index: number;
  peak_category: Category;
  days_by_category: Record<Category, number>;
  sensitivity: string;
  ceiling: Evidence;
  days_at_or_over_ceiling: number;
  peaks: { start: string; end: string; days: number; max_index: number; drivers: string[] }[];
  redistribution: {
    date: string;
    alternatives: { destination: string; name: string; mean_index: number }[];
  } | null;
  profiled_rooms: number;
  sellers_listed: number;
  official_arrivals: { year: number; total: number; source: string; note: string } | null;
}

export interface RegionResponse {
  start: string;
  days: number;
  pressure: PressureRow[];
  under_served_categories: {
    destination: string;
    name: string;
    category: string;
    score: number;
    sellers_listed: number;
  }[];
  review_issues: {
    aspect: string;
    cluster_mean: number | null;
    n: number;
    pct_negative: number | null;
    scope: string;
    pattern: string | null;
    n_properties_reviewed: number;
  }[];
  notes: string[];
}

export interface PlanRequest {
  origin: string;
  destination: string;
  start: string;
  nights: number;
  travellers: number;
  budget: number;
  interests: string[];
  stay_pref: "any" | "budget" | "standard" | "family";
  transport: "car" | "bus";
  sustainability: boolean;
}

export interface Variant {
  label: string;
  how: string;
  destination: string;
  destination_name: string;
  start: string;
  transport: string;
  total: number;
  per_person: number;
  delta_cost: number;
  mean_index: number;
  category: Category;
  delta_index: number;
}

export interface TripPlan {
  request: PlanRequest;
  destination_name: string;
  end: string;
  demand: { mean_index: number; category: Category; drivers: [string, number][] };
  stay: {
    property_id: string;
    kind: string;
    category: string;
    rooms: number;
    price_per_night: number;
  } | null;
  itinerary: { day: string; items: string[]; demand: Category | null }[];
  costs: Evidence[];
  total: number;
  per_person: number;
  within_budget: boolean;
  carbon: Evidence[];
  sellers: Seller[];
  variants: Variant[];
  notes: string[];
}

export interface ClassifyResponse {
  backend: string;
  mentions: { aspect: string; sentiment: number; sentence: string }[];
}

// --- small helpers ---------------------------------------------------------------------
export const inr = (v: number) =>
  `${v < 0 ? "−" : ""}₹${Math.abs(Math.round(v)).toLocaleString("en-IN")}`;
export const signedInr = (v: number) => (v > 0 ? `+${inr(v)}` : inr(v));

export function isoDate(d: Date): string {
  const z = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
}

export function addDays(iso: string, n: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  return isoDate(new Date(y, m - 1, d + n));
}

export function fmtDay(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-IN", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}
