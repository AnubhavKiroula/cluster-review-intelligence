"""The synthetic generator must be deterministic and schema-compliant."""

from cri.generate import INJECTED_PATTERNS, PROPERTIES, generate
from cri.schema import IDENTITY_COLUMNS, REQUIRED_COLUMNS, validate_reviews


def test_deterministic_for_same_seed():
    a = generate(seed=42)
    b = generate(seed=42)
    assert a.equals(b)


def test_different_seed_changes_data():
    a = generate(seed=1)
    b = generate(seed=2)
    assert not a.equals(b)


def test_schema_compliant_and_no_pii():
    df = generate(seed=42)
    for col in REQUIRED_COLUMNS:
        assert col in df.columns
    assert not ({c.lower() for c in df.columns} & IDENTITY_COLUMNS)
    # Should pass the same validation real data must pass.
    validate_reviews(df)


def test_twelve_properties_and_rating_bounds():
    df = generate(seed=42)
    assert sorted(df["property_id"].unique()) == sorted(PROPERTIES)
    assert df["rating"].between(1, 5).all()


def test_injected_patterns_metadata():
    assert INJECTED_PATTERNS["food_decline"]["property"] == "Property F"
    assert INJECTED_PATTERNS["food_decline"]["change_month"] == "2025-06"
    assert INJECTED_PATTERNS["december_heating"]["scope"] == "market-wide"


def test_null_mode_has_no_injected_patterns():
    null = generate(seed=42, inject_patterns=False)
    injected = generate(seed=42)
    # The December burst of extra Room complaints only exists with patterns injected.
    assert len(null) < len(injected)
    validate_reviews(null)


def test_end_accepts_a_full_date():
    assert generate(seed=5, end="2025-12-31").equals(generate(seed=5, end="2025-12"))


def test_seed_42_reproduces_the_committed_sample():
    from cri.loader import load_reviews

    committed = load_reviews("data/sample/synthetic_reviews.csv")
    assert committed.equals(validate_reviews(generate(seed=42)))


def test_cli_refuses_an_output_name_without_synthetic(tmp_path):
    import pytest

    from cri.generate import main

    with pytest.raises(SystemExit):
        main(["--out", str(tmp_path / "reviews.csv")])
    main(["--out", str(tmp_path / "synthetic_null.csv"), "--no-patterns"])
    assert (tmp_path / "synthetic_null.csv").exists()
