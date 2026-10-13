"use client";

// Small shared UI pieces: page header, SYNTHETIC banner, states, change split, CSV
// download, generic table.
import { fmtNum, useData } from "@/lib/data";
import { useCountUp, useGrowBars } from "@/lib/motion";
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

/**
 * The labelled rule that separates a page's verdict from the evidence for it. It is
 * decoration only in the sense that a signpost is: it tells the reader that what
 * follows is the working, not the answer, so its words are read out like any others.
 *
 * `heading` makes it the real <h2> for the section it introduces, which is right when
 * the rule is that section's only title; the pages that follow it with their own
 * headings leave it as a paragraph.
 */
export function ZoneRule({
  label,
  id,
  heading = false,
}: {
  label: string;
  id?: string;
  heading?: boolean;
}) {
  const Tag = heading ? "h2" : "p";
  return (
    <Tag id={id} className="zone-rule">
      {label}
    </Tag>
  );
}

// Not rendered at the moment: the team hid it from the site for now (see
// docs/TODO_RESULTS.md). To restore it, render <SyntheticBanner /> above <Header />
// in app/layout.tsx; it then appears on every page (CLAUDE.md rule 2).
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

/**
 * Holds the shape of the page that is coming. The snapshot is a single JSON file of a
 * few megabytes, so on a hill-town connection this is on screen for a while; a one-line
 * "Loading…" that is then replaced by a full page moves everything under it.
 *
 * Only the screen-reader text announces the wait. The grey blocks are decoration for
 * that announcement and are hidden from assistive technology.
 */
export function Loading({ what = "the cluster snapshot" }: { what?: string }) {
  return (
    <div className="skeleton" role="status" aria-live="polite" aria-busy="true">
      <span className="visually-hidden">Loading {what}…</span>
      <div className="skel-lines" aria-hidden>
        <div className="skel-bar" style={{ height: 42, maxWidth: "min(100%, 24ch)" }} />
        <div className="skel-bar" style={{ height: "1.1em", maxWidth: "min(100%, 56ch)" }} />
      </div>
      <div className="skel-panel" aria-hidden style={{ height: 200 }} />
      <div className="skel-panel" aria-hidden style={{ height: 320 }} />
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

/**
 * A quantity that counts up to its value the first time it is seen, and counts from the
 * old value to the new one when the reader changes the question. The rendered text is
 * always the final, correct string, so a reader with reduced motion, without JavaScript
 * or with a failed GSAP chunk sees the number and nothing else.
 */
export function Counter({
  value,
  format,
}: {
  value: number | null | undefined;
  /** Must produce the final text as well as every frame of the count. */
  format: (v: number) => string;
}) {
  const ref = useCountUp(value, format);
  return <span ref={ref}>{value == null ? "—" : format(value)}</span>;
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
 *
 * The bars also grow out of that zero line on arrival, and again whenever the numbers
 * change, because the figure is an argument in three steps and the growth is what makes
 * it read in that order. Widths are rendered as final values, so the animation is an
 * enhancement and never the source of the figure.
 */
export function ChangeSplit({
  rows,
  caption,
  delay = 0,
}: {
  rows: SplitRow[];
  caption?: React.ReactNode;
  /** Seconds to wait before the bars grow, so the home figure can run the line
   * drawing and this figure as one sequence instead of two at once. */
  delay?: number;
}) {
  const scale = Math.max(0.5, ...rows.map((r) => Math.abs(r.value ?? 0)));
  // Replays when the property, aspect or month behind the figure changes.
  const signature = rows.map((r) => `${r.label}:${r.value}`).join("|");
  const ref = useGrowBars(signature, delay);
  return (
    <figure className="split">
      <div className="split-rows" ref={ref}>
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
                    data-bar
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

/**
 * Marks every occurrence of `query` in `text`. The explorer searches 5,124 reviews and
 * then shows the clause it matched in; without this the reader has to find the phrase
 * themselves. Matching is literal and case-insensitive, the same comparison the filter
 * itself uses.
 */
export function Highlight({ text, query }: { text: string; query: string }) {
  const needle = query.trim().toLowerCase();
  if (!needle || !text) return <>{text}</>;
  const parts: React.ReactNode[] = [];
  const hay = text.toLowerCase();
  let at = 0;
  for (let i = hay.indexOf(needle); i !== -1; i = hay.indexOf(needle, at)) {
    if (i > at) parts.push(text.slice(at, i));
    parts.push(
      <mark className="hit" key={i}>
        {text.slice(i, i + needle.length)}
      </mark>,
    );
    at = i + needle.length;
  }
  if (at === 0) return <>{text}</>;
  if (at < text.length) parts.push(text.slice(at));
  return <>{parts}</>;
}

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
  tall,
}: {
  rows: T[];
  columns: Column<T>[];
  caption?: string;
  /** Caps the height and scrolls inside, which is what makes the sticky column names
   * useful. For the hundred-row result tables, not for short ones. */
  tall?: boolean;
}) {
  return (
    <div
      className={tall ? "table-wrap tall" : "table-wrap"}
      tabIndex={0}
      role="region"
      aria-label={caption ?? "Table"}
    >
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
