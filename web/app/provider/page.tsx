"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { inr, isoDate, query, useApi, type Meta, type ProviderResponse } from "@/lib/api";
import { Info, Loading, PageIntro, SectionHeading } from "@/components/ui";
import {
  ApiErrorState,
  ApiStatusBanner,
  EvidenceList,
  travelStyles as s,
} from "@/components/travel";

const KIND_LABEL: Record<string, string> = {
  review_priority: "From guest reviews",
  amenity_gap: "Amenity gap",
  demand_peak: "Upcoming demand",
  offer_window: "Low-demand window",
  sustainability: "Sustainability",
};

export default function ProviderPage() {
  const meta = useApi<Meta>("/meta");
  const [prop, setProp] = useState("Property F");
  const [days, setDays] = useState(90);
  const start = isoDate(new Date());

  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("property");
    if (q) setProp(q);
  }, []);

  const res = useApi<ProviderResponse>(
    `/provider/${encodeURIComponent(prop)}/insights?${query({ start, days })}`,
  );

  if (meta.error) return <ApiErrorState error={meta.error} />;
  if (!meta.data) return <Loading />;

  return (
    <>
      <PageIntro
        eyebrow="Accommodation provider"
        icon="🛎️"
        title="What to improve, and when demand is coming"
        description="Decision support for hotels, homestays, guesthouses and camps: review-based priorities, amenity gaps, upcoming peaks against your room mix, and quiet windows for offers. Every item says why."
      />
      <ApiStatusBanner />

      <div className="controls">
        <div className="field">
          <label htmlFor="pv-prop">Property</label>
          <select id="pv-prop" value={prop} onChange={(e) => setProp(e.target.value)}>
            {meta.data.properties.map((p) => (
              <option key={p.id} value={p.id}>
                {p.id} · {p.kind}, {meta.data!.destinations.find((d) => d.id === p.destination)?.name}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="pv-days">Look ahead</label>
          <select id="pv-days" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            {[30, 60, 90, 120].map((d) => (
              <option key={d} value={d}>
                {d} days from today
              </option>
            ))}
          </select>
        </div>
      </div>

      {res.error ? (
        <ApiErrorState error={res.error} />
      ) : !res.data ? (
        <Loading />
      ) : (
        <>
          <div className="insight-strip">
            <div className="insight-tile">
              <div className="tile-label">Listing</div>
              <div className="tile-value" style={{ fontSize: 17 }}>
                {res.data.profile.kind} in {res.data.profile.destination_name}
              </div>
              <div className="tile-note">
                {res.data.profile.total_rooms} rooms · {inr(res.data.profile.price_from)}–
                {inr(res.data.profile.price_to)} (SYNTHETIC)
              </div>
            </div>
            <div className="insight-tile">
              <div className="tile-label">Guests praise / flag</div>
              <div className="tile-value" style={{ fontSize: 15 }}>
                {res.data.profile.leads.join(", ") || "—"} / {res.data.profile.lags.join(", ") || "—"}
              </div>
              <div className="tile-note">Aspect sentiment vs the cluster, from review text</div>
            </div>
            <div className="insight-tile">
              <div className="tile-label">Room mix</div>
              <div className="tile-value" style={{ fontSize: 15 }}>
                {res.data.profile.rooms.map((r) => `${r.count} ${r.category}`).join(" · ")}
              </div>
              <div className="tile-note">
                <Link href={`/property/?property=${encodeURIComponent(prop)}`}>
                  Open the full review scorecard →
                </Link>
              </div>
            </div>
          </div>

          <SectionHeading
            title="✅ Recommendations"
            description="Ranked high → low. Estimates are decision support, not revenue predictions or automatic pricing."
          />
          {res.data.insights.length === 0 ? (
            <Info>No recommendations for this window.</Info>
          ) : (
            <div style={{ display: "grid", gap: 12 }}>
              {res.data.insights.map((i, n) => (
                <div key={n} className={`${s.card} ${s.priority} ${s[i.priority]}`}>
                  <div className={s.cardHead}>
                    <h3>{i.title}</h3>
                    <span className="badge">
                      {KIND_LABEL[i.kind] ?? i.kind} · {i.priority}
                    </span>
                  </div>
                  <p style={{ margin: "4px 0", fontSize: 14 }}>
                    <strong>Why:</strong> {i.why}
                  </p>
                  {i.evidence.length > 0 && (
                    <details>
                      <summary className={s.muted}>Evidence ({i.evidence.length})</summary>
                      <EvidenceList items={i.evidence} />
                    </details>
                  )}
                </div>
              ))}
            </div>
          )}
          <p className="caption">{res.data.profile.note}</p>
        </>
      )}
    </>
  );
}
