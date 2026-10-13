"use client";

// Small shared UI pieces: page header, SYNTHETIC banner, states, change split, CSV
// download, generic table.
import { fmtNum, useData } from "@/lib/data";
import { WHOSE_VARS } from "@/lib/theme";

export function PageHeader({
  title,
  lede,
  children,
}: {
  title: React.ReactNode;
  lede: React.ReactNode;
  children?: React.ReactNode;
}) {
  return (
    <header className="page-header">
      <h1>{title}</h1>
      <p className="lede">{lede}</p>
      {children}
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
      <h2>{title}</h2>
      {description ? <p>{description}</p> : null}
    </div>
  );
}

// Rendered once, by the root layout, so every page carries it (CLAUDE.md rule 2).
export function SyntheticBanner() {
  const { data } = useData();
  if (!data) return null;
  if (!data.meta.is_synthetic) {
    return <p className="source-strip">Source: {data.meta.source_name}</p>;
  }
  return (
    <div className="synthetic-strip" role="note">
      <strong>SYNTHETIC DATA</strong>
      <span>
        {data.meta.source_name}. Every figure describes generated reviews, not real properties.
      </span>
    </div>
  );
}

export function Loading({ what = "the cluster snapshot" }: { what?: string }) {
  return (
    <div className="state" role="status" aria-live="polite">
      Loading {what}…
    </div>
  );
}

export function ErrorState({ message, file = "cluster.synthetic.json" }: { message: string; file?: string }) {
  return (
    <div className="state error" role="alert">
      <p>
        <strong>Could not load</strong> <code>data/{file}</code> ({message}).
      </p>
      <p>
        Regenerate the snapshots with <code>python web/scripts/export_snapshot.py</code>, then
        rebuild.
      </p>
    </div>
  );
}

/** "Is it you or the market?" verdict for one priority (priority_actions.whose_problem). */
export function WhosePill({ value }: { value: string }) {
  return (
    <span className="whose" style={{ "--tone": WHOSE_VARS[value] ?? "var(--stone)" } as React.CSSProperties}>
      {value}
    </span>
  );
}

export function SentimentTag({ value }: { value: number | null | undefined }) {
  if (value == null) return <span className="sentiment none">none</span>;
  const name = value > 0 ? "positive" : value < 0 ? "negative" : "neutral";
  return <span className={`sentiment ${name}`}>{name}</span>;
}

export function Info({ children }: { children: React.ReactNode }) {
  return <div className="state info">{children}</div>;
}

export interface SplitRow {
  label: string;
  note: string;
  value: number | null;
  /** The row the reader should act on: drawn in the verdict colour. */
  verdict?: boolean;
}

/**
 * The product's core idea in one figure: what your reviews did, split into what the
 * whole market did over the same months and what is left over for you alone.
 * Bars grow left (worse) or right (better) from a shared zero.
 */
export function ChangeSplit({ rows, caption }: { rows: SplitRow[]; caption?: React.ReactNode }) {
  const scale = Math.max(0.5, ...rows.map((r) => Math.abs(r.value ?? 0)));
  return (
    <figure className="split">
      <div className="split-rows">
        {rows.map((r) => {
          const v = r.value ?? 0;
          const width = `${(Math.abs(v) / scale) * 50}%`;
          const tone = r.value == null ? "none" : v < 0 ? "down" : v > 0 ? "up" : "flat";
          return (
            <div key={r.label} className={r.verdict ? "split-row is-verdict" : "split-row"}>
              <div className="split-label">
                <span>{r.label}</span>
                <small>{r.note}</small>
              </div>
              <div className="split-track" aria-hidden>
                <span className="split-zero" />
                {r.value != null && (
                  <span
                    className={`split-bar ${tone}`}
                    style={v < 0 ? { right: "50%", width } : { left: "50%", width }}
                  />
                )}
              </div>
              <div className={`split-value ${tone}`}>{signed(r.value)}</div>
            </div>
          );
        })}
      </div>
      {caption ? <figcaption>{caption}</figcaption> : null}
    </figure>
  );
}

export const signed = (v: number | null | undefined): string =>
  v == null ? "—" : `${v > 0 ? "+" : v < 0 ? "−" : ""}${fmtNum(Math.abs(v))}`;

interface Column<T> {
  key: keyof T | string;
  label: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  render?: (row: T) => any;
  align?: "left" | "right";
  /** Wide free-text columns get a minimum width so they wrap instead of squeezing. */
  wide?: boolean;
}

export function Table<T>({
  rows,
  columns,
  caption,
}: {
  rows: T[];
  columns: Column<T>[];
  caption?: string;
}) {
  return (
    <div className="table-wrap" tabIndex={0} role="region" aria-label={caption ?? "Table"}>
      <table className="data-table">
        {caption ? <caption className="visually-hidden">{caption}</caption> : null}
        <thead>
          <tr>
            {columns.map((c) => (
              <th
                key={String(c.key)}
                scope="col"
                className={[c.align === "right" ? "num" : "", c.wide ? "wide" : ""].join(" ").trim() || undefined}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {columns.map((c) => (
                <td
                  key={String(c.key)}
                  className={[c.align === "right" ? "num" : "", c.wide ? "wide" : ""].join(" ").trim() || undefined}
                >
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

/** The data behind a chart, as a table: exact values for owners, and a text
 * alternative for screen-reader users (Plotly's SVG is not accessible). */
export function ChartNumbers<T>({
  rows,
  columns,
  caption,
}: {
  rows: T[];
  columns: Column<T>[];
  caption: string;
}) {
  return (
    <details className="chart-numbers">
      <summary>Show the numbers</summary>
      <Table rows={rows} columns={columns} caption={caption} />
    </details>
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
    <button type="button" className="btn btn-quiet" onClick={download} disabled={rows.length === 0}>
      Download CSV
    </button>
  );
}
