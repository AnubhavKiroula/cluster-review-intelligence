"use client";

// Snapshot types + a context that fetches /data/cluster.json once and shares it.
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export interface Meta {
  is_synthetic: boolean;
  source_name: string;
  generated_at: string;
  properties: string[];
  aspects: string[];
  date_min: string;
  date_max: string;
  n_reviews: number;
}

export interface ScorecardRow {
  aspect: string;
  mean: number;
  ci_low: number | null;
  ci_high: number | null;
  n: number;
  cluster_mean: number;
  diff: number;
  flag: string;
  n_reviews: number;
  q_value: number | null;
}

export interface PriorityRow {
  aspect: string;
  gap: number;
  volume: number;
  impact_score: number;
  started: string | null;
  rationale: string;
  current_mean: number;
  reference_mean: number;
  basis: string;
  n: number;
}

export interface TrendPoint {
  month: string;
  mean: number;
  n: number;
}

export interface Changepoint {
  property_id: string;
  aspect: string;
  change_month: string;
  delta: number;
  direction: string;
  raw_delta: number;
  market_delta: number | null;
  p_value: number;
  q_value: number;
}

export interface PropertyData {
  scorecard: ScorecardRow[];
  priority_actions: PriorityRow[];
  trends: Record<string, TrendPoint[]>;
  changepoints: Changepoint[];
}

export interface ScopeRow {
  aspect: string;
  n_properties: number;
  fraction: number;
  scope: string;
  properties: string;
  pattern: string;
}

export interface DestinationRow {
  aspect: string;
  cluster_mean: number;
  n: number;
  pct_negative: number;
  scope: string;
  pattern: string;
  n_properties_reviewed: number;
}

export interface Review {
  review_id: number;
  property_id: string;
  date: string;
  platform: string;
  rating: number;
  language_hint: string;
  text: string;
}

export interface Mention {
  review_id: number;
  aspect: string;
  sentiment: number;
  sentence: string;
}

export interface Snapshot {
  meta: Meta;
  cluster_matrix: { properties: string[]; aspects: string[]; z: (number | null)[][] };
  market_scope: ScopeRow[];
  destination_summary: DestinationRow[];
  per_property: Record<string, PropertyData>;
  reviews: Review[];
  mentions: Mention[];
}

interface State {
  data: Snapshot | null;
  error: string | null;
}

// Root-relative: a relative "data/..." resolves against the current route
// (/property/ -> /property/data/...), so any page opened directly or by deep link 404s.
export const dataUrl = (file: string): string => `/data/${file}`;

const DataContext = createContext<State>({ data: null, error: null });

export function DataProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<State>({ data: null, error: null });

  useEffect(() => {
    let alive = true;
    fetch(dataUrl("cluster.synthetic.json"))
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: Snapshot) => alive && setState({ data, error: null }))
      .catch((e: unknown) =>
        alive && setState({ data: null, error: e instanceof Error ? e.message : String(e) }),
      );
    return () => {
      alive = false;
    };
  }, []);

  return <DataContext.Provider value={state}>{children}</DataContext.Provider>;
}

export function useData(): State {
  return useContext(DataContext);
}

// --- "Did my fix work?": precomputed results, loaded only by the fix-check page --------
export interface FixCheck {
  property_id: string;
  aspect: string;
  start: string;
  baseline_start: string | null;
  verdict: "improved" | "worsened" | "no detectable change" | "too early to tell" | "no data";
  basis: "market" | "own history" | null;
  effect: number | null;
  ci_low: number | null;
  ci_high: number | null;
  p_value: number | null;
  naive_delta: number | null;
  market_delta: number | null;
  before_mean: number | null;
  after_mean: number | null;
  n_before: number;
  n_after: number;
  months_before: number;
  months_after: number;
  mde: number | null;
  placebo_rank: number | null;
  n_placebo: number;
  detected_start: string | null;
  summary: string;
}

export interface FixCheckSnapshot {
  meta: { is_synthetic: boolean; source_name: string; generated_at: string; months: string[] };
  // results[property][aspect][month]
  results: Record<string, Record<string, Record<string, FixCheck>>>;
}

export function useFixChecks(): { data: FixCheckSnapshot | null; error: string | null } {
  const [state, setState] = useState<{ data: FixCheckSnapshot | null; error: string | null }>({
    data: null,
    error: null,
  });
  useEffect(() => {
    let alive = true;
    fetch(dataUrl("fixcheck.synthetic.json"))
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: FixCheckSnapshot) => alive && setState({ data, error: null }))
      .catch((e: unknown) =>
        alive && setState({ data: null, error: e instanceof Error ? e.message : String(e) }),
      );
    return () => {
      alive = false;
    };
  }, []);
  return state;
}

// --- formatting helpers -------------------------------------------------------------
export const fmtNum = (v: number | null | undefined, digits = 2): string =>
  v == null || Number.isNaN(v) ? "—" : v.toFixed(digits);

export const fmtPct = (v: number | null | undefined, digits = 0): string =>
  v == null || Number.isNaN(v) ? "—" : `${(v * 100).toFixed(digits)}%`;

export const SENTIMENT_LABELS: Record<number, string> = {
  1: "👍 positive",
  0: "😐 neutral",
  [-1]: "👎 negative",
};

export const sentimentLabel = (v: number | null | undefined): string =>
  v == null ? "— none" : SENTIMENT_LABELS[v] ?? String(v);
