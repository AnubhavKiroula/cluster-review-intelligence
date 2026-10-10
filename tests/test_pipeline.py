"""label_reviews: review_id linkage and robustness to empty/missing input."""

import numpy as np
import pandas as pd

from cri.generate import generate
from cri.pipeline import LABELLED_COLUMNS, label_reviews


def _reviews(texts):
    return pd.DataFrame(
        {
            "property_id": ["Property A"] * len(texts),
            "date": pd.to_datetime(["2024-01-05"] * len(texts)),
            "text": texts,
        }
    )


def test_review_id_defaults_to_the_frame_index():
    df = _reviews(["The food was delicious.", "The staff were rude."]).set_axis([10, 20])
    lab = label_reviews(df)
    assert list(lab.columns) == LABELLED_COLUMNS
    assert set(lab["review_id"]) == {10, 20}


def test_review_id_column_is_honoured():
    df = _reviews(["The food was delicious."]).assign(review_id=["R-1"])
    assert label_reviews(df)["review_id"].tolist() == ["R-1"]


def test_one_review_can_yield_several_mentions_with_one_id():
    lab = label_reviews(_reviews(["Khaana badhiya tha aur nashta bhi tasty."]))
    assert len(lab) >= 2 and lab["review_id"].nunique() == 1


def test_empty_input_keeps_columns_and_dtypes():
    lab = label_reviews(generate(seed=1).head(0))
    assert lab.empty and list(lab.columns) == LABELLED_COLUMNS
    assert pd.api.types.is_datetime64_any_dtype(lab["date"])


def test_missing_text_produces_no_mentions_instead_of_crashing():
    lab = label_reviews(_reviews(["The food was delicious.", np.nan, None]))
    assert set(lab["review_id"]) == {0}


def test_sentiment_is_integer():
    lab = label_reviews(_reviews(["The food was delicious.", "The room was dirty."]))
    assert lab["sentiment"].dtype == "int64"
