# API contracts

Two interfaces:

1. **HTTP API** (`src/cri/server.py`, FastAPI): one feature, the explorer's live
   *Try your own review*. Every other page reads the static snapshot, so the site
   works without it. Interactive OpenAPI docs at `http://localhost:8000/docs`.
2. **Python facade** (`cri.api`): the frozen contract in `docs/HACKATHON_PLAN.md`
   §3.2, unchanged except the additive changes listed below.

All examples are real responses captured on 2026-10-13 with FastAPI's `TestClient`
against `cri.server.create_app()` (default `rule` backend).

## Running

```bash
python -m pip install -e ".[api]"
uvicorn cri.server:app --port 8000
```

| Env var | Default | Effect |
|---|---|---|
| `CRI_API_CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Browser origins allowed (comma-separated). GET/POST only, `Content-Type` header only, no credentials. |
| `CRI_MODEL_BACKEND` | `rule` | Classifier for `/reviews/classify`: `rule`, `learned`, `transformer` |
| `CRI_LEARNED_MODEL_PATH` | packaged open model | Model file for the `learned` backend |

The server loads no review data; the classifier is built on first use.

## Endpoints

| Method + path | Input (limits) | Returns |
|---|---|---|
| `GET /health` | — | status and classifier backend |
| `POST /reviews/classify` | `{"text": str}` (1–2,000 chars) | backend name + one mention per detected aspect, with its clause |

Any other path returns `404 {"detail": "Not Found"}`; the travel endpoints were
removed with the travel layer (tag `travel-layer-v1`).

### `GET /health`

```json
{"status": "ok", "classifier": "rule"}
```

### `POST /reviews/classify`

```json
// request
{"text": "Khana accha tha lekin kamra ganda tha."}
// response 200
{"backend": "rule",
 "mentions": [{"aspect": "Food", "sentiment": 1, "sentence": "khana accha tha"},
              {"aspect": "Room", "sentiment": -1, "sentence": "kamra ganda tha"},
              {"aspect": "Cleanliness", "sentiment": -1, "sentence": "kamra ganda tha"}]}
```

```json
// request
{"text": "कमरा साफ़ था और view zabardast tha."}
// response 200
{"backend": "rule",
 "mentions": [{"aspect": "Room", "sentiment": 1, "sentence": "कमरा साफ़ था और view zabardast tha"},
              {"aspect": "Location", "sentiment": 1, "sentence": "कमरा साफ़ था और view zabardast tha"},
              {"aspect": "Cleanliness", "sentiment": 1, "sentence": "कमरा साफ़ था और view zabardast tha"}]}
```

- `sentiment` ∈ `-1 | 0 | 1`; `sentence` is the normalised clause the label came from.
- No aspect detected → `200 {"backend": "rule", "mentions": []}`
  (request `{"text": "nothing to see"}`).
- The result is identical to `cri.api.classify_text(text)` (pinned by
  `tests/test_server.py`).

### Errors (FastAPI validation, `422`)

```json
// {"text": ""}
{"detail": [{"type": "string_too_short", "loc": ["body", "text"],
             "msg": "String should have at least 1 character", "input": "",
             "ctx": {"min_length": 1}}]}
// {"text": "<2,001 characters>"}   ("input" echoes the text; omitted here)
{"detail": [{"type": "string_too_long", "loc": ["body", "text"],
             "msg": "String should have at most 2000 characters",
             "ctx": {"max_length": 2000}}]}
```

### CORS

| Preflight `Origin` | Result |
|---|---|
| `http://localhost:3000` (allowed) | `200`, `access-control-allow-origin: http://localhost:3000`, `access-control-allow-methods: GET, POST` |
| `http://evil.example` (not listed) | `400 Disallowed CORS origin`, no `access-control-allow-origin` header |

## Python facade changes (`cri.api` and friends)

- **`priority_actions` → `whose_problem`, `whose_detail`** (2026-10-13, additive; no
  column removed or renamed). `whose_problem` ∈ `yours alone | everyone's |
  not tested`, derived **per property** (rules: `docs/SYSTEM_DESIGN.md`), never joined
  from `market_scope.scope` by aspect. Real row from the snapshot (Property F):

  ```json
  {"aspect": "Food", "gap": 1.049, "volume": 0.143, "impact_score": 0.1501,
   "started": "2025-06",
   "rationale": "Food is 1.05 below the cluster since 2025-06 (now -0.70 vs +0.35; a significant decline relative to the market). It appears in 14% of your aspect mentions.",
   "current_mean": -0.704, "reference_mean": 0.346, "basis": "cluster", "n": 128,
   "whose_problem": "yours alone",
   "whose_detail": "you dropped 1.22 relative to the market from 2025-06; the market itself moved +0.01"}
  ```

  Property D, Room: `"whose_problem": "yours alone"`, `"whose_detail": "still 0.36
  below the market outside December; the seasonal dip in December (12/12 properties,
  average drop 1.10) is everyone's"`.
- `cri.benchmark`: `market_findings` and `describe_finding` are now public (they were
  private helpers); used by `insights`.
- `classify.BACKENDS` includes `"learned"`; `get_classifier("learned")` returns the
  hybrid classifier with the trained model (`cri.learned_backend`).
- The classifier cache in `cri.api` is keyed by backend, aspects file **and** learned
  model path.
- `cri.travel` was removed; nothing in the frozen contract depended on it.
