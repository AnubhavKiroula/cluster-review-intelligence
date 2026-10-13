"use client";

import { useEffect, useState } from "react";
import {
  fmtDay,
  inr,
  isoDate,
  postApi,
  signedInr,
  useApi,
  type ApiError,
  type Meta,
  type PlanRequest,
  type TripPlan,
} from "@/lib/api";
import { DownloadCsv, Info, Loading, PageIntro, SectionHeading } from "@/components/ui";
import {
  ApiErrorState,
  ApiStatusBanner,
  BasisTag,
  CategoryPill,
  travelStyles as s,
} from "@/components/travel";

const DEFAULT: PlanRequest = {
  origin: "delhi",
  destination: "mussoorie",
  start: isoDate(new Date()),
  nights: 2,
  travellers: 2,
  budget: 15000,
  interests: [],
  stay_pref: "any",
  transport: "bus",
  sustainability: false,
};

export default function PlanPage() {
  const meta = useApi<Meta>("/meta");
  const [form, setForm] = useState<PlanRequest>(DEFAULT);
  const [plan, setPlan] = useState<TripPlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Prefill from /explore: /plan/?destination=…&start=…&nights=…&origin=…
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    setForm((f) => ({
      ...f,
      destination: q.get("destination") ?? f.destination,
      start: q.get("start") ?? f.start,
      nights: Number(q.get("nights")) || f.nights,
      origin: q.get("origin") ?? f.origin,
    }));
  }, []);

  async function submit(req: PlanRequest) {
    setBusy(true);
    setError(null);
    try {
      setPlan(await postApi<TripPlan>("/plan", req));
    } catch (e) {
      setError((e as ApiError).message);
      setPlan(null);
    } finally {
      setBusy(false);
    }
  }

  const set = <K extends keyof PlanRequest>(k: K, v: PlanRequest[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  if (meta.error) return <ApiErrorState error={meta.error} />;
  if (!meta.data) return <Loading />;
  const m = meta.data;

  return (
    <>
      <PageIntro
        eyebrow="Traveller · affordable and sustainable"
        icon="🗺️"
        title="Plan a hill trip on a budget"
        description="An itinerary with every rupee and kilogram of CO₂ traced to its formula, local sellers along the way, and cheaper or quieter variants."
      />
      <ApiStatusBanner />

      <form
        className={s.form}
        onSubmit={(e) => {
          e.preventDefault();
          submit(form);
        }}
      >
        <div className="field">
          <label htmlFor="p-origin">From</label>
          <select id="p-origin" value={form.origin} onChange={(e) => set("origin", e.target.value)}>
            {m.origins.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="p-dest">To</label>
          <select
            id="p-dest"
            value={form.destination}
            onChange={(e) => set("destination", e.target.value)}
          >
            {m.destinations.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="p-start">Arrive</label>
          <input
            id="p-start"
            type="date"
            value={form.start}
            onChange={(e) => e.target.value && set("start", e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="p-nights">Nights</label>
          <input
            id="p-nights"
            type="number"
            min={1}
            max={14}
            value={form.nights}
            onChange={(e) => set("nights", Number(e.target.value))}
          />
        </div>
        <div className="field">
          <label htmlFor="p-trav">Travellers</label>
          <input
            id="p-trav"
            type="number"
            min={1}
            max={12}
            value={form.travellers}
            onChange={(e) => set("travellers", Number(e.target.value))}
          />
        </div>
        <div className="field">
          <label htmlFor="p-budget">Total budget (₹)</label>
          <input
            id="p-budget"
            type="number"
            min={500}
            step={500}
            value={form.budget}
            onChange={(e) => set("budget", Number(e.target.value))}
          />
        </div>
        <div className="field">
          <label htmlFor="p-stay">Stay</label>
          <select
            id="p-stay"
            value={form.stay_pref}
            onChange={(e) => set("stay_pref", e.target.value as PlanRequest["stay_pref"])}
          >
            <option value="any">Any (cheapest that fits)</option>
            <option value="budget">Budget / dorm</option>
            <option value="standard">Standard</option>
            <option value="family">Family room</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="p-mode">Transport</label>
          <select
            id="p-mode"
            value={form.transport}
            onChange={(e) => set("transport", e.target.value as PlanRequest["transport"])}
          >
            <option value="bus">Bus</option>
            <option value="car">Car</option>
          </select>
        </div>
        <div className={`field ${s.full}`}>
          <label>Interests</label>
          <div className={s.chips}>
            {m.interests.map((t) => {
              const on = form.interests.includes(t);
              return (
                <button
                  type="button"
                  key={t}
                  className={`${s.chip} ${on ? s.chipOn : ""}`}
                  aria-pressed={on}
                  onClick={() =>
                    set("interests", on ? form.interests.filter((x) => x !== t) : [...form.interests, t])
                  }
                >
                  {t}
                </button>
              );
            })}
          </div>
        </div>
        <div className={`field ${s.full}`} style={{ flexDirection: "row", alignItems: "center" }}>
          <input
            id="p-green"
            type="checkbox"
            checked={form.sustainability}
            onChange={(e) => set("sustainability", e.target.checked)}
          />
          <label htmlFor="p-green" style={{ textTransform: "none", fontSize: 13 }}>
            Prefer stays that report more sustainability practices
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy} style={{ marginLeft: "auto" }}>
            {busy ? "Planning…" : "Plan my trip"}
          </button>
        </div>
      </form>

      {error && <div className="state error">Could not plan this trip: {error}</div>}
      {!plan && !error && <Info>Fill in the form and press “Plan my trip”.</Info>}
      {plan && <PlanView plan={plan} onUse={(req) => { setForm(req); submit(req); }} />}
    </>
  );
}

function PlanView({ plan, onUse }: { plan: TripPlan; onUse: (r: PlanRequest) => void }) {
  const req = plan.request;
  return (
    <>
      <div className="insight-strip">
        <div className="insight-tile">
          <div className="tile-label">Estimated total</div>
          <div className="tile-value">{inr(plan.total)}</div>
          <div className="tile-note">
            {inr(plan.per_person)} per person ·{" "}
            {plan.within_budget
              ? `within your ${inr(req.budget)} budget`
              : `${inr(plan.total - req.budget)} over your budget`}
          </div>
        </div>
        <div className="insight-tile">
          <div className="tile-label">Expected crowd</div>
          <div className="tile-value">
            <CategoryPill category={plan.demand.category} index={plan.demand.mean_index} />
          </div>
          <div className="tile-note">
            {plan.destination_name}, {fmtDay(req.start)} – {fmtDay(plan.end)}
          </div>
        </div>
        <div className="insight-tile">
          <div className="tile-label">Travel emissions ({req.transport})</div>
          <div className="tile-value">
            {plan.carbon.find((c) => c.label.includes("your choice"))?.value} kg CO₂
          </div>
          <div className="tile-note">Return trip, rough estimate; see assumptions below</div>
        </div>
      </div>

      <SectionHeading title="💸 Where the money goes" description="Each line shows its formula." />
      <div className="chart-panel" style={{ padding: 14 }}>
        <table className={s.factors}>
          <tbody>
            {plan.costs.map((c) => (
              <tr key={c.label}>
                <td>
                  {c.label} <BasisTag basis={c.basis} />
                  <div className={s.muted}>{c.detail}</div>
                </td>
                <td>{inr(Number(c.value))}</td>
              </tr>
            ))}
            <tr>
              <td>
                <strong>Total</strong>
              </td>
              <td>{inr(plan.total)}</td>
            </tr>
          </tbody>
        </table>
        <div style={{ marginTop: 10 }}>
          <DownloadCsv rows={plan.costs} filename={`trip_costs_${req.destination}.csv`} />
        </div>
      </div>

      <SectionHeading title="🗓️ Day by day" />
      <div className={s.grid3}>
        {plan.itinerary.map((d, i) => (
          <div className={s.card} key={d.day}>
            <div className={s.cardHead}>
              <h3>
                Day {i + 1} · {fmtDay(d.day)}
              </h3>
              {d.demand && <CategoryPill category={d.demand} />}
            </div>
            <ul className={s.list}>
              {d.items.map((it) => (
                <li key={it}>{it}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      {plan.stay ? (
        <p className="caption">
          Stay: {plan.stay.property_id} ({plan.stay.kind}), {plan.stay.rooms} ×{" "}
          {plan.stay.category} room at {inr(plan.stay.price_per_night)}/night. Picked for the
          fewest guest-feedback gaps, then price{req.sustainability ? ", after reported practices" : ""}.
        </p>
      ) : (
        <p className="caption">
          No profiled stays in {plan.destination_name}: the stay line uses a typical price.
        </p>
      )}

      {plan.variants.length > 0 && (
        <>
          <SectionHeading title="↔️ Cheaper or quieter options" />
          <div className={s.grid2}>
            {plan.variants.map((v) => (
              <div className={s.card} key={v.label}>
                <div className={s.cardHead}>
                  <h3>{v.label}</h3>
                  <CategoryPill category={v.category} index={v.mean_index} />
                </div>
                <div>
                  {v.how}: <strong>{inr(v.total)}</strong> ({signedInr(v.delta_cost)}), crowd{" "}
                  {v.delta_index > 0 ? "+" : ""}
                  {v.delta_index} points
                </div>
                <button
                  className="btn"
                  style={{ marginTop: 10 }}
                  onClick={() =>
                    onUse({
                      ...req,
                      destination: v.destination,
                      start: v.start,
                      transport: v.transport as PlanRequest["transport"],
                      stay_pref: v.label === "Lower budget" ? "budget" : req.stay_pref,
                    })
                  }
                >
                  Use this option
                </button>
              </div>
            ))}
          </div>
        </>
      )}

      <SectionHeading
        title="🌿 Carbon: compare modes"
        description="A rough estimate from sourced factors; not a precise measurement."
      />
      <div className="chart-panel" style={{ padding: 14 }}>
        <table className={s.factors}>
          <tbody>
            {plan.carbon.map((c) => (
              <tr key={c.label}>
                <td>
                  {c.label} <BasisTag basis={c.basis} />
                  <div className={s.muted}>{c.detail}</div>
                </td>
                <td>{c.value} kg</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <SectionHeading
        title="🧶 Local sellers and experiences"
        description="Locally owned, non-restaurant businesses at your destination (SYNTHETIC, unverified)."
      />
      {plan.sellers.length === 0 ? (
        <Info>No local sellers listed for {plan.destination_name} yet.</Info>
      ) : (
        <div className={s.grid3}>
          {plan.sellers.map((x) => (
            <div className={s.card} key={x.id}>
              <h3>{x.name}</h3>
              <div className={s.muted}>
                {x.category} · {x.price}
              </div>
              <div style={{ fontSize: 13, marginTop: 4 }}>{x.offering}</div>
              <span className="badge" style={{ marginTop: 8 }}>
                {x.verification}
              </span>
            </div>
          ))}
        </div>
      )}
      <p className="caption">{plan.notes.join(" ")}</p>
    </>
  );
}
