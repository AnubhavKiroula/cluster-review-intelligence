"use client";

// Motion for the site, in one place.
//
// Three rules hold everywhere:
//   1. The DOM already holds the final state. Every helper animates *towards* what
//      JSX rendered, so a reader who blocks JavaScript, loses the GSAP chunk or asks
//      for reduced motion sees the finished, correct figure — never a blank one.
//   2. Motion carries meaning: a bar grows because the quantity grows, a number
//      counts because it is a count, the split resolves because that is the product's
//      argument. Nothing fades in merely to arrive.
//   3. `prefers-reduced-motion: reduce` skips the animation entirely rather than
//      shortening it.
//
// GSAP is imported dynamically so it never blocks first paint, and the whole
// dependency is reachable from this file alone (see web/README.md).
import { useEffect, useRef, useState } from "react";

type Gsap = typeof import("gsap")["gsap"];

let gsapPromise: Promise<Gsap | null> | null = null;

/** The GSAP core, loaded once and shared; null if it cannot be loaded. */
export function loadGsap(): Promise<Gsap | null> {
  if (!gsapPromise) {
    gsapPromise = import("gsap")
      .then((m) => m.gsap)
      // A failed chunk must not break the page: callers keep the rendered state.
      .catch(() => null);
  }
  return gsapPromise;
}

export function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/** Shared timings, so durations are chosen per distance rather than copied. */
export const DUR = { fast: 0.18, base: 0.36, slow: 0.6, draw: 1.1 } as const;

/**
 * True once `ref` has been on screen. Used instead of GSAP's ScrollTrigger: Plotly
 * measures its charts after mount and changes section heights, which invalidates
 * ScrollTrigger's cached positions unless it is refreshed on every chart resize.
 */
export function useInView<T extends Element>(
  ref: React.RefObject<T>,
  margin = "0px 0px -10% 0px",
): boolean {
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || seen) return;
    // No IntersectionObserver (or reduced motion): treat it as already seen, so
    // callers settle on the final state at once.
    if (typeof IntersectionObserver === "undefined" || prefersReducedMotion()) {
      setSeen(true);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setSeen(true);
          io.disconnect();
        }
      },
      { rootMargin: margin },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [ref, seen, margin]);
  return seen;
}

/**
 * Counts an element's text up to `value` the first time it is on screen, and again
 * whenever the value changes — the change is the point, so a new number is counted
 * rather than swapped. `format` must render the final text, since it also produces
 * every intermediate frame.
 */
export function useCountUp(
  value: number | null | undefined,
  format: (v: number) => string,
): React.RefObject<HTMLSpanElement> {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref);
  // Count from the previous value on a change, so a correction reads as a move.
  const from = useRef(0);
  // Callers pass an inline formatter; held in a ref, its identity cannot restart the
  // count on an unrelated re-render.
  const fmt = useRef(format);
  fmt.current = format;

  useEffect(() => {
    const el = ref.current;
    if (!el || !inView || value == null || Number.isNaN(value)) return;
    const target = value;
    const start = from.current;
    const format = fmt.current;
    from.current = target;
    if (prefersReducedMotion() || start === target) return;

    let tween: { kill(): void } | null = null;
    let live = true;
    loadGsap().then((gsap) => {
      if (!gsap || !live || !ref.current) return;
      const box = { v: start };
      tween = gsap.to(box, {
        v: target,
        duration: DUR.slow,
        ease: "power2.out",
        onUpdate: () => {
          if (ref.current) ref.current.textContent = format(box.v);
        },
        // Land on the exact rendered text, never on a rounding artefact.
        onComplete: () => {
          if (ref.current) ref.current.textContent = format(target);
        },
      });
    });
    return () => {
      live = false;
      tween?.kill();
      if (ref.current) ref.current.textContent = format(target);
    };
  }, [inView, value]);

  return ref;
}

/**
 * Grows the bars of a change split from the shared zero line, in reading order, so
 * the figure is read as an argument: this is what your reviews did, this is what the
 * market did, this is what is left for you. Keyed on `signature` so switching
 * property or month replays it with the new numbers.
 */
export function useGrowBars(signature: string, delay = 0): React.RefObject<HTMLDivElement> {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref);

  useEffect(() => {
    const root = ref.current;
    if (!root || !inView) return;
    const bars = Array.from(root.querySelectorAll<HTMLElement>("[data-bar]"));
    if (bars.length === 0 || prefersReducedMotion()) return;

    let tween: { kill(): void } | null = null;
    let live = true;
    loadGsap().then((gsap) => {
      if (!gsap || !live) return;
      // scaleX, not width: width would lay out every frame.
      tween = gsap.fromTo(
        bars,
        { scaleX: 0 },
        {
          scaleX: 1,
          duration: DUR.base,
          ease: "power2.out",
          stagger: 0.08,
          // Non-zero only in the home figure, where the bars follow the line drawing.
          delay,
          // Clear the transform so a later re-render inherits no inline scale.
          clearProps: "transform",
        },
      );
    });
    return () => {
      live = false;
      tween?.kill();
      for (const b of bars) b.style.transform = "";
    };
  }, [inView, signature, delay]);

  return ref;
}

/**
 * Reveals a container's direct children once, staggered. Deliberately used on one
 * group per page at most: a fade-up on every section is decoration, not meaning.
 */
export function useStaggerIn<T extends HTMLElement>(): React.RefObject<T> {
  const ref = useRef<T>(null);
  const inView = useInView(ref);

  useEffect(() => {
    const root = ref.current;
    if (!root || !inView || prefersReducedMotion()) return;
    const items = Array.from(root.children) as HTMLElement[];
    if (items.length === 0) return;

    let tween: { kill(): void } | null = null;
    let live = true;
    loadGsap().then((gsap) => {
      if (!gsap || !live) return;
      tween = gsap.from(items, {
        opacity: 0,
        y: 12,
        duration: DUR.base,
        ease: "power1.out",
        stagger: 0.07,
        clearProps: "opacity,transform",
      });
    });
    return () => {
      live = false;
      tween?.kill();
      for (const i of items) {
        i.style.opacity = "";
        i.style.transform = "";
      }
    };
  }, [inView]);

  return ref;
}
