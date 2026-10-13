"""Train and evaluate the learned clause-sentiment model (CRI_MODEL_BACKEND=learned).

Two models, same recipe (TF-IDF over cri.learned_backend.featurize -> multinomial
logistic regression, balanced classes, C tuned on dev only, seed 42):

- open   : SentiMix Hinglish tweets (SemEval-2020 Task 9, Zenodo 3974927, CC BY 4.0)
           + Hinglish YouTube comments (shae2977, CC BY 4.0). Redistributable:
           written to src/cri/resources/models/sentiment_open.npz (committed).
- region : open + hill-destination hotel reviews (scripts/prepare_region_reviews.py)
           with weak labels from stars. Provenance of that data is uncertain
           (likely TripAdvisor-derived), so the model stays LOCAL:
           data/raw/external/models/sentiment_region.npz (gitignored).

Splits: SentiMix official train/dev/test; YouTube stratified 80/10/10; hill reviews
80/10/10 grouped by HOTEL (no hotel on both sides). Duplicates (normalised text)
are removed across splits, and the SYNTHETIC generator templates are dropped from
training so the template probe stays a fair test.

Every number this prints is measured on held-out data; README/docs quote only these.

    python scripts/prepare_region_reviews.py           # needs the Kaggle download
    python scripts/train_sentiment.py --model open
    python scripts/train_sentiment.py --model region

Needs the train extra: pip install -e ".[train]".
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import GroupShuffleSplit, train_test_split

from cri.classify import RuleClassifier
from cri.generate import TEMPLATES
from cri.learned_backend import LinearSentimentModel, featurize
from cri.normalize import normalize

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "data/raw/external"
SENTIMIX = EXT / "sentimix/Semeval_2020_task9_data/Hinglish"
YOUTUBE = EXT / "hinglish_youtube/yt_hinglish_comments_dataset.csv"
REGION = EXT / "prepared/region_reviews.csv"
OUT = {"open": ROOT / "src/cri/resources/models/sentiment_open.npz",
       "region": EXT / "models/sentiment_region.npz"}
LABELS = {"negative": -1, "neutral": 0, "positive": 1}
CLASSES = [-1, 0, 1]
SEED = 42
C_GRID = (0.5, 1.0, 2.0, 4.0)
MAX_FEATURES = 60_000
FOCUS_TOWN_MIN_REVIEWS = 1000
SOURCES = {
    "sentimix": "SentiMix Hinglish tweets (SemEval-2020 Task 9), Zenodo 10.5281/zenodo.3974927, "
                "CC BY 4.0",
    "youtube": "Hinglish YouTube comments, huggingface.co/datasets/shae2977/"
               "hinglish-youtube-sentiments-dataset @84abda5, CC BY 4.0",
    "region": "Hill-destination hotel reviews (Kaggle orionpax00/uttarakhand-hotel-reviews-india, "
              "uploader-declared CC0, likely TripAdvisor-derived); weak labels from stars",
}


# --- data ---------------------------------------------------------------------------------
def _conll(path: Path) -> dict[str, tuple[str, str | None]]:
    """SentiMix CoNLL: 'meta <uid> [label]' then 'token<TAB>lang' lines."""
    tweets, uid, label, tokens = {}, None, None, []
    for line in path.read_text(encoding="utf-8").splitlines() + ["meta\t__end__"]:
        parts = line.split("\t")
        if parts[0] == "meta":
            if uid is not None:
                tweets[uid] = (_clean(" ".join(tokens)), label)
            uid, label, tokens = parts[1], (parts[2] if len(parts) > 2 else None), []
        elif parts[0]:
            tokens.append(parts[0])
    return tweets


def _clean(text: str) -> str:
    text = re.sub(r"https? : / / \S+(?: [./] \S+)*", " ", text)  # tokenised URLs
    text = re.sub(r"@ \S+", " ", text)  # @mentions (usernames)
    return re.sub(r"\s+", " ", text).strip()


def load_sentimix() -> pd.DataFrame:
    rows = []
    for split, name in (("train", "Hinglish_train_14k_split_conll.txt"),
                        ("dev", "Hinglish_dev_3k_split_conll.txt")):
        for text, label in _conll(SENTIMIX / name).values():
            rows.append((text, LABELS[label], split, "sentimix", None))
    gold = pd.read_csv(SENTIMIX / "Hinglish_test_labels.txt", dtype=str)
    gold = gold.set_index("Uid")["Sentiment"]
    for uid, (text, _) in _conll(SENTIMIX / "Hinglish_test_unalbelled_conll_updated.txt").items():
        rows.append((text, LABELS[gold[uid]], "test", "sentimix", None))
    return pd.DataFrame(rows, columns=["text", "label", "split", "source", "group"])


def load_youtube() -> pd.DataFrame:
    df = pd.read_csv(YOUTUBE)
    df = pd.DataFrame({"text": df["comment"].astype(str),
                       "label": df["sentiment"].str.lower().map(LABELS)}).dropna()
    train, rest = train_test_split(df, test_size=0.2, stratify=df["label"], random_state=SEED)
    dev, test = train_test_split(rest, test_size=0.5, stratify=rest["label"], random_state=SEED)
    return pd.concat([train.assign(split="train"), dev.assign(split="dev"),
                      test.assign(split="test")]).assign(source="youtube", group=None)


def load_region(neutral: str) -> pd.DataFrame:
    df = pd.read_csv(REGION)
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
    train_idx, rest_idx = next(gss.split(df, groups=df["hotel"]))
    rest = df.iloc[rest_idx]
    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=SEED)
    dev_idx, test_idx = next(gss2.split(rest, groups=rest["hotel"]))
    split = pd.Series("train", index=df.index)
    split.iloc[rest_idx[dev_idx]] = "dev"
    split.iloc[rest_idx[test_idx]] = "test"
    df = df.assign(split=split, source="region", group=df["hotel"])
    if neutral == "drop":  # ablation: 3-star reviews are mixed; drop them from training only
        df = df[~((df["split"] == "train") & (df["label"] == 0))]
    return df


def assemble(model: str, neutral: str) -> pd.DataFrame:
    parts = [load_sentimix(), load_youtube()]
    if REGION.is_file():
        parts.append(load_region(neutral))  # region test is evaluated for both models
    df = pd.concat(parts, ignore_index=True)
    if model == "open":
        df = df[~((df["source"] == "region") & (df["split"] != "test"))]
    df["norm"] = df["text"].map(normalize)
    templates = {normalize(t) for opts in TEMPLATES.values() for _, t in opts}
    df = df[~df["norm"].isin(templates)]
    df = df[df["norm"].str.len() > 0]
    # A text seen in training never counts as dev/test (and dev never as test).
    seen: set[str] = set()
    keep = []
    for split in ("train", "dev", "test"):
        part = df[df["split"] == split]
        part = part[~part["norm"].isin(seen)].drop_duplicates("norm")
        seen |= set(part["norm"])
        keep.append(part)
    return pd.concat(keep, ignore_index=True)


# --- metrics ------------------------------------------------------------------------------
def macro_f1(y, p) -> float:
    return float(f1_score(y, p, labels=CLASSES, average="macro", zero_division=0))


def report(y, p, rng: np.random.Generator, n_boot: int = 500) -> dict:
    y, p = np.asarray(y), np.asarray(p)
    prec, rec, f1, support = precision_recall_fscore_support(y, p, labels=CLASSES, zero_division=0)
    boots = [macro_f1(y[i], p[i]) for i in (rng.integers(0, len(y), len(y)) for _ in range(n_boot))]
    return {
        "n": int(len(y)), "macro_f1": round(macro_f1(y, p), 3),
        "macro_f1_ci95": [round(float(np.percentile(boots, 2.5)), 3),
                          round(float(np.percentile(boots, 97.5)), 3)],
        "per_class": {str(c): {"precision": round(float(a), 3), "recall": round(float(b), 3),
                               "f1": round(float(f), 3), "support": int(s)}
                      for c, a, b, f, s in zip(CLASSES, prec, rec, f1, support, strict=True)},
        "confusion": confusion_matrix(y, p, labels=CLASSES).tolist(),
    }


def rule_predict(texts) -> list[int]:
    return [RuleClassifier.sentence_sentiment(normalize(t)) for t in texts]


def template_probe(predict) -> tuple[int, int]:
    """Polarity of the 36 SYNTHETIC generator templates (whole sentence)."""
    items = [(t, 1 if pol == "pos" else -1) for (_, pol), opts in TEMPLATES.items()
             for _, t in opts]
    preds = predict([t for t, _ in items])
    return sum(int(p == y) for p, (_, y) in zip(preds, items, strict=True)), len(items)


# --- training -----------------------------------------------------------------------------
def train(df: pd.DataFrame) -> tuple[LinearSentimentModel, dict]:
    tr, dev = df[df["split"] == "train"], df[df["split"] == "dev"]
    vec = TfidfVectorizer(analyzer=featurize, sublinear_tf=True, min_df=3,
                          max_features=MAX_FEATURES, dtype=np.float32)
    t0 = time.time()
    x_tr = vec.fit_transform(tr["text"])
    x_dev = vec.transform(dev["text"])
    print(f"features: {x_tr.shape[1]} ({time.time() - t0:.0f}s)")
    # Equal total weight per source, so 80k hotel reviews do not drown 17k Hinglish texts.
    per_source = tr["source"].value_counts()
    weights = tr["source"].map(lambda s: len(tr) / (len(per_source) * per_source[s])).to_numpy()
    tuning = {}
    best = None
    for c in C_GRID:
        clf = LogisticRegression(C=c, class_weight="balanced", max_iter=3000, random_state=SEED)
        clf.fit(x_tr, tr["label"], sample_weight=weights)
        pred = clf.predict(x_dev)
        per = {s: macro_f1(dev["label"][dev["source"] == s], pred[(dev["source"] == s).to_numpy()])
               for s in dev["source"].unique()}
        score = float(np.mean(list(per.values())))
        tuning[str(c)] = {"dev_mean_macro_f1": round(score, 4),
                          **{k: round(v, 4) for k, v in per.items()}}
        print(f"C={c}: dev mean macro-F1 {score:.4f} {per}")
        if best is None or score > best[0]:
            best = (score, c, clf)
    _, c, clf = best
    vocab = {f: int(i) for f, i in vec.vocabulary_.items()}
    model = LinearSentimentModel(vocab, vec.idf_.astype(np.float64), clf.coef_.astype(np.float64),
                                 clf.intercept_.astype(np.float64),
                                 tuple(int(k) for k in clf.classes_), {})
    return model, {"C": c, "tuning": tuning, "n_features": len(vocab),
                   "n_train": {k: int(v) for k, v in per_source.items()}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", choices=("open", "region"), required=True)
    parser.add_argument("--neutral", choices=("keep", "drop"), default="keep",
                        help="3-star hill reviews in training: keep as neutral, or drop")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    if args.model == "region" and not REGION.is_file():
        raise SystemExit(f"{REGION} missing: run scripts/prepare_region_reviews.py first")
    out = args.out or OUT[args.model]
    rng = np.random.default_rng(SEED)

    df = assemble(args.model, args.neutral)
    print(df.groupby(["source", "split"]).size().unstack(fill_value=0).to_string())
    model, info = train(df)

    test = df[df["split"] == "test"]
    results = {}
    for source, part in test.groupby("source"):
        y = part["label"].to_numpy()
        seen = df[(df["source"] == source) & (df["split"] == "train")]["label"]
        majority = np.full(len(y), (seen if len(seen) else part["label"]).mode().iloc[0])
        results[source] = {"model": report(y, model.predict(part["text"].tolist()), rng),
                           "rules": report(y, rule_predict(part["text"]), rng),
                           "majority_macro_f1": round(macro_f1(y, majority), 3)}
        print(f"[test] {source}: model {results[source]['model']['macro_f1']} "
              f"{results[source]['model']['macro_f1_ci95']} | rules "
              f"{results[source]['rules']['macro_f1']} | majority "
              f"{results[source]['majority_macro_f1']} (n={len(y)})")
    if "region" in set(test["source"]):
        reg = test[test["source"] == "region"]
        model_pred = pd.Series(model.predict(reg["text"].tolist()), index=reg.index)
        rule_pred = pd.Series(rule_predict(reg["text"]), index=reg.index)
        all_region = pd.read_csv(REGION)
        focus = all_region["town"].value_counts()
        focus = set(focus[focus >= FOCUS_TOWN_MIN_REVIEWS].index)
        breakdown = {}
        for key, part in list(reg.groupby("state")) + [
                (f"town:{t}", p) for t, p in reg.groupby("town") if t in focus]:
            breakdown[key] = {"n": int(len(part)),
                              "model": round(macro_f1(part["label"], model_pred[part.index]), 3),
                              "rules": round(macro_f1(part["label"], rule_pred[part.index]), 3)}
        results["region_breakdown"] = breakdown

    probe = template_probe(model.predict)
    probe_rules = template_probe(rule_predict)
    info |= {"templates_correct": {"model": list(probe), "rules": list(probe_rules)}}
    print(f"templates: model {probe[0]}/{probe[1]}, rules {probe_rules[0]}/{probe_rules[1]}")

    meta = {"name": f"sentiment_{args.model}", "trained": time.strftime("%Y-%m-%d"),
            "neutral_3star": args.neutral, "seed": SEED,
            "sources": {s: SOURCES[s] for s in sorted(set(df[df["split"] == "train"]["source"]))},
            "classes": [-1, 0, 1], **info}
    model = LinearSentimentModel(model.vocab, model.idf, model.coef, model.intercept,
                                 model.classes, meta)
    out.parent.mkdir(parents=True, exist_ok=True)
    model.save(out)
    metrics_path = out.with_suffix(".metrics.json")
    metrics_path.write_text(json.dumps({"meta": meta, "test": results}, indent=1), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1e6:.2f} MB) and {metrics_path}")


if __name__ == "__main__":
    main()
