"use client";

// Shared pieces for the API-backed travel pages: honesty banner, API error state,
// crowd-category pill, provenance tags and factor/evidence tables.
import { API_BASE, type Basis, type Category, type Evidence } from "@/lib/api";
import s from "./travel.module.css";

export function ApiStatusBanner() {
  return (
    <div className="banner" role="status">
      <span className="banner-icon" aria-hidden>
        ✦
      </span>
      <span>
        <strong>PROTOTYPE ESTIMATES</strong> · SYNTHETIC profiles, prices and sellers; holidays,
        distances and emission factors are sourced facts. Demand is an indicative estimate of
        visitor pressure, <strong>not live traffic</strong> or bookings.
      </span>
    </div>
  );
}

export function ApiErrorState({ error }: { error: string }) {
  return (
    <div className="state error">
      Could not reach the API at <code>{API_BASE}</code>: {error}
      <br />
      Start it with <code>pip install -e &quot;.[api]&quot;</code> then{" "}
      <code>uvicorn cri.server:app --port 8000</code> (see README).
    </div>
  );
}

export function CategoryPill({ category, index }: { category: Category; index?: number }) {
  return (
    <span className={`${s.pill} ${s[category.replace(" ", "")]}`}>
      {category}
      {index !== undefined ? ` · ${Math.round(index)}` : ""}
    </span>
  );
}

const BASIS_HELP: Record<Basis, string> = {
  fact: "From a cited official or open source",
  measured: "Computed from the (SYNTHETIC) review data",
  derived: "Calculated from other shown values",
  synthetic: "Illustrative SYNTHETIC value",
  assumption: "An assumption, stated openly",
};

export function BasisTag({ basis }: { basis: Basis }) {
  return (
    <span className={`${s.basis} ${s[basis]}`} title={BASIS_HELP[basis]}>
      {basis}
    </span>
  );
}

/** Points table: every factor of a demand index, so the total is auditable. */
export function FactorTable({ factors, unit = "pts" }: { factors: Evidence[]; unit?: string }) {
  return (
    <table className={s.factors}>
      <tbody>
        {factors.map((f, i) => (
          <tr key={i}>
            <td>
              {f.label} <BasisTag basis={f.basis} />
              {f.detail ? <div className={s.detail}>{f.detail}</div> : null}
            </td>
            <td>
              {typeof f.value === "number" && f.value > 0 ? "+" : ""}
              {f.value} {typeof f.value === "number" ? unit : ""}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function EvidenceList({ items }: { items: Evidence[] }) {
  return (
    <ul className={s.list}>
      {items.map((e, i) => (
        <li key={i}>
          <strong>{e.label}:</strong> {String(e.value)} <BasisTag basis={e.basis} />
          {e.detail ? <span className={s.muted}> · {e.detail}</span> : null}
        </li>
      ))}
    </ul>
  );
}

export { s as travelStyles };
