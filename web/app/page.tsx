"use client";

import Link from "next/link";
import { fmtPct, useData, type Snapshot } from "@/lib/data";
import { ChangeSplit, ErrorState, Loading, WhosePill } from "@/components/ui";

const TOOLS = [
  {
    href: "/property",
    title: "Your property",
    text: "What to fix first, since when, and whether each problem is yours alone or everyone's.",
  },
  {
    href: "/market",
    title: "The market",
    text: "Which declines the whole cluster shares, so you stop chasing problems that are not yours.",
  },
  {
    href: "/fix-check",
    title: "Did my fix work?",
    text: "A before and after check that takes out what the market did over the same months.",
  },
  {
    href: "/explorer",
    title: "Review explorer",
    text: "Search the reviews and see the exact clause behind every label, in English, Hinglish or Hindi.",
  },
];

// The first property whose top priority has a dated, market-adjusted shift: the
// example that shows a decline the market does not share.
function ownProblemExample(data: Snapshot) {
  for (const p of data.meta.properties) {
    const pd = data.per_property[p];
    const top = pd.priority_actions[0];
    if (!top || top.whose_problem !== "yours alone" || !top.started) continue;
    const cp = pd.changepoints.find((c) => c.aspect === top.aspect && c.change_month === top.started);
    if (cp) return { property: p, top, cp };
  }
  return null;
}

export default function Home() {
  const { data, error } = useData();
  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading />;
  const headline = data.market_headline;
  const own = ownProblemExample(data);
  const hood = data.neighbourhoods[0];

  return (
    <>
      <section className="home-hero">
        <h1>Your reviews got worse. Is it your property, your street, or the whole market?</h1>
        <p className="lede">
          One property&apos;s reviews cannot answer that. A December dip that hits every hotel in a
          hill town needs a different response from a kitchen problem only you have. Compare
          yourself with your cluster and the two separate.
        </p>
        <div className="hero-actions">
          <Link className="btn btn-primary" href="/property">
            Open your property
          </Link>
          <Link className="btn btn-quiet" href="/market">
            See what the market shares
          </Link>
        </div>
      </section>

      <section className="contrast" aria-labelledby="contrast-title">
        <h2 id="contrast-title" className="visually-hidden">
          Two declines, two owners
        </h2>
        {own && (
          <article className="contrast-case">
            <header>
              <h3>
                {own.property}: {own.top.aspect} since {own.top.started}
              </h3>
              <WhosePill value={own.top.whose_problem} />
            </header>
            <ChangeSplit
              rows={[
                { label: "Your reviews", note: "plain before and after", value: own.cp.raw_delta },
                { label: "The market", note: "other properties, same months", value: own.cp.market_delta },
                { label: "Yours alone", note: "after taking the market out", value: own.cp.delta, verdict: true },
              ]}
            />
            <p>
              {Math.abs(own.cp.market_delta ?? 0) < 0.1
                ? `The market barely moved while ${own.top.aspect.toLowerCase()} fell here.`
                : `Part of the change is the market's; the rest is this property's.`}{" "}
              It tops this property&apos;s list of what to fix.
            </p>
            <Link href={`/property/?property=${encodeURIComponent(own.property)}`}>
              Open {own.property}
            </Link>
          </article>
        )}
        {headline && (
          <article className="contrast-case">
            <header>
              <h3>Every property: {headline.aspect}</h3>
              <WhosePill value="everyone's" />
            </header>
            <p className="contrast-figure">
              <span>{fmtPct(headline.pct_negative)}</span> of {headline.aspect.toLowerCase()}{" "}
              mentions are negative across {headline.n_properties_reviewed} properties.
            </p>
            <p>
              Pattern: {headline.pattern}. The whole cluster shares it, so it is not a gap against
              your competitors.
            </p>
            <Link href="/market/">See the market view</Link>
          </article>
        )}
        {hood && (
          <article className="contrast-case">
            <header>
              <h3>
                {hood.n_members} neighbours: {hood.aspect} since {hood.change_month}
              </h3>
              <WhosePill value="your neighbourhood's" />
            </header>
            <ChangeSplit
              rows={hood.members.map((m) => ({
                label: m,
                note: "vs the rest of the market",
                value: hood.gaps[m] ?? null,
              }))}
            />
            <p>
              Each is too small to prove alone; together, within {hood.radius_km.toFixed(2)} km,
              the decline is clear (p = {hood.p_value.toFixed(3)}). Raise it together, not one by one.
            </p>
            <Link href={`/market/?aspect=${encodeURIComponent(hood.aspect)}`}>See it on the map</Link>
          </article>
        )}
      </section>

      <section className="tools" aria-labelledby="tools-title">
        <h2 id="tools-title">Four views, one question</h2>
        <ul className="tool-list">
          {TOOLS.map((t) => (
            <li key={t.href}>
              <Link href={t.href}>
                <span className="tool-title">{t.title}</span>
                <span className="tool-text">{t.text}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section className="about">
        <h2>How to read this</h2>
        <p>
          Scores are mean sentiment per aspect on a scale from −1 to +1, from {data.meta.n_reviews.toLocaleString()}{" "}
          reviews of {data.meta.properties.length} properties between {data.meta.date_min} and{" "}
          {data.meta.date_max}. A gap is only flagged when it survives a multiple-testing correction.
          We work for the properties that MakeMyTrip, Goibibo and Booking.com list, not against
          those platforms. Snapshot generated {data.meta.generated_at.slice(0, 10)}.
        </p>
      </section>
    </>
  );
}
