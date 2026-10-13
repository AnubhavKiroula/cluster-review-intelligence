# System design

## Scope

**One user: the hotel or homestay owner.** One question, before a fix and after it:
*when my reviews get worse on an aspect, is it my problem or the whole market's?*
Answering it needs the cluster of nearby properties; one hotel's reviews cannot.

- `src/cri` is a Python library behind the `cri.api` facade.
- Next.js (`web/`, static export) is the only frontend: four pages (`/property`,
  `/market`, `/fix-check`, `/explorer`) plus home, all reading a static JSON
  snapshot exported from `cri.api`.
- A small FastAPI service (`cri.server`) serves one feature: the explorer's live
  *Try your own review*. The site works without it.
- The same analysis also gives a tourism board a destination view
  (`destination_summary`); the earlier travel layer (`cri.travel`, its pages and
  endpoints) was removed on 2026-10-13 and is preserved at the git tag
  `travel-layer-v1`.

```mermaid
flowchart LR
  subgraph Browser["Browser: Next.js static site (web/)"]
    PAGES["Pages<br/>property, market,<br/>fix-check, explorer"]
    TRY["Explorer: try your own review"]
  end
  SNAP[("public/data/cluster.synthetic.json<br/>public/data/fixcheck.synthetic.json")]
  EXP["web/scripts/export_snapshot.py"]
  subgraph API["FastAPI: cri.server (optional)"]
    EP["GET /health<br/>POST /reviews/classify"]
  end
  subgraph Core["Python library: src/cri"]
    CRI["cri.api<br/>review intelligence"]
    CLS["classifiers<br/>rule | learned | transformer"]
  end
  RES[("resources<br/>aspects.yaml, lexicon.yaml,<br/>models/sentiment_open.npz")]
  CRI --> EXP --> SNAP
  PAGES --> SNAP
  TRY -- "fetch NEXT_PUBLIC_API_BASE_URL" --> EP
  EP --> CRI
  CRI --> CLS --> RES
```

## Components

| Component | Responsibility | Key files |
|---|---|---|
| Review core | Ingest and validate reviews (PII dropped), normalise Hinglish/Devanagari, classify aspect+sentiment, benchmark, changepoints, market scope, priorities with *whose problem*, fix check | `src/cri/{schema,loader,sources,normalize,classify,pipeline,benchmark,changepoint,insights,intervention,api}.py` |
| Learned sentiment | Trained linear model plugged into the hybrid classifier (opt-in) | `src/cri/learned_backend.py`, `scripts/train_sentiment.py`, `scripts/prepare_region_reviews.py` |
| Snapshot exporter | Dumps every page's data from `cri.api`, plus the precomputed fix-check grid | `web/scripts/export_snapshot.py` |
| HTTP API | Live classification only: input validation, CORS | `src/cri/server.py` |
| Web pages | `/property /market /fix-check /explorer` and home | `web/app/**/page.tsx` |
| Web client | `POST` helper with timeout, used only by the explorer | `web/lib/api.ts` |

**Dependency direction:** pages → snapshot ← exporter → `cri.api` → core. The
explorer's live box → API → `cri.api.classify_text`. The scoring logic lives only in
Python; TypeScript only renders it.

## Snapshot (`cluster.synthetic.json`)

| Key | Contents | Read by |
|---|---|---|
| `meta` | SYNTHETIC flag, source, properties, aspects, date range, review count | every page |
| `per_property` | scorecard, `priority_actions` (with `whose_problem`), trends, changepoints | `/property` |
| `market_scope` | scope per aspect with its pattern and participating properties | `/market`, `/property` |
| `destination_summary` | cluster-wide level and negative share per aspect | `/market` (y axis) |
| `market_headline` | worst market-wide aspect by negative share, or `null` | home, `/market` |
| `reviews`, `mentions` | raw reviews and classified clauses | `/explorer` |

`fixcheck.synthetic.json` holds every "Did my fix work?" result (property × aspect ×
month) and is loaded only by `/fix-check`.

## Whose problem is it? (`priority_actions.whose_problem`)

Each priority is tested **for that property**. It is never joined from
`market_scope.scope` by aspect: that label describes the cluster, not each row.

```mermaid
flowchart TD
  P["Priority row<br/>(property, aspect)"] --> B{"Fewer than 3 properties<br/>review the aspect?"}
  B -- Yes --> NT["not tested"]
  B -- No --> D{"Market-adjusted<br/>decline (changepoint)?"}
  D -- Yes --> Y1["yours alone"]
  D -- No --> M{"Takes part in a market-wide<br/>pattern on this aspect?"}
  M -- No --> Y2["yours alone"]
  M -- Yes --> R["Re-test the lag with those<br/>pattern months set aside"]
  R --> F{"Enough reviews left?"}
  F -- No --> NT2["not tested"]
  F -- Yes --> L{"Still a lag?"}
  L -- Yes --> Y3["yours alone<br/>(the pattern itself is everyone's)"]
  L -- No --> E["everyone's"]
```

`whose_detail` states the reason. On the SYNTHETIC sample, Property F's Food decline
is *yours alone* (the market moved +0.01 while F dropped 1.22), and Property D's Room
gap is *yours alone* too: D is still 0.36 below the market outside the December dip
that all 12 properties share.

## Storage

- **No database.** All state is versioned files: YAML resources, the packaged model
  `.npz`, the JSON snapshots, and gitignored local data under `data/raw/`.
- The API holds no data: it builds the classifier on first use and loads no cluster.

## Design decisions and trade-offs

| Decision | Why | Trade-off |
|---|---|---|
| One user, four pages | Mentors found the earlier four-audience scope unfocused; the moat is the cluster comparison | Traveller, seller and region features are gone (recoverable from `travel-layer-v1`) |
| Static snapshot for every page | No backend to deploy or break; deep links work on any static host | Analytics changes need a re-export and commit |
| API only for live classify | Typed text must be classified by the tested Python classifier, not re-implemented in TypeScript | A second process, needed only for that box |
| *Whose problem* derived per property | A cluster-level "market-wide" label would wrongly excuse a property that lags all year | One extra benchmark re-test per lagging row in a market-wide aspect |
| Trained model opt-in, rules default | The model wins on its own domain's text but loses clause-level on the SYNTHETIC patterns (AI_MODEL.md) | The better hill-review model stays local because of data provenance |
| `.npz` model without pickle | Loading a model never executes code | Inference re-implemented in numpy, covered by a parity test |
| No auth | Demo with SYNTHETIC data only | Must be added before any real property data (SRS NFR-SEC) |

## Scalability

- **Static front end:** deploys to any CDN. The main snapshot is about 2.6 MB and
  loads once per visit; the fix-check grid loads only on that page.
- **API:** stateless, one classification per request; scales horizontally.
- **When data grows:** precompute snapshots per cluster nightly, and split the
  explorer corpus out of the main snapshot before it dominates its size.
