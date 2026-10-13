"use client";

// Small shared UI pieces: provenance chip, source toggle, states, CSV download, table.
import { useEffect, useState } from "react";
import { useData } from "@/lib/data";
import { COLORS, WHOSE_COLORS } from "@/lib/theme";

export function PageIntro({
  eyebrow,
  icon,
  title,
  description,
  chip,
}: {
  eyebrow: string;
  icon: string;
  title: string;
  description: React.ReactNode;
  chip?: React.ReactNode; // where the page's numbers come from
}) {
  return (
    <header className="page-heading">
      <div className="page-heading-copy">
        <div className="eyebrow">
          <span aria-hidden>{icon}</span> {eyebrow}
        </div>
        <h1>{title}</h1>
        {chip}
        <p className="page-subtitle">{description}</p>
      </div>
    </header>
  );
}

export function SectionHeading({
  title,
  description,
}: {
  title: string;
  description?: React.ReactNode;
}) {
  return (
    <div className="section-heading">
      <div>
        <h2>{title}</h2>
        {description ? <p className="section-description">{description}</p> : null}
      </div>
    </div>
  );
}

/** Where a screen's numbers come from: every page shows one. */
export function SourceChip({ kind }: { kind: "real" | "simulated" | "illustrative" }) {
  const { data } = useData();
  const p = data?.meta.provenance;
  if (kind === "real") {
    if (!data || !p) return null;
    const title =
      `${p.dataset}: ${p.platform}-derived reviews (platform inferred, not stated per review). ` +
      `${p.hotels} of the town's ${p.hotels_in_town} hotels: those with at least ${p.min_reviews} ` +
      `reviews. The source has no review dates. Aggregates only: review text is never published.`;
    return (
      <span className="source-chip real" title={title}>
        {p.town} · {p.hotels} hotels · {data.meta.n_reviews.toLocaleString()} real reviews ·{" "}
        {p.platform}
      </span>
    );
  }
  if (kind === "simulated") {
    return (
      <span
        className="source-chip simulated"
        title="SYNTHETIC data. The real hill-hotel corpus we use has no review dates, so the time-series method is shown on a simulated timeline; its calibration is in docs/methodology.md section 10."
      >
        Method demo · simulated timeline
      </span>
    );
  }
  return (
    <span
      className="source-chip simulated"
      title="SYNTHETIC reviews. Real review text is never published: the real source is TripAdvisor-derived."
    >
      Illustrative examples · SYNTHETIC reviews
    </span>
  );
}

export type Source = "real" | "demo";

/** Real cluster by default; `?source=demo` opens the simulated timeline. */
export function useSource(): [Source, (s: Source) => void] {
  const [source, setSource] = useState<Source>("real");
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("source") === "demo") setSource("demo");
  }, []);
  return [source, setSource];
}

export function SourceToggle({ value, onChange }: { value: Source; onChange: (s: Source) => void }) {
  const options: [Source, string][] = [
    ["real", "Real cluster"],
    ["demo", "Method demo: simulated timeline"],
  ];
  return (
    <div className="source-toggle" role="group" aria-label="Data source">
      {options.map(([key, label]) => (
        <button
          key={key}
          type="button"
          className={value === key ? "active" : ""}
          aria-pressed={value === key}
          onClick={() => onChange(key)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

export function Loading() {
  return <div className="state">Loading data…</div>;
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="state error">
      Failed to load <code>data/cluster.synthetic.json</code>: {message}
      <br />
      Run <code>npm run export:data</code> (or <code>python scripts/export_snapshot.py</code>) to
      regenerate the snapshot.
    </div>
  );
}

/** "Is it you or the market?" verdict for one priority (priority_actions.whose_problem). */
export function WhosePill({ value }: { value: string }) {
  return (
    <span className="whose">
      <i style={{ background: WHOSE_COLORS[value] ?? COLORS.muted }} aria-hidden />
      {value}
    </span>
  );
}

export function Info({ children }: { children: React.ReactNode }) {
  return <div className="state info">{children}</div>;
}

interface Column<T> {
  key: keyof T | string;
  label: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  render?: (row: T) => any;
  align?: "left" | "right";
}

export function Table<T>({ rows, columns }: { rows: T[]; columns: Column<T>[] }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={String(c.key)} style={{ textAlign: c.align ?? "left" }}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {columns.map((c) => (
                <td key={String(c.key)} style={{ textAlign: c.align ?? "left" }}>
                  {c.render
                    ? c.render(row)
                    : String((row as Record<string, unknown>)[c.key as string] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DownloadCsv<T>({ rows, filename }: { rows: T[]; filename: string }) {
  function toCsv(): string {
    if (rows.length === 0) return "";
    const records = rows as Record<string, unknown>[];
    const headers = Object.keys(records[0]);
    const escape = (v: unknown) => {
      const s = v == null ? "" : String(v);
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    const lines = [headers.join(",")];
    for (const r of records) lines.push(headers.map((h) => escape(r[h])).join(","));
    return lines.join("\n");
  }
  function download() {
    const blob = new Blob([toCsv()], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }
  return (
    <button className="btn" onClick={download} disabled={rows.length === 0}>
      ⬇ Download CSV
    </button>
  );
}
