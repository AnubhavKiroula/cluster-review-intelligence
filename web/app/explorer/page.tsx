"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { postApi, type ApiError, type ClassifyResponse } from "@/lib/api";
import { syncQuery, useData, type Mention, type Review } from "@/lib/data";
import {
  DownloadCsv,
  ErrorState,
  Info,
  Loading,
  PageHeader,
  SectionHeading,
  SentimentTag,
  Table,
} from "@/components/ui";

const ANY = "__any__";
// Rows rendered per step: a few hundred table rows is already a long page.
const PAGE = 100;
const SENTIMENTS = ["1", "0", "-1"];

interface Row {
  date: string;
  property_id: string;
  platform: string;
  rating: number;
  aspect: string;
  sentiment: number | null;
  sentence: string;
  text: string;
}

export default function ExplorerPage() {
  const { data, error } = useData();
  const [prop, setProp] = useState(ANY);
  const [aspect, setAspect] = useState(ANY);
  const [sentiment, setSentiment] = useState(ANY);
  const [query, setQuery] = useState("");
  // Filtering ~11k clauses per keystroke would lag the input; the box updates at once
  // and the table follows when React has time.
  const deferredQuery = useDeferredValue(query);
  const [shown, setShown] = useState(PAGE);
  const [ready, setReady] = useState(false);

  // Deep link: /explorer/?property=Property%20F&aspect=Food&sentiment=-1&q=khana
  useEffect(() => {
    if (!data || ready) return;
    const q = new URLSearchParams(window.location.search);
    const pick = (v: string | null, options: string[]) => (v && options.includes(v) ? v : ANY);
    setProp(pick(q.get("property"), data.meta.properties));
    setAspect(pick(q.get("aspect"), data.meta.aspects));
    setSentiment(pick(q.get("sentiment"), SENTIMENTS));
    setQuery(q.get("q") ?? "");
    setReady(true);
  }, [data, ready]);

  // Keep the URL shareable, and start from the first page whenever the filters change.
  useEffect(() => {
    if (!ready) return;
    const named = (v: string) => (v === ANY ? "" : v);
    syncQuery({ property: named(prop), aspect: named(aspect), sentiment: named(sentiment), q: deferredQuery.trim() });
    setShown(PAGE);
  }, [ready, prop, aspect, sentiment, deferredQuery]);

  const rows = useMemo<Row[]>(() => {
    if (!data) return [];
    const q = deferredQuery.trim().toLowerCase();
    const aspectActive = aspect !== ANY;
    const sentActive = sentiment !== ANY;

    const reviewOk = (r: Review) =>
      (prop === ANY || r.property_id === prop) && (!q || r.text.toLowerCase().includes(q));

    const byId = new Map<number, Review>();
    for (const r of data.reviews) if (reviewOk(r)) byId.set(r.review_id, r);

    const mentionOk = (m: Mention) =>
      (!aspectActive || m.aspect === aspect) &&
      (!sentActive || m.sentiment === Number(sentiment));

    const out: Row[] = [];
    if (aspectActive || sentActive) {
      // Inner join: only reviews with a matching clause.
      for (const m of data.mentions) {
        if (!mentionOk(m)) continue;
        const r = byId.get(m.review_id);
        if (!r) continue;
        out.push(toRow(r, m));
      }
    } else {
      // Left join: keep reviews even if nothing was detected.
      const mentionsByReview = new Map<number, Mention[]>();
      for (const m of data.mentions) {
        if (!byId.has(m.review_id)) continue;
        const list = mentionsByReview.get(m.review_id);
        if (list) list.push(m);
        else mentionsByReview.set(m.review_id, [m]);
      }
      for (const r of byId.values()) {
        const ms = mentionsByReview.get(r.review_id);
        if (ms && ms.length) for (const m of ms) out.push(toRow(r, m));
        else out.push(toRow(r, null));
      }
    }
    out.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
    return out;
  }, [data, prop, aspect, sentiment, deferredQuery]);

  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading />;

  return (
    <>
      <PageHeader
        title="Review explorer"
        lede="Every score on this site comes from clauses in reviews. Check any of them, or paste a review of your own."
      />

      <TryYourOwnReview />

      <section className="tool-section">
        <SectionHeading
          title="Search the reviews"
          description="Filter by property, aspect, sentiment, or a phrase from the review text."
        />
        <div className="controls">
          <div className="field">
            <label htmlFor="f-prop">Property</label>
            <select id="f-prop" name="property" value={prop} onChange={(e) => setProp(e.target.value)}>
              <option value={ANY}>Any property</option>
              {data.meta.properties.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="f-aspect">Aspect</label>
            <select id="f-aspect" name="aspect" value={aspect} onChange={(e) => setAspect(e.target.value)}>
              <option value={ANY}>Any aspect</option>
              {data.meta.aspects.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="f-sent">Sentiment</label>
            <select id="f-sent" name="sentiment" value={sentiment} onChange={(e) => setSentiment(e.target.value)}>
              <option value={ANY}>Any sentiment</option>
              <option value="1">Positive</option>
              <option value="0">Neutral</option>
              <option value="-1">Negative</option>
            </select>
          </div>
          <div className="field grow">
            <label htmlFor="f-q">Search review text</label>
            <input
              id="f-q"
              name="q"
              type="search"
              placeholder="For example: kamra ganda…"
              autoComplete="off"
              spellCheck={false}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
        </div>
      </section>

      <p className="caption" aria-live="polite">
        {rows.length.toLocaleString()} matching {rows.length === 1 ? "clause" : "clauses"}
        {rows.length > shown ? `, showing the newest ${shown.toLocaleString()}` : ""}.
      </p>

      {rows.length === 0 ? (
        <Info>No reviews match these filters. Clear the search box or set a filter back to any.</Info>
      ) : (
        <>
          <Table
            caption="Matching review clauses"
            rows={rows.slice(0, shown)}
            columns={[
              { key: "date", label: "Date", render: (r) => <span className="nowrap">{r.date.slice(0, 10)}</span> },
              { key: "property_id", label: "Property", render: (r) => <span className="nowrap">{r.property_id}</span> },
              { key: "platform", label: "Platform" },
              { key: "rating", label: "Rating", align: "right" },
              { key: "aspect", label: "Aspect", render: (r) => r.aspect || "—" },
              { key: "sentiment", label: "Sentiment", render: (r) => <SentimentTag value={r.sentiment} /> },
              { key: "sentence", label: "Matched clause", wide: true },
              { key: "text", label: "Full review", wide: true },
            ]}
          />
          <div className="table-actions">
            {rows.length > shown && (
              <button type="button" className="btn btn-quiet" onClick={() => setShown((n) => n + PAGE)}>
                Show {Math.min(PAGE, rows.length - shown)} more
              </button>
            )}
            <DownloadCsv rows={rows} filename="search_results.csv" />
          </div>
        </>
      )}
    </>
  );
}

// Live classification needs the Python API (cri.server); the rest of this page does not.
function TryYourOwnReview() {
  const [text, setText] = useState("Khana accha tha lekin kamra ganda tha.");
  const [res, setRes] = useState<ClassifyResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    setErr(null);
    try {
      setRes(await postApi<ClassifyResponse>("/reviews/classify", { text }));
    } catch (e) {
      setErr((e as ApiError).message);
      setRes(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="tool-section try">
      <SectionHeading
        title="Try your own review"
        description="English, Hinglish or Devanagari. You get each aspect, its sentiment and the clause it came from."
      />
      <div className="controls">
        <div className="field grow">
          <label htmlFor="try-text">Review text</label>
          <input
            id="try-text"
            name="review"
            type="text"
            maxLength={2000}
            value={text}
            onChange={(e) => setText(e.target.value)}
            autoComplete="off"
            onKeyDown={(e) => e.key === "Enter" && text.trim() && !busy && run()}
          />
        </div>
        <button type="button" className="btn btn-primary" onClick={run} disabled={busy || !text.trim()}>
          {busy ? "Classifying…" : "Classify"}
        </button>
      </div>
      {err && (
        <div className="state error" role="alert">
          <p>
            <strong>The classifier did not answer</strong> ({err}).
          </p>
          <p>
            Live classification needs the API. Locally, start it with{" "}
            <code>uvicorn cri.server:app --port 8000</code>. The rest of the site works without it.
          </p>
        </div>
      )}
      {res &&
        (res.mentions.length === 0 ? (
          <Info>No aspect detected. The rule baseline only knows the cue words in aspects.yaml.</Info>
        ) : (
          <Table
            caption="Classified clauses"
            rows={res.mentions}
            columns={[
              { key: "aspect", label: "Aspect" },
              { key: "sentiment", label: "Sentiment", render: (r) => <SentimentTag value={r.sentiment} /> },
              { key: "sentence", label: "Clause", wide: true },
            ]}
          />
        ))}
      {res && <p className="caption">Classifier backend: {res.backend}.</p>}
    </section>
  );
}

function toRow(r: Review, m: Mention | null): Row {
  return {
    date: r.date,
    property_id: r.property_id,
    platform: r.platform,
    rating: r.rating,
    aspect: m?.aspect ?? "",
    sentiment: m ? m.sentiment : null,
    sentence: m?.sentence ?? "",
    text: r.text,
  };
}
