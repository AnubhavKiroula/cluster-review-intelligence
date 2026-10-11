"use client";

import { useMemo, useState } from "react";
import { sentimentLabel, useData, type Mention, type Review } from "@/lib/data";
import { DownloadCsv, ErrorState, Info, Loading, SyntheticBanner, Table } from "@/components/ui";

const ANY = "__any__";
const MAX_ROWS = 300;

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

  const rows = useMemo<Row[]>(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
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
  }, [data, prop, aspect, sentiment, query]);

  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading />;

  return (
    <>
      <h1>🔍 Review explorer</h1>
      <SyntheticBanner />
      <p className="lede">
        Every classification is auditable: the <strong>matched clause</strong> shows which words
        drove the aspect and sentiment. Try a mixed Hinglish/Devanagari phrase in the search box.
      </p>

      <div className="controls">
        <div className="field">
          <label htmlFor="f-prop">Property</label>
          <select id="f-prop" value={prop} onChange={(e) => setProp(e.target.value)}>
            <option value={ANY}>— any —</option>
            {data.meta.properties.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="f-aspect">Aspect</label>
          <select id="f-aspect" value={aspect} onChange={(e) => setAspect(e.target.value)}>
            <option value={ANY}>— any —</option>
            {data.meta.aspects.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="f-sent">Sentiment</label>
          <select id="f-sent" value={sentiment} onChange={(e) => setSentiment(e.target.value)}>
            <option value={ANY}>— any —</option>
            <option value="1">👍 positive</option>
            <option value="0">😐 neutral</option>
            <option value="-1">👎 negative</option>
          </select>
        </div>
        <div className="field" style={{ flex: 1 }}>
          <label htmlFor="f-q">Search review text</label>
          <input
            id="f-q"
            type="text"
            placeholder="e.g. khana accha tha lekin kamra ganda"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{ width: "100%" }}
          />
        </div>
      </div>

      <p className="caption">
        {rows.length.toLocaleString()} matched clause(s)
        {rows.length > MAX_ROWS ? ` (showing first ${MAX_ROWS})` : ""}.
      </p>

      {rows.length === 0 ? (
        <Info>No reviews match these filters. Loosen a filter or clear the search box.</Info>
      ) : (
        <>
          <Table
            rows={rows.slice(0, MAX_ROWS)}
            columns={[
              { key: "date", label: "Date", render: (r) => r.date.slice(0, 10) },
              { key: "property_id", label: "Property" },
              { key: "platform", label: "Platform" },
              { key: "rating", label: "Rating", align: "right" },
              { key: "aspect", label: "Aspect", render: (r) => r.aspect || "—" },
              { key: "sentiment", label: "Sentiment", render: (r) => sentimentLabel(r.sentiment) },
              { key: "sentence", label: "Matched clause" },
              { key: "text", label: "Full review" },
            ]}
          />
          <div style={{ marginTop: 10 }}>
            <DownloadCsv rows={rows} filename="search_results.csv" />
          </div>
        </>
      )}
    </>
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
