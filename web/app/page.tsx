"use client";

import Link from "next/link";
import { useData } from "@/lib/data";
import { ErrorState, Loading, SyntheticBanner } from "@/components/ui";

export default function Home() {
  const { data, error } = useData();
  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading />;
  const m = data.meta;

  return (
    <>
      <h1>🏔️ Cluster Review Intelligence</h1>
      <p className="lede">
        <em>“Am I behind my cluster, since when, and is it just me or the whole market?”</em>
      </p>
      <SyntheticBanner />

      <p>
        A <strong>4.1-star average</strong> means different things for different hotels. One
        property&apos;s weak spot is a competitive gap it owns; another&apos;s is a problem the{" "}
        <em>entire cluster</em> shares every winter. This dashboard separates the two — and tells
        you what to fix first.
      </p>

      <div className="cards">
        <div className="card">
          <div className="value">{m.properties.length}</div>
          <div className="label">Properties</div>
        </div>
        <div className="card">
          <div className="value">{m.n_reviews.toLocaleString()}</div>
          <div className="label">Reviews</div>
        </div>
        <div className="card">
          <div className="value">{m.aspects.length}</div>
          <div className="label">Aspects tracked</div>
        </div>
        <div className="card">
          <div className="value" style={{ fontSize: 18 }}>
            {m.date_min} – {m.date_max}
          </div>
          <div className="label">Date range</div>
        </div>
      </div>

      <h2>Where to go</h2>
      <div className="cardlinks">
        <Link className="cardlink" href="/property">
          <div className="t">🏨 Property</div>
          <div className="d">Your scorecard vs the cluster, trends, and fix-this-first actions.</div>
        </Link>
        <Link className="cardlink" href="/market">
          <div className="t">⚖️ Market</div>
          <div className="d">The differentiator: market-wide vs property-specific issues.</div>
        </Link>
        <Link className="cardlink" href="/cluster">
          <div className="t">🗺️ Cluster</div>
          <div className="d">The property × aspect heatmap: who leads, who lags.</div>
        </Link>
        <Link className="cardlink" href="/destination">
          <div className="t">🧭 Destination</div>
          <div className="d">The tourism-board view of cluster-wide problems.</div>
        </Link>
        <Link className="cardlink" href="/explorer">
          <div className="t">🔍 Explorer</div>
          <div className="d">Search reviews; see the exact clause each label came from.</div>
        </Link>
      </div>

      <p className="caption">
        Honesty note: no accuracy or F1 numbers are shown here — see{" "}
        <code>docs/TODO_RESULTS.md</code> for what is measured and what is still{" "}
        <code>TBD</code> (CLAUDE.md rule 1). Snapshot generated {m.generated_at}.
      </p>
    </>
  );
}
