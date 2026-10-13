"""Learned sentiment backend: features, safe model files, sklearn parity, data scripts.

No network and no downloaded data: tiny in-test fixtures only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from cri.classify import get_classifier
from cri.learned_backend import LinearSentimentModel, featurize, model_path

CORPUS = [
    ("khana bahut accha tha", 1), ("room was clean and lovely", 1),
    ("great view, loved it", 1),
    ("khana bekaar tha", -1), ("dirty room and rude staff", -1),
    ("worst stay, never again", -1),
    ("we checked in at noon", 0), ("the hotel is near the mall", 0),
    ("kamra second floor pe tha", 0),
]


def test_featurize_words_bigrams_and_char_ngrams():
    feats = featurize("Khana ACCHA tha")
    assert "w:khana" in feats and "w:khana accha" in feats and "c: kh" in feats
    assert featurize("Khana ACCHA tha") == feats  # deterministic
    assert featurize(None) == [] and featurize("") == []


def test_model_file_round_trip_without_pickle(tmp_path):
    vocab = {"w:accha": 0, "w:bekaar": 1}
    model = LinearSentimentModel(
        vocab, np.ones(2), np.array([[-1.0, 2.0], [0.0, 0.0], [2.0, -1.0]]),
        np.array([0.0, 0.1, 0.0]), (-1, 0, 1), {"name": "tiny"})  # no known feature -> intercept
    path = tmp_path / "m.npz"
    model.save(path)
    with np.load(path, allow_pickle=False) as z:  # must load without pickle
        assert set(z.files) == {"vocab", "idf", "coef", "intercept", "classes", "meta"}
    loaded = LinearSentimentModel.load(path)
    assert loaded.predict(["accha", "bekaar", "unrelated words"]) == [1, -1, 0]
    assert loaded.meta["name"] == "tiny"


def test_numpy_inference_matches_sklearn():
    pytest.importorskip("sklearn")
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression

    texts, labels = zip(*CORPUS, strict=True)
    vec = TfidfVectorizer(analyzer=featurize, sublinear_tf=True)
    x = vec.fit_transform(texts)
    clf = LogisticRegression(C=10, max_iter=1000).fit(x, labels)
    model = LinearSentimentModel(dict(vec.vocabulary_), vec.idf_, clf.coef_, clf.intercept_,
                                 tuple(int(c) for c in clf.classes_), {})
    probes = ["khana accha tha", "rude staff", "near the mall", "unseen words only"]
    ours = np.array([model.scores(t) for t in probes])
    assert np.allclose(ours, clf.decision_function(vec.transform(probes)), atol=1e-9)
    assert model.predict(probes) == clf.predict(vec.transform(probes)).tolist()


def test_learned_backend_is_hybrid_with_packaged_model():
    assert model_path().name == "sentiment_open.npz"
    mentions = get_classifier("learned").classify_review("The food was delicious.")
    assert [m.aspect for m in mentions] == ["Food"]  # aspects still come from the rules
    assert mentions[0].sentiment in (-1, 0, 1)


def test_missing_model_path_is_an_error(monkeypatch, tmp_path):
    monkeypatch.setenv("CRI_LEARNED_MODEL_PATH", str(tmp_path / "nope.npz"))
    with pytest.raises(FileNotFoundError):
        model_path()


# --- data scripts ---------------------------------------------------------------------------


def test_region_file_names_parse_and_plains_are_dropped(tmp_path):
    from scripts.prepare_region_reviews import parse_name, prepare

    assert parse_name("Camp_Awara-Dhanaulti_Tehri_Garhwal_District_Uttarakhand") == {
        "town": "Dhanaulti", "district": "Tehri Garhwal", "state": "Uttarakhand"}
    assert parse_name("X-Kausani_Bageshwar_District_Uttarakhan")["state"] == "Uttarakhand"
    assert parse_name("X-Leh_Leh_District_Ladakh_Jammu_and_Kashmir")["state"] == "Ladakh"
    assert parse_name("Parwati_Resort-Kumaon_Uttarakhand") is None

    rows = {"location": "x", "name": "Secret Reviewer", "user_profile": "/profile/secret",
            "userloc": "Secret Town"}
    pd.DataFrame([{**rows, "review": "Lovely stay, great view", "rating": 50.0},
                  {**rows, "review": "LOVELY stay,  great view", "rating": 40.0},  # same text
                  {**rows, "review": "Dirty and noisy", "rating": 10.0}]).to_csv(
        tmp_path / "Hill_Inn-Mussoorie_Dehradun_District_Uttarakhand.csv", index=False)
    pd.DataFrame([{**rows, "review": "Plains hotel", "rating": 30.0}]).to_csv(
        tmp_path / "Plain_Inn-Haridwar_Haridwar_District_Uttarakhand.csv", index=False)
    data, report = prepare(tmp_path)
    assert list(data["label"]) == [1, -1]  # duplicate dropped, plains district dropped
    assert report["rows_after_hill_filter"] == 3
    assert not data.astype(str).apply(lambda c: c.str.contains("Secret")).any().any()
    assert not {"name", "user_profile", "userloc"} & set(data.columns)


def test_conll_parser_and_hotel_grouped_split(tmp_path, monkeypatch):
    pytest.importorskip("sklearn")
    import scripts.train_sentiment as ts

    conll = tmp_path / "t.txt"
    conll.write_text("meta\t1\tpositive\nkhana\tHin\n@\tO\nsomeone\tEng\naccha\tHin\n"
                     "meta\t2\tnegative\nbekaar\tHin\nhttps\tEng\n", encoding="utf-8")
    parsed = ts._conll(conll)
    assert parsed["1"] == ("khana accha", "positive") and parsed["2"][1] == "negative"

    hotels = [f"H{i:03d}" for i in range(40) for _ in range(5)]
    region = tmp_path / "region.csv"
    pd.DataFrame({"text": [f"review {i}" for i in range(200)], "stars": 5, "label": 1,
                  "hotel": hotels, "town": "T", "district": "D", "state": "S"}).to_csv(region,
                                                                                       index=False)
    monkeypatch.setattr(ts, "REGION", region)
    df = ts.load_region("keep")
    by_split = [set(df[df["split"] == s]["hotel"]) for s in ("train", "dev", "test")]
    assert all(by_split)
    assert not (by_split[0] & by_split[1] or by_split[0] & by_split[2] or by_split[1] & by_split[2])
