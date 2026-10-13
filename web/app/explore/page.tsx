"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  addDays,
  fmtDay,
  inr,
  isoDate,
  query,
  useApi,
  type AlternativesResponse,
  type DemandDay,
  type Meta,
  type StayProfile,
  type TripDemandResponse,
} from "@/lib/api";
import { Info, Loading, PageIntro, SectionHeading } from "@/components/ui";
import {
  ApiErrorState,
  ApiStatusBanner,
  BasisTag,
  CategoryPill,
  EvidenceList,
  FactorTable,
  travelStyles as s,
} from "@/components/travel";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const CELL_BG: Record<string, string> = {
  Low: "#d8f0ea",
  Moderate: "#fbefc0",
  High: "#ffd9ad",
  "Very High": "#ffc4bc",
};

export default function ExplorePage() {
  const meta = useApi<Meta>("/meta");
  const [dest, setDest] = useState("mussoorie");
  const [start, setStart] = useState(() => isoDate(new Date()));
  const [nights, setNights] = useState(2);
  const [home, setHome] = useState("delhi");

  // Deep link: /explore/?destination=mussoorie&start=2026-12-25&nights=2
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    if (q.get("destination")) setDest(q.get("destination")!);
    if (q.get("start")) setStart(q.get("start")!);
    if (q.get("nights")) setNights(Math.min(14, Math.max(1, Number(q.get("nights")) || 2)));
  }, []);

  const monthStart = useMemo(() => {
    const [y, m] = start.split("-").map(Number);
    return isoDate(new Date(y, m - 1, 1));
  }, [start]);

  const trip = useApi<TripDemandResponse>(
    `/demand/trip?${query({ destination: dest, start, nights })}`,
  );
  const cal = useApi<DemandDay[]>(
    `/demand/calendar?${query({ destination: dest, start: monthStart, days: 42 })}`,
  );
  const alts = useApi<AlternativesResponse>(
    `/alternatives?${query({ destination: dest, start, nights, home })}`,
  );
  const stays = useApi<StayProfile[]>(`/stays?${query({ destination: dest })}`);

  if (meta.error) return <ApiErrorState error={meta.error} />;
  if (!meta.data) return <Loading />;
  const m = meta.data;
  const destMeta = m.destinations.find((d) => d.id === dest);
  const holidays = new Map(m.holidays.map((h) => [h.date, h.name]));

  return (
    <>
      <PageIntro
        eyebrow="Traveller · crowd-aware planning"
        icon="🧭"
        title="When and where to go"
        description="Pick a hill destination and dates. See how busy it is likely to be and why, quieter dates nearby, and similar places with more room. No star ratings."
      />
      <ApiStatusBanner />

      <div className="controls">
        <div className="field">
          <label htmlFor="ex-dest">Destination</label>
          <select id="ex-dest" value={dest} onChange={(e) => setDest(e.target.value)}>
            {m.destinations.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.state})
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="ex-start">Arrive</label>
          <input
            id="ex-start"
            className={s.controlsInput}
            type="date"
            value={start}
            onChange={(e) => e.target.value && setStart(e.target.value)}
          />
        </div>
        <div className="field" style={{ minWidth: 110 }}>
          <label htmlFor="ex-nights">Nights</label>
          <select id="ex-nights" value={nights} onChange={(e) => setNights(Number(e.target.value))}>
            {[1, 2, 3, 4, 5, 6, 7].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="ex-home">Travelling from</label>
          <select id="ex-home" value={home} onChange={(e) => setHome(e.target.value)}>
            {m.origins.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {trip.error ? (
        <ApiErrorState error={trip.error} />
      ) : !trip.data ? (
        <Loading />
      ) : (
        <TripSummary
          t={trip.data}
          name={destMeta?.name ?? dest}
          onPick={(d) => setStart(d)}
        />
      )}

      <SectionHeading
        title="📅 Demand calendar"
        description="Each day's index is the sum of its factors (click a day to plan around it). Weekends, gazetted holidays, long weekends and assumed school / year-end windows push demand up."
      />
      {cal.error ? (
        <ApiErrorState error={cal.error} />
      ) : !cal.data ? (
        <Loading />
      ) : (
        <div className="chart-panel" style={{ padding: 14 }}>
          <div className={s.calendar}>
            {WEEKDAYS.map((w) => (
              <div key={w} className={s.weekday}>
                {w}
              </div>
            ))}
            {Array.from({ length: mondayOffset(monthStart) }).map((_, i) => (
              <div key={`pad${i}`} />
            ))}
            {cal.data.map((d) => {
              const inTrip = d.day >= start && d.day < addDays(start, nights);
              return (
                <button
                  key={d.day}
                  className={`${s.dayCell} ${inTrip ? s.selected : ""}`}
                  style={{ background: CELL_BG[d.category] }}
                  onClick={() => setStart(d.day)}
                  title={`${fmtDay(d.day)}: ${d.category} (${d.index}/100)${d.borderline ? " · borderline" : ""}`}
                >
                  {Number(d.day.slice(8))}
                  <b>{d.index}</b>
                  {holidays.get(d.day) ? (
                    <span className={s.holidayDot}>★ {holidays.get(d.day)}</span>
                  ) : null}
                </button>
              );
            })}
          </div>
          <p className="caption">
            {Object.entries(CELL_BG).map(([k, bg]) => (
              <span key={k} style={{ background: bg, padding: "2px 8px", borderRadius: 6, marginRight: 6 }}>
                {k}
              </span>
            ))}
            <br />★ = gazetted Central Government holiday (DoPT lists, covered{" "}
            {m.holiday_coverage.start} to {m.holiday_coverage.end}). State holidays are not
            included. Outlined days = your stay.
          </p>
        </div>
      )}

      <SectionHeading
        title="🔀 Similar, less crowded places"
        description="Ranked by similarity × crowd relief, capped by an assumed capacity ceiling so the engine never just moves pressure to a more fragile place."
      />
      {alts.error ? (
        <ApiErrorState error={alts.error} />
      ) : !alts.data ? (
        <Loading />
      ) : alts.data.alternatives.length === 0 ? (
        <Info>
          No clearly quieter, similar destination with headroom for these dates. That is an
          answer too: consider shifting dates instead.
        </Info>
      ) : (
        <>
          <div className="callout">{alts.data.alternatives[0].explanation.why_origin_busy}</div>
          <div className={s.grid3}>
            {alts.data.alternatives.map((a) => (
              <div className={s.card} key={a.destination}>
                <div className={s.cardHead}>
                  <h3>{a.name}</h3>
                  <CategoryPill category={a.category} index={a.mean_index} />
                </div>
                <ul className={s.list}>
                  <li>{a.explanation.why_similar}</li>
                  <li>{a.explanation.expected_crowd}</li>
                  <li>{a.explanation.trade_off}</li>
                  <li className={s.muted}>{a.explanation.limitations}</li>
                </ul>
                <details style={{ marginTop: 8 }}>
                  <summary className={s.muted}>
                    Score {a.score.toFixed(3)} · similarity {a.similarity}
                  </summary>
                  <EvidenceList items={a.components} />
                </details>
                <div style={{ marginTop: 10 }}>
                  <button className="btn" onClick={() => setDest(a.destination)}>
                    Explore {a.name}
                  </button>
                </div>
              </div>
            ))}
          </div>
          {alts.data.excluded.length > 0 && (
            <details style={{ marginTop: 12 }}>
              <summary className="caption">
                Not suggested ({alts.data.excluded.length}) and why
              </summary>
              <ul className={s.list}>
                {alts.data.excluded.map(([id, why]) => (
                  <li key={id}>
                    <strong>{m.destinations.find((d) => d.id === id)?.name ?? id}</strong>: {why}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </>
      )}

      <SectionHeading
        title="🏡 Where to stay (no star ratings)"
        description="Compare price, rooms, listed amenities, self-reported practices and what guests say about each aspect, computed from review text."
      />
      {stays.error ? (
        <ApiErrorState error={stays.error} />
      ) : !stays.data ? (
        <Loading />
      ) : stays.data.length === 0 ? (
        <Info>
          No profiled stays in {destMeta?.name} yet (the demo profiles stays in Mussoorie,
          Dhanaulti, Kanatal and Chakrata).
        </Info>
      ) : (
        <div className={s.grid3}>
          {stays.data.map((p) => (
            <StayCard key={p.property_id} p={p} />
          ))}
        </div>
      )}

      <div style={{ marginTop: 22 }}>
        <Link
          className="btn btn-primary"
          href={`/plan/?${query({ destination: dest, start, nights, origin: home })}`}
        >
          Plan this trip with a budget <span aria-hidden>→</span>
        </Link>
      </div>
    </>
  );
}

// Blank cells before the 1st so the grid starts on Monday (local date, no UTC shift).
function mondayOffset(iso: string): number {
  const [y, m, d] = iso.split("-").map(Number);
  return (new Date(y, m - 1, d).getDay() + 6) % 7;
}

function TripSummary({
  t,
  name,
  onPick,
}: {
  t: TripDemandResponse;
  name: string;
  onPick: (d: string) => void;
}) {
  const first = t.trip.days[0];
  return (
    <>
      <div className="insight-strip">
        <div className="insight-tile">
          <div className="tile-label">Expected crowd, {name}</div>
          <div className="tile-value">
            <CategoryPill category={t.trip.category} index={t.trip.mean_index} />
          </div>
          <div className="tile-note">
            Average over {t.trip.nights} night(s) from {fmtDay(t.trip.start)} · indicative
          </div>
        </div>
        <div className="insight-tile">
          <div className="tile-label">Main drivers</div>
          <div className="tile-value" style={{ fontSize: 15 }}>
            {t.drivers.length ? t.drivers.map(([l, p]) => `${l} (+${p})`).join(", ") : "Season only"}
          </div>
          <div className="tile-note">Average points per day above the baseline</div>
        </div>
        <div className="insight-tile">
          <div className="tile-label">Quieter nearby dates</div>
          <div className="tile-value" style={{ fontSize: 15 }}>
            {t.quieter.length ? (
              <button className="btn" onClick={() => onPick(t.quieter[0].start)}>
                {fmtDay(t.quieter[0].start)} · −{t.quieter[0].drop.toFixed(0)} pts
              </button>
            ) : (
              "None clearly quieter within ±7 days"
            )}
          </div>
          <div className="tile-note">
            {t.quieter.length && t.quieter[0].avoids.length
              ? `Avoids: ${t.quieter[0].avoids.join(", ")}`
              : "Shifts that lower the trip average by 10+ points"}
          </div>
        </div>
      </div>
      <details className="panel">
        <summary>
          <strong>Why {first.index}/100 on {fmtDay(first.day)}?</strong>{" "}
          <span className="caption">every point, with its source</span>
        </summary>
        <FactorTable factors={first.factors} />
        <p className="caption">{first.notes.join(" ")}</p>
      </details>
    </>
  );
}

function StayCard({ p }: { p: StayProfile }) {
  const reported = p.practices.filter((x) => x.status === "reported");
  return (
    <div className={s.card}>
      <div className={s.cardHead}>
        <h3>{p.property_id}</h3>
        <span className="badge">{p.kind}</span>
      </div>
      <div>
        <strong>{inr(p.price_from)}</strong>
        {p.price_to > p.price_from ? `–${inr(p.price_to)}` : ""} / room / night{" "}
        <BasisTag basis="synthetic" />
      </div>
      <div className={s.muted}>
        {p.total_rooms} rooms · {p.rooms.map((r) => `${r.count} ${r.category}`).join(", ")}
      </div>
      <ul className={s.list}>
        {p.suitability.map((x) => (
          <li key={x.label}>
            <strong>{x.label}</strong> <span className={s.muted}>({x.detail})</span>
          </li>
        ))}
      </ul>
      <div style={{ marginTop: 8, fontSize: 13 }}>
        <strong>Guests praise:</strong> {p.leads.length ? p.leads.join(", ") : "—"}
        <br />
        <strong>Guests flag:</strong> {p.lags.length ? p.lags.join(", ") : "—"}
      </div>
      <div className={s.muted} style={{ marginTop: 6 }}>
        Practices reported: {reported.length}/{p.practices.length} (self-reported, unverified) ·
        Amenities listed: {p.amenities.join(", ")}
      </div>
      <details style={{ marginTop: 8 }}>
        <summary className={s.muted}>Aspect-by-aspect guest feedback</summary>
        <table className={s.factors}>
          <tbody>
            {p.feedback.map((f) => (
              <tr key={f.aspect}>
                <td>
                  {f.aspect} <span className={s.muted}>(n={f.n})</span>
                </td>
                <td>
                  {f.mean === null ? "—" : f.mean.toFixed(2)}{" "}
                  <span className={s.muted}>
                    {f.flag === "on_par" ? "on par" : f.flag}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="caption">
          Mean sentiment (−1…+1) vs the cluster; {p.consistency.label.toLowerCase()}:{" "}
          {p.consistency.detail}. {p.note}
        </p>
      </details>
    </div>
  );
}
