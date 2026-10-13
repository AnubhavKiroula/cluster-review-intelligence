"use client";

import Link from "next/link";
import { fmtPct, useData } from "@/lib/data";
import { ErrorState, Loading, PageIntro, SyntheticBanner } from "@/components/ui";

export default function Home() {
  const { data, error } = useData();
  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading />;
  const headline = data.market_headline;

  return (
    <>
      <PageIntro
        eyebrow="For hotel and homestay owners"
        icon="◈"
        title="Cluster review intelligence"
        description="When your reviews get worse on something, is it your problem or the whole market's? Your own reviews cannot tell. Your cluster can."
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
          <p>
            MakeMyTrip, Goibibo and Booking.com help travellers find you. We work on the supply
            side, for the properties those platforms list, and do not compete with them.
          </p>
          <Link className="btn btn-primary" href="/property">
            Open property workspace <span aria-hidden>→</span>
          </Link>
        </div>
        <div className="hero-panel hero-panel-insight">
          <div>
            <div className="insight-label">Market signal</div>
            {headline ? (
              <>
                <h3>{headline.aspect} is a market-wide issue, not one property&apos;s.</h3>
                <p>
                  {fmtPct(headline.pct_negative)} of mentions are negative across{" "}
                  {headline.n_properties_reviewed} properties: {headline.pattern}.
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

      <div className="section-heading">
        <div>
          <h2>Choose a decision view</h2>
          <p className="section-description">Start with the question you need to answer today.</p>
        </div>
      </div>
      <div className="cardlinks">
        <Link className="cardlink" href="/property">
          <div className="t">🏨 Property</div>
          <div className="d">What to fix first, and whether each problem is yours alone or everyone&apos;s.</div>
        </Link>
        <Link className="cardlink" href="/market">
          <div className="t">⚖️ Market</div>
          <div className="d">Which declines are market-wide and which belong to one property.</div>
        </Link>
        <Link className="cardlink" href="/fix-check">
          <div className="t">🔧 Did my fix work?</div>
          <div className="d">A before/after check that nets out what the market did meanwhile.</div>
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
          <code>TBD</code> until the labelled set exists. Snapshot generated{" "}
          {data.meta.generated_at}.
        </p>
      </div>
    </>
  );
}
