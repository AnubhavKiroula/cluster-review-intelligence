"use client";

import Link from "next/link";
import { useData } from "@/lib/data";
import { ErrorState, Loading, PageIntro, SyntheticBanner } from "@/components/ui";

export default function Home() {
  const { data, error } = useData();
  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading />;
  const m = data.meta;
  const marketSignals = data.destination_summary.filter((row) => row.scope === "market-wide");
  const leadingSignal = [...marketSignals].sort((a, b) => b.pct_negative - a.pct_negative)[0];

  return (
    <>
      <PageIntro
        eyebrow="Workspace overview"
        icon="◈"
        title="Cluster review intelligence"
        description="Turn guest voice into an action plan for every property, aspect, and destination-level signal."
      />
      <SyntheticBanner />

      <section className="hero-grid" aria-label="Dashboard introduction">
        <div className="hero-panel hero-panel-primary">
          <span className="hero-kicker">THE DECISION LAYER</span>
          <h2>Know what to fix — and who owns the problem.</h2>
          <p>
            Compare each property with its cluster, follow sentiment over time, and separate a
            competitive gap from an issue the whole destination shares.
          </p>
          <Link className="btn btn-primary" href="/property">
            Open property workspace <span aria-hidden>→</span>
          </Link>
        </div>
        <div className="hero-panel hero-panel-insight">
          <div>
            <div className="insight-label">Cluster signal</div>
            {leadingSignal ? (
              <>
                <h3>{leadingSignal.aspect} needs destination attention.</h3>
                <p>
                  {Math.round(leadingSignal.pct_negative * 100)}% of mentions are negative across{" "}
                  {leadingSignal.n_properties_reviewed} properties in the current snapshot.
                </p>
              </>
            ) : (
              <>
                <h3>No market-wide issue flagged.</h3>
                <p>The current snapshot has no aspect classified as a destination-wide concern.</p>
              </>
            )}
          </div>
          <div className="insight-footer">
            <span className="status-dot" aria-hidden />
            Evidence-led · snapshot available
          </div>
        </div>
      </section>

      <div className="cards">
        <div className="metric-card">
          <div className="metric-icon" aria-hidden>⌂</div>
          <div className="value">{m.properties.length}</div>
          <div className="label">Properties</div>
        </div>
        <div className="metric-card">
          <div className="metric-icon" aria-hidden>⌁</div>
          <div className="value">{m.n_reviews.toLocaleString()}</div>
          <div className="label">Reviews</div>
        </div>
        <div className="metric-card">
          <div className="metric-icon" aria-hidden>⊙</div>
          <div className="value">{m.aspects.length}</div>
          <div className="label">Aspects tracked</div>
        </div>
        <div className="metric-card">
          <div className="metric-icon" aria-hidden>◷</div>
          <div className="value" style={{ fontSize: 17 }}>
            {m.date_min} – {m.date_max}
          </div>
          <div className="label">Date range</div>
        </div>
      </div>

      <div className="section-heading">
        <div>
          <h2>Choose a decision view</h2>
          <p className="section-description">Start with the question you need to answer today.</p>
        </div>
      </div>
      <div className="cardlinks">
        <Link className="cardlink" href="/property">
          <div className="t">🏨 Property scorecard</div>
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

      <div className="panel">
        <div className="eyebrow">Data &amp; methodology</div>
        <p className="caption" style={{ marginTop: 0 }}>
          This workspace is transparent by design. Explore the matched review clauses, download
          every table, and review the limitations before acting. Real-data accuracy remains{" "}
          <code>TBD</code> until the labelled set exists. Snapshot generated {m.generated_at}.
        </p>
      </div>
    </>
  );
}
