# Hackathon Build Plan — Cluster Review Intelligence (G5)

**Team:** Anubhav `[A]` · Purvansh `[P]` · Archit `[R]`
**Window:** Day 0 (today, 10 Oct) → Day 1 (tomorrow, 11 Oct) → Hackathon (24 h)
**Goal:** a live, polished dashboard that answers *"am I behind my cluster, since
when, and is it just me or the whole market?"* — backed by honest numbers.

> Tick only **your own** boxes. Owner tags: `[A]` Anubhav · `[P]` Purvansh · `[R]` Archit · `[ALL]` everyone.

---

## 0. How to use this document

1. Read §1–§3 **before writing any code**. §3 is what stops the three of you
   colliding.
2. Work top-down through your own column in §4 → §5 → §6.
3. At every **integration window**, stop, merge, and make sure `main` still runs.
4. If something here turns out to be wrong, change *this file* first, then the code.

---

## 1. Decisions (locked — do not relitigate during the build)

| Decision | Choice | Why |
|---|---|---|
| UI | **Streamlit + Plotly** | All three of us are Python. No API layer ⇒ no integration risk, which is the #1 cause of broken hackathon demos. A themed Streamlit app looks polished and frees our scarcest resource (time) for the *insight*, not plumbing. |
| Backend | **In-process Python** (`src/cri`) | No service to deploy or debug. Streamlit calls the library directly. |
| Charts | **Plotly** | Interactive (hover, zoom) — reads as a product, not a notebook. |
| Hosting | **Streamlit Community Cloud** | Free, deploys from GitHub in minutes, gives a public link for judges. |
| Model backend | **Stretch only** | Rule/lexicon baseline is explainable and already works. A transformer is a *nice-to-have*, never a blocker. |
| Data | Synthetic (shipped) **+** real CSVs if legitimately obtained | See §8 — scraping is forbidden by `CLAUDE.md`. |

**Explicitly out of scope:** React/FastAPI, user accounts, databases, real-time
ingestion, mobile app. If anyone proposes these, the answer is no.

---

## 2. What actually wins this (build in this order)

Judges reward a sharp story over feature count. Priority order:

1. **The core insight, visible in 10 seconds** — "4.1 means different things."
   Market-wide vs property-specific is our differentiator. *Nothing else matters
   more than this landing clearly.*
2. **A working live demo** on a public URL. Working beats feature-rich.
3. **Hinglish / Devanagari handling** — locally relevant, judges in an India
   tourism context will test it. Have a live example ready to type in.
4. **Actionable output** — not "your food score is 0.21" but *"fix food first;
   it's your biggest gap vs the cluster and it started in June."* → `priority_actions`.
5. **Honest evaluation** — real F1 with a confusion matrix and an error analysis.
   Saying "we're 0.71 macro F1 and here's where we fail" beats a vague claim.
   **Never invent a number** (`CLAUDE.md` rule 1).

Secondary but cheap: the destination (tourism board) view — it proves a second
user persona and widens the market story.

---

## 3. Parallelism rules — read this twice

The only way three people ship in ~3 working days without stepping on each other
is **disjoint file ownership** plus **a frozen contract**.

### 3.1 File ownership map

> **Rule: you only edit files you own.** Need a change in someone else's file?
> Message them. Do not edit it yourself, even for a one-liner.

| Path | Owner | Everyone else |
|---|---|---|
| `src/cri/api.py` *(the contract)* | `[A]` | **read-only** — consume it, never edit |
| `src/cri/benchmark.py`, `changepoint.py`, `insights.py`, `classify.py`, `normalize.py`, `pipeline.py` | `[A]` | do not edit |
| `app/**` *(entire Streamlit app)* | `[P]` | do not edit |
| `eval/**`, `scripts/**`, `.github/**`, `data/**` | `[R]` | do not edit |
| `src/cri/loader.py`, `schema.py`, `sources.py` | `[R]` | do not edit |
| `src/cri/resources/aspects.yaml`, `lexicon.yaml` *(tuning config)* | `[R]` | do not edit |
| `tests/test_benchmark.py`, `test_insights.py`, `test_api.py` | `[A]` | — |
| `tests/test_app_smoke.py` | `[P]` | — |
| `tests/test_eval.py`, `test_schema_loader.py`, `test_sources.py` | `[R]` | — |
| `pyproject.toml` | `[R]` **sole editor** | request deps in the group chat |
| `README.md` | `[A]`, and only at the end | — |
| `CONTEXT.md` | `[A]` | — |
| `docs/HACKATHON_PLAN.md` *(this file)* | shared | tick **only your own** boxes |

**Why `lexicon.yaml` exists:** the sentiment word lists currently live inside
`classify.py`, which `[A]` owns. Pulling them into a YAML file lets `[R]` tune
them from error analysis without ever touching `[A]`'s code. This extraction is a
Day-0 task.

### 3.2 The frozen contract — `src/cri/api.py`

`[P]` builds the **entire dashboard** against this facade and never imports
anything else from `cri`. `[A]` is free to rewrite internals as long as these
signatures hold.

```python
# src/cri/api.py — FROZEN after Day 0. Changes need all three to agree.
from dataclasses import dataclass
import pandas as pd

@dataclass
class ClusterData:
    reviews: pd.DataFrame      # schema-validated raw reviews
    labelled: pd.DataFrame     # property_id, date, aspect, sentiment, sentence
    is_synthetic: bool
    source_name: str           # shown in the UI banner

def load_cluster(path=None, *, synthetic=True, seed=42) -> ClusterData: ...
def list_properties(d: ClusterData) -> list[str]: ...
def list_aspects() -> list[str]: ...
def date_range(d: ClusterData) -> tuple[pd.Timestamp, pd.Timestamp]: ...

# aspect, mean, ci_low, ci_high, n, cluster_mean, diff, flag  (flag: lead|lag|on_par)
def property_scorecard(d: ClusterData, property_id: str) -> pd.DataFrame: ...

# index=property_id, columns=aspect, values=mean sentiment
def cluster_matrix(d: ClusterData) -> pd.DataFrame: ...

# month, mean, n   (one property-aspect monthly series)
def trend(d: ClusterData, property_id: str, aspect: str) -> pd.DataFrame: ...

# property_id, aspect, change_month, delta, direction
def changepoints(d: ClusterData, property_id=None, aspect=None) -> pd.DataFrame: ...

# aspect, scope (market-wide|property-specific), fraction, n_properties, properties
def market_scope(d: ClusterData) -> pd.DataFrame: ...

# aspect, cluster_mean, n, pct_negative, scope   (tourism-board view)
def destination_summary(d: ClusterData) -> pd.DataFrame: ...

# aspect, gap, volume, impact_score, started, rationale   -> "fix this first"
def priority_actions(d: ClusterData, property_id: str, top_n: int = 5) -> pd.DataFrame: ...

# filtered raw reviews for the explorer page
def search_reviews(d: ClusterData, property_id=None, aspect=None, sentiment=None,
                   start=None, end=None, query: str | None = None) -> pd.DataFrame: ...
```

**Day-0 unblock rule:** `[A]` pushes `api.py` with *working or stubbed* returns
(correct columns, plausible shapes) **within the first 2 hours**. From that moment
`[P]` is never blocked, even if the internals are still being written.

### 3.3 Git protocol

- Branch per task: `feat/<name>-<topic>` (e.g. `feat/purvansh-property-page`).
- `git pull --rebase origin main` **before** you start and **before** you push.
- Small commits, Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`).
- Never push to `main`. PR → `[A]` merges.
- Before any PR: `python -m pytest` and `python -m ruff check .` must pass.
- Never commit `data/raw/**`, `.env`, or anything with personal data.

### 3.4 Integration windows (non-negotiable)

Everyone stops, merges to `main`, and confirms the app still launches.

| When | What must be true after it |
|---|---|
| Day 0, end | `api.py` contract pushed; `app/` skeleton runs; `eval/` scaffold exists |
| Day 1, midday | Each track's core path works in isolation |
| Day 1, end | **App runs end-to-end on synthetic data from `main`** |
| Hackathon H+5 | Real data (or confirmed fallback) wired in |
| Hackathon H+11 | **Feature freeze.** Only bugfixes and polish after this |
| Hackathon H+18 | Backup demo video recorded |

---

## 4. Phase 0 — Day 0 (today): lock the contract

Short, high-leverage session. Aim ~3 h. **Nothing here is optional** — it's what
makes Day 1 parallel.

### `[ALL]` Together first (~30 min)
- [ ] Read §1–§3 of this doc out loud; agree the ownership map.
- [ ] Agree the contract in §3.2 — change it *now* if needed, then freeze it.
- [ ] Exchange GitHub handles; everyone can push branches and open PRs.
- [ ] Agree integration-window times in real clock hours and put them in a group chat.

### `[A]` Anubhav — unblock everyone
- [ ] Create `src/cri/api.py` implementing §3.2 on top of existing modules.
      Stub anything not ready (`priority_actions`, `destination_summary`) with
      correct columns and a `# TODO` — **push within 2 h**.
- [ ] Extract the sentiment lexicon from `classify.py` → `src/cri/resources/lexicon.yaml`;
      `classify.py` loads it. Hand ownership of the YAML to `[R]`.
- [ ] Add `tests/test_api.py` asserting every function returns the documented columns.
- [ ] Tell `[P]` and `[R]` the moment `api.py` is on `main`.

### `[P]` Purvansh — app skeleton
- [ ] `app/Home.py` + `app/pages/1_Property.py … 5_Explorer.py` (empty shells that run).
- [ ] `app/theme.py` — navy `#0B2545`, amber `#F4A259`, teal `#2A9D8F`; `.streamlit/config.toml`.
- [ ] Sidebar shell: data-source selector, property selector, date range.
- [ ] Prominent **SYNTHETIC** banner component (shows when `d.is_synthetic`).
- [ ] Confirm `streamlit run app/Home.py` launches with placeholder content.
- [ ] *(Use stubs/hardcoded frames until `api.py` lands — do not wait.)*

### `[R]` Archit — data + eval scaffold
- [x] Merge the Scorecard CI fix (PR #11) — **done**, `main` is green-ready.
- [ ] Enable branch protection on `main` (require PR + CI) — see `docs/hardening.md`.
- [ ] `eval/` scaffold: `eval/labels_schema.md`, `eval/score.py` (empty CLI), `eval/labelled/.gitkeep`.
- [ ] `src/cri/sources.py` — adapter that maps an arbitrary team CSV's columns onto our schema.
- [ ] **Start the real-data hunt** (§8). This has the longest lead time — begin today.
- [ ] Add `matplotlib`/`plotly`/`streamlit` deps to `pyproject.toml` (you're sole editor).

---

## 5. Phase 1 — Day 1 (tomorrow): parallel build

Three tracks, zero file overlap. This is the big push.

### `[A]` Anubhav — analytics core
- [ ] **Bootstrap CIs** in `benchmark.py`, replacing the normal approximation;
      `property_scorecard` returns real `ci_low`/`ci_high`. Lead/lag flags only when the CI supports it.
- [ ] **`priority_actions`** (`src/cri/insights.py`) — rank aspects by
      `impact = gap_to_cluster × mention_volume`, attach the changepoint month as
      `started`, and generate a one-line `rationale` string. *This is our killer feature.*
- [ ] **`destination_summary`** — cluster-level aggregate for the tourism-board page.
- [ ] **Reduce changepoint false positives** — require the shift to exceed a
      significance threshold, not just a fixed delta (see `methodology.md` §6).
- [ ] Make `market_scope` robust when a cluster has few properties.
- [ ] Tests for each of the above; keep `pytest` + `ruff` green.
- [ ] *Stretch:* PELT via `ruptures`; a transformer `Classifier` behind a flag.

### `[P]` Purvansh — the dashboard (biggest single chunk)
- [ ] **Property view** — aspect bars vs cluster (with CI error bars), trend line
      with changepoint marker, and the **priority-actions table** up top. This page
      *is* the demo; make it the best one.
- [ ] **Cluster heatmap** — property × aspect, diverging colour scale, hover detail.
- [ ] **Market-wide vs property-specific quadrant** — the money chart for §2.1.
      Make the two regions visually unmistakable and annotated.
- [ ] **Destination view** — tourism-board aggregate, "top cluster-wide issues".
- [ ] **Review explorer** — filters (property/aspect/sentiment/date) + text search,
      showing the matched clause so the classification is auditable.
- [ ] Empty states, error states, spinners for slow calls.
- [ ] `@st.cache_data` on `load_cluster` and the heavy aggregations.
- [ ] "Download CSV" on each table.
- [ ] `tests/test_app_smoke.py` — imports every page module (catches syntax/import breaks in CI).

### `[R]` Archit — data, evaluation, ops
- [ ] Finish `sources.py` + a column-mapping UI/config so a new CSV loads without code changes.
- [ ] **`eval/score.py`** — macro + per-aspect precision/recall/F1, confusion
      matrix, and an error-analysis table (sarcasm / mixed aspects / very short reviews).
- [ ] Labelling pack: template, a written 1-page guideline, and a split so three
      people can label disjoint slices without overlap.
- [ ] **Deploy to Streamlit Community Cloud** from `main`; share the public URL.
- [ ] Add the app smoke test + (stretch) CodeQL to CI.
- [ ] Keep `docs/TODO_RESULTS.md` current — every `TBD` tracked.

### `[ALL]` End of Day 1
- [ ] Integration window: merge everything, `streamlit run app/Home.py` works from a
      fresh clone of `main`.
- [ ] 10-minute dry run of the demo. Note what's confusing.

---

## 6. Phase 2 — Hackathon (24 h)

Hour-blocked. `H+0` is when the clock starts.

| Hours | `[A]` Anubhav | `[P]` Purvansh | `[R]` Archit |
|---|---|---|---|
| **H0–H1** | `[ALL]` Kickoff: pull `main`, smoke-test the deployed app, re-read §2, confirm the story |||
| **H1–H5** | Tune insight engine on real data | Polish Property + Quadrant pages | **Wire in real data** (or trigger fallback §9) |
| **H5** | `[ALL]` **Integration window** — real data (or fallback) is live |||
| **H5–H8** | Fix whatever real data breaks | Destination + Explorer pages | Run `eval/score.py`, produce first real numbers |
| **H8–H9** | `[ALL]` **Labelling sprint** — 1 h, three disjoint slices, ~250 reviews total |||
| **H9–H11** | Tune thresholds from error analysis | Chart polish, annotations, captions | Final eval numbers → README table (replace `TBD`s **with real values only**) |
| **H11** | `[ALL]` **FEATURE FREEZE** — bugfixes and polish only from here |||
| **H11–H15** | Verify every number shown is real | Visual polish, copy, empty states | README, screenshots, `docs/` updates |
| **H15–H18** | `[ALL]` Demo rehearsal ×2. Fix only what breaks the demo |||
| **H18** | `[R]` **Record a backup demo video** (insurance against live failure) |||
| **H18–H22** | `[ALL]` Buffer. Stretch goals *only* if everything above is done |||
| **H22–H24** | `[ALL]` Final rehearsal, tag a release, submit |||

---

## 7. Definition of done (per task)

A task is done only when **all** of these hold:

- [ ] `python -m pytest` passes
- [ ] `python -m ruff check .` is clean
- [ ] It works from a **fresh clone** of `main`, not just your machine
- [ ] Docs/README updated if behaviour changed
- [ ] No `TBD` silently replaced by a made-up number
- [ ] Synthetic data/figures still labelled `SYNTHETIC`
- [ ] No secrets, no personal data, no scraped content

---

## 8. Real data — the long-pole risk

`CLAUDE.md` rule 3 forbids scraping and bypassing platform terms. Legitimate routes,
in order of preference:

1. **Open datasets** with a licence permitting research use (verify the licence and
   record it in `docs/CREDITS.md`).
2. **Data the tourism board / a partner property gives us** in writing.
3. **Our own manual collection** of a small set, within platform terms.
4. **Fallback: stay synthetic.** Clearly labelled, and we say so on the slide.

Whatever the source: drop reviewer identity at ingestion, anonymise property names
(`Property A…`), and record provenance in `docs/CREDITS.md`.

> `[R]` owns this and starts Day 0, because it has the longest lead time and it is
> the single most likely thing to not arrive in time.

---

## 9. Risk register

| # | Risk | Likelihood | Fallback |
|---|---|---|---|
| 1 | **No real data in time** | High | Demo on synthetic, labelled honestly. Frame the pipeline as source-agnostic and show the loader accepting any schema-conforming CSV. Judges respect honesty more than a fake dataset. |
| 2 | **Merge conflicts / overwritten work** | Medium | §3.1 ownership map + integration windows. If two people need one file, one of them waits. |
| 3 | **Over-scoping** | High | H+11 feature freeze. Everything in "stretch" is explicitly cuttable. |
| 4 | **Deployment breaks on demo day** | Medium | Backup video at H+18, plus a local `streamlit run` rehearsed as plan C. |
| 5 | **Eval numbers come out weak** | Medium | Report them honestly with an error analysis. A measured 0.6 F1 with insight into *why* beats an unverifiable claim. |
| 6 | **Someone gets blocked** | Medium | The §3.2 contract + Day-0 stubs mean no one hard-blocks on anyone else. |
| 7 | **Live Hinglish demo input fails** | Low | Pre-test 5 example strings and keep them in the demo script. |

---

## 10. Demo script (judge-facing, ~3 min)

Rehearse until this is muscle memory.

1. **Hook (20 s)** — "This property averages 4.1 stars. So does this one. One of
   them has a serious problem. A star average can't tell you which."
2. **Property view (40 s)** — open Property F. Priority actions say *fix Food
   first*. The trend shows it fell off a cliff in June.
3. **The differentiator (40 s)** — "But is that *them*, or the whole market?"
   Open the quadrant. Food = property-specific → a competitive gap they own.
   Room = market-wide → every property gets cold-room complaints each December.
   **"Same chart, two completely different actions."**
4. **Hinglish (20 s)** — type a mixed Hinglish/Devanagari review in the explorer;
   show the aspect + sentiment picked up correctly.
5. **Destination view (20 s)** — "And for a tourism board, this is the cluster-wide
   view: heating is a destination problem, not a hotel problem."
6. **Honesty (20 s)** — show the evaluation table and the limitations section.
   "Here's our measured F1, and here's exactly where we fail."
7. **Close (10 s)** — one line on what we'd build next.

---

## 11. Honesty guardrails (non-negotiable, from `CLAUDE.md`)

These apply to all three of us, in code, docs, slides, and anything we say to judges:

1. **Never fabricate** results, accuracy, dataset sizes, quotes, or statistics.
   Unknown ⇒ `TBD` in `docs/TODO_RESULTS.md`.
2. **Label synthetic data** `SYNTHETIC` in filenames, figures, captions, and the UI.
3. **No scraping**, no bypassing logins/rate limits.
4. **No personal data**; anonymise properties in anything public.
5. **No secrets in git**; config via env vars.
6. **No unlicensed images**; record every asset in `docs/CREDITS.md`.

If a number is on a slide, one of us must be able to point at the command that
produced it.

---

## 12. Quick reference

```bash
python -m pip install -e ".[dev]"     # setup
python -m pytest                      # tests
python -m ruff check .                # lint
streamlit run app/Home.py             # the dashboard
python scripts/demo.py                # CLI demo
python scripts/make_figures.py        # regenerate README figures
python -m cri.generate --out data/sample/synthetic_reviews.csv
```
