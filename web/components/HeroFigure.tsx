"use client";

// The home page's one figure, and the only load animation on the site.
//
// It is the product's argument in the order the product makes it: here is a real
// property's monthly sentiment, here is the month it broke, and here is that break
// divided into what the whole market did and what is left for this property alone.
// The line draws, then the split resolves under it.
//
// Every number is read from the snapshot (CLAUDE.md rule 1): the series is
// `per_property[p].trends[aspect]`, the month and the three deltas are the changepoint
// the Python core found. Nothing here is computed in the browser except pixel
// positions, and nothing is invented.
import { useEffect, useLayoutEffect, useRef } from "react";
import { ChangeSplit } from "@/components/ui";
import type { Changepoint, TrendPoint } from "@/lib/data";
import { DUR, loadGsap, prefersReducedMotion } from "@/lib/motion";

// A fixed drawing space, scaled by CSS. Sentiment runs -1 (bottom) to +1 (top).
const W = 480;
const H = 150;
const PAD = { l: 6, r: 6, t: 16, b: 20 };

const xAt = (i: number, n: number) =>
  PAD.l + (n <= 1 ? 0 : (i / (n - 1)) * (W - PAD.l - PAD.r));
const yAt = (mean: number) =>
  PAD.t + (1 - (Math.max(-1, Math.min(1, mean)) + 1) / 2) * (H - PAD.t - PAD.b);

export default function HeroFigure({
  property,
  aspect,
  trend,
  changepoint,
  synthetic,
}: {
  property: string;
  aspect: string;
  trend: TrendPoint[];
  changepoint: Changepoint;
  synthetic: boolean;
}) {
  const lineRef = useRef<SVGPathElement>(null);
  const breakRef = useRef<SVGGElement>(null);

  const n = trend.length;
  const path = trend.map((p, i) => `${i === 0 ? "M" : "L"}${xAt(i, n).toFixed(1)} ${yAt(p.mean).toFixed(1)}`).join(" ");

  // The month of the break, as an index into the series.
  const breakAt = trend.findIndex((p) => p.month.slice(0, 7) === changepoint.change_month);
  const breakX = breakAt >= 0 ? xAt(breakAt, n) : null;

  // Hide the line before the first paint, so it is never shown and then withdrawn.
  // If GSAP cannot be loaded the effect below puts it straight back.
  useLayoutEffect(() => {
    const el = lineRef.current;
    if (!el || prefersReducedMotion()) return;
    const len = el.getTotalLength();
    el.style.strokeDasharray = `${len}`;
    el.style.strokeDashoffset = `${len}`;
    if (breakRef.current) breakRef.current.style.opacity = "0";
  }, [path]);

  useEffect(() => {
    const el = lineRef.current;
    const mark = breakRef.current;
    if (!el) return;
    const show = () => {
      el.style.strokeDasharray = "";
      el.style.strokeDashoffset = "";
      if (mark) mark.style.opacity = "";
    };
    if (prefersReducedMotion()) return;

    let live = true;
    let tl: { kill(): void } | null = null;
    loadGsap().then((gsap) => {
      if (!live) return;
      if (!gsap) {
        show();
        return;
      }
      tl = gsap
        .timeline()
        // The decline is read left to right, at reading speed, once.
        .to(el, { strokeDashoffset: 0, duration: DUR.draw, ease: "power1.inOut" })
        // Then the month it happened, and only then.
        .to(mark, { opacity: 1, duration: DUR.base, ease: "power1.out" }, ">-0.1");
    });
    return () => {
      live = false;
      tl?.kill();
      show();
    };
  }, [path]);

  const months = `${trend[0]?.month.slice(0, 7) ?? ""} to ${trend[n - 1]?.month.slice(0, 7) ?? ""}`;

  return (
    <figure className="hero-figure">
      <div className="hero-figure-head">
        <h2>
          {property}: {aspect}, monthly
        </h2>
        <span>{months}</span>
      </div>
      <svg
        className="hero-trend"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Monthly mean ${aspect} sentiment at ${property} from ${months}, falling at ${changepoint.change_month}.`}
      >
        {/* Neutral sentiment, for the eye to measure the fall against. */}
        <line className="trend-zero" x1={PAD.l} x2={W - PAD.r} y1={yAt(0)} y2={yAt(0)} />
        {breakX != null && (
          <g ref={breakRef}>
            <rect className="trend-after" x={breakX} y={PAD.t} width={W - PAD.r - breakX} height={H - PAD.t - PAD.b} />
            <line className="trend-break" x1={breakX} x2={breakX} y1={PAD.t - 6} y2={H - PAD.b} />
            <text className="trend-tick" x={breakX} y={PAD.t - 9} textAnchor="middle">
              {changepoint.change_month}
            </text>
          </g>
        )}
        <path className="trend-line" ref={lineRef} d={path} />
      </svg>
      <div className="hero-split">
        <ChangeSplit
          // Begins as the line finishes drawing: one sequence, not two animations.
          delay={DUR.draw * 0.85}
          rows={[
            { label: "Your reviews", note: "plain before and after", value: changepoint.raw_delta },
            { label: "The market", note: "other properties, same months", value: changepoint.market_delta },
            { label: "Yours alone", note: "after taking the market out", value: changepoint.delta, verdict: true },
          ]}
        />
      </div>
      <figcaption>
        Mean sentiment per month on a scale from −1 to +1, and the shift the test found at{" "}
        {changepoint.change_month}.{synthetic ? " SYNTHETIC data: a generated property, not a real hotel." : ""}
      </figcaption>
    </figure>
  );
}
