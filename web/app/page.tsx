"use client";

import Link from "next/link";
import { fmtPct, useData } from "@/lib/data";
import { ErrorState, Loading, PageIntro, SourceChip } from "@/components/ui";

export default function Home() {
  const { data, error } = useData();
  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading />;
  const headline = data.market_headline;
  const p = data.meta.provenance;
  const flagged = Object.values(data.per_property).filter((x) => x.priority_actions.length > 0);

  return (
    <>
      <PageIntro
        eyebrow="For hotel and homestay owners"
        icon="◈"
        title="Cluster review intelligence"
        description="When your reviews get worse on something, is it your problem or the whole market's? Your own reviews cannot tell. Your cluster can."
        chip={<SourceChip kind="real" />}
      />

      <section className="hero-grid" aria-label="Dashboard introduction">
        <div className="hero-panel hero-panel-primary">
          <span className="hero-kicker">THE DECISION LAYER</span>
          <h2>Know what to fix — and who owns the problem.</h2>
          <p>
            Compare each property with its cluster, follow sentiment over time where reviews
            carry dates, and separate a competitive gap from an issue the whole destination
            shares.
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
                <h3>{headline.aspect} is a market-wide weak spot: an opportunity.</h3>
                <p>
                  {fmtPct(headline.pct_negative)} of mentions are negative across{" "}
                  {headline.n_properties_reviewed} properties: {headline.pattern}.
                </p>
              </>
            ) : (
              <>
                <h3>No shared weak spot in {p?.town ?? "this cluster"}.</h3>
                <p>
                  Every flagged gap belongs to individual hotels: {flagged.length} of{" "}
                  {data.meta.properties.length} hotels lag the cluster on at least one aspect.
                </p>
              </>
            )}
          </div>
          <div className="insight-footer">
            <span className="status-dot" aria-hidden />
            Evidence-led · snapshot available
          </div>
        </div>
      </section>

      {p && (
        <div className="insight-strip">
          <div className="insight-tile">
            <div className="tile-label">Reviews analysed</div>
            <div className="tile-value">{data.meta.n_reviews.toLocaleString()}</div>
            <div className="tile-note">
              From {p.hotels} {p.town} hotels: the whole local market
            </div>
          </div>
          <div className="insight-tile">
            <div className="tile-label">One hotel&apos;s own reviews</div>
            <div className="tile-value">{p.median_reviews_per_hotel}</div>
            <div className="tile-note">The median a single {p.town} hotel has to read</div>
          </div>
          <div className="insight-tile">
            <div className="tile-label">Hotels with a flagged gap</div>
            <div className="tile-value">
              {flagged.length} of {data.meta.properties.length}
            </div>
            <div className="tile-note">Each tested against the cluster, not a star average</div>
          </div>
        </div>
      )}

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
          <div className="d">A before/after check that nets out the market (method demo on a simulated timeline).</div>
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
          every table, and review the limitations before acting. The {p?.town} reviews have no
          dates, so time-based views run on a simulated timeline. Clause-level accuracy on real
          reviews remains <code>TBD</code> until the labelled set exists. Snapshot generated{" "}
          {data.meta.generated_at}.
        </p>
      </div>
    </>
  );
}
