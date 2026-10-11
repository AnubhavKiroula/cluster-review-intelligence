"use client";

// Small shared UI pieces: SYNTHETIC banner, states, CSV download, generic table.
import { useData } from "@/lib/data";

export function SyntheticBanner() {
  const { data } = useData();
  if (!data) return null;
  if (!data.meta.is_synthetic) {
    return <p className="source-caption">Source: {data.meta.source_name}</p>;
  }
  return (
    <div className="banner" role="status">
      🧪 <strong>SYNTHETIC DATA</strong> — {data.meta.source_name}. Figures below describe
      generated reviews, not real properties.
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
