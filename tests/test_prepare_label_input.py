import pandas as pd
from scripts.prepare_label_input import prepare_input


def test_prepare_input_validates_drops_identity_and_adds_labels(tmp_path):
    source = tmp_path / "export.csv"
    output = tmp_path / "labels.csv"
    pd.DataFrame(
        {
            "property_id": ["Property A", "Property B"],
            "platform": ["partner", "partner"],
            "date": ["2025-01-01", "2025-01-02"],
            "rating": [5, 2],
            "text": ["Great food", "Room was cold"],
            "language_hint": ["en", "en"],
            "reviewer_name": ["Removed", "Removed too"],
        }
    ).to_csv(source, index=False)

    prepare_input(source, output)
    labels = pd.read_csv(output)

    assert labels["review_id"].tolist() == [0, 1]
    assert labels["gold_aspects"].fillna("").tolist() == ["", ""]
    assert "reviewer_name" not in labels.columns
    assert labels["text"].tolist() == ["Great food", "Room was cold"]
