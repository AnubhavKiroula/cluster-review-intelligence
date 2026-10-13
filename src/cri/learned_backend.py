"""Trained clause-sentiment backend (``CRI_MODEL_BACKEND=learned``).

Hybrid like the transformer backend: aspects still come from the transparent cue
terms; a linear model trained on public data (scripts/train_sentiment.py) scores
each aspect clause -1 / 0 / +1. Features are word 1-2-grams and character 2-5-grams
of the *normalised* text (cri.normalize), TF-IDF weighted with sublinear tf and L2
norm, so Hinglish spelling variants share character n-grams.

Inference is numpy-only and the model file is a compressed ``.npz`` read with
``allow_pickle=False``: loading a model never executes code. ``featurize`` is the
exact analyzer used in training, so features cannot drift between the two.

Model file: ``$CRI_LEARNED_MODEL_PATH`` if set, else the packaged open-data model
(``resources/models/sentiment_open.npz``, trained on CC BY 4.0 data only). Results:
docs/AI_MODEL.md. The default backend stays ``rule`` until this one wins on real,
hand-labelled hill-tourism reviews (TBD).
"""

from __future__ import annotations

import json
import math
import os
from collections import Counter
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import numpy as np

from .normalize import normalize, tokenize

PACKAGED_MODEL = "sentiment_open.npz"
FORMAT_VERSION = 1
CHAR_RANGE = (2, 5)


def featurize(text: str) -> list[str]:
    """Word 1-2-grams (``w:``) + within-word character 2-5-grams (``c:``)."""
    words = tokenize(normalize(text if isinstance(text, str) else ""))
    feats = [f"w:{w}" for w in words]
    feats += [f"w:{a} {b}" for a, b in zip(words, words[1:], strict=False)]
    lo, hi = CHAR_RANGE
    for w in words:
        padded = f" {w} "
        for n in range(lo, hi + 1):
            feats += [f"c:{padded[i:i + n]}" for i in range(len(padded) - n + 1)]
    return feats


@dataclass(frozen=True)
class LinearSentimentModel:
    vocab: dict[str, int]
    idf: np.ndarray        # (V,)
    coef: np.ndarray       # (C, V)
    intercept: np.ndarray  # (C,)
    classes: tuple[int, ...]
    meta: dict

    @classmethod
    def load(cls, path: str | Path) -> LinearSentimentModel:
        with np.load(path, allow_pickle=False) as z:
            meta = json.loads(str(z["meta"]))
            if meta.get("format_version") != FORMAT_VERSION:
                raise ValueError(f"{path}: unsupported model format {meta.get('format_version')}")
            vocab = {f: i for i, f in enumerate(z["vocab"].tolist())}
            return cls(vocab, z["idf"].astype(np.float64), z["coef"].astype(np.float64),
                       z["intercept"].astype(np.float64), tuple(int(c) for c in z["classes"]),
                       meta)

    def save(self, path: str | Path) -> None:
        order = sorted(self.vocab, key=self.vocab.get)
        np.savez_compressed(
            path, vocab=np.array(order), idf=self.idf.astype(np.float32),
            coef=self.coef.astype(np.float32), intercept=self.intercept.astype(np.float32),
            classes=np.array(self.classes, dtype=np.int8),
            meta=np.array(json.dumps(self.meta | {"format_version": FORMAT_VERSION})))

    def scores(self, text: str) -> np.ndarray:
        counts = Counter(f for f in featurize(text) if f in self.vocab)
        if not counts:
            return self.intercept.copy()
        idx = np.fromiter((self.vocab[f] for f in counts), dtype=np.int64, count=len(counts))
        tf = np.fromiter((1.0 + math.log(c) for c in counts.values()), dtype=np.float64,
                         count=len(counts))
        x = tf * self.idf[idx]
        x /= np.linalg.norm(x)
        return self.coef[:, idx] @ x + self.intercept

    def predict(self, texts: list[str]) -> list[int]:
        return [self.classes[int(np.argmax(self.scores(t)))] for t in texts]


def model_path() -> Path:
    env = os.environ.get("CRI_LEARNED_MODEL_PATH")
    if env:
        path = Path(env)
        if not path.is_file():
            raise FileNotFoundError(f"CRI_LEARNED_MODEL_PATH={env} does not exist")
        return path
    packaged = resources.files("cri").joinpath("resources", "models", PACKAGED_MODEL)
    if not packaged.is_file():
        raise FileNotFoundError(
            "No packaged learned model; train one with scripts/train_sentiment.py and set "
            "CRI_LEARNED_MODEL_PATH")
    return Path(str(packaged))


def load_learned_sentiment_fn():
    """``clauses -> [-1|0|+1]`` from the configured model file."""
    return LinearSentimentModel.load(model_path()).predict
