"""The rule classifier should recover aspect + sentiment on known clauses, and its
word lists (aspects.yaml, lexicon.yaml) must load and validate correctly."""

import pytest

from cri import classify
from cri.classify import RuleClassifier, get_classifier, load_aspects, parse_lexicon


def _single(clf, text):
    res = clf.classify_review(text)
    assert res, f"no aspect found in: {text!r}"
    return res


def test_food_positive_english():
    clf = RuleClassifier()
    res = _single(clf, "The food was delicious and the breakfast was fresh.")
    aspects = {r.aspect for r in res}
    assert "Food" in aspects
    assert all(r.sentiment == 1 for r in res if r.aspect == "Food")


def test_food_negative_hinglish():
    clf = RuleClassifier()
    res = _single(clf, "Khaana bekaar aur thanda tha.")
    food = [r for r in res if r.aspect == "Food"]
    assert food and all(r.sentiment == -1 for r in food)


def test_food_positive_devanagari():
    clf = RuleClassifier()
    res = _single(clf, "खाना बहुत बढ़िया था।")
    food = [r for r in res if r.aspect == "Food"]
    assert food and all(r.sentiment == 1 for r in food)


def test_room_heating_negative():
    clf = RuleClassifier()
    res = _single(clf, "The room heater was not working and it was freezing cold.")
    room = [r for r in res if r.aspect == "Room"]
    assert room and all(r.sentiment == -1 for r in room)


def test_negation_flips_sentiment():
    assert RuleClassifier.sentence_sentiment("the food was not good") == -1
    assert RuleClassifier.sentence_sentiment("the food was good") == 1


def test_multiple_aspects_in_one_review():
    clf = RuleClassifier()
    res = clf.classify_review(
        "The food was delicious. The staff were rude and unhelpful."
    )
    by_aspect = {r.aspect: r.sentiment for r in res}
    assert by_aspect.get("Food") == 1
    assert by_aspect.get("Staff") == -1


# --- lexicon config (resources/lexicon.yaml) ----------------------------------------


def _valid_lexicon():
    return {
        "positive": ["good"], "negative": ["bad"], "positive_phrases": ["paisa vasool"],
        "negative_phrases": ["not working"], "negation": ["not"],
    }


def test_lexicon_loads_from_yaml_into_module_names():
    assert "badhiya" in classify.POSITIVE and "bekaar" in classify.NEGATIVE
    assert "बढ़िया" in classify.POSITIVE  # Devanagari survives the YAML round trip
    assert "not working" in classify.NEGATIVE_PHRASES
    assert classify.NEGATION >= {"not", "nahi"}
    assert not classify.POSITIVE & classify.NEGATIVE


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda lx: lx.pop("negation"), "missing key"),
        (lambda lx: lx.update(positive=["Good"]), "lowercase"),
        (lambda lx: lx.update(positive=[" good"]), "lowercase"),
        (lambda lx: lx.update(negative=[""]), "empty"),
        (lambda lx: lx.update(negative=[]), "non-empty list"),
        (lambda lx: lx.update(negative=["good"]), "both 'positive' and 'negative'"),
        (lambda lx: lx.update(negation=["bad"]), "both 'negation' and 'negative'"),
    ],
)
def test_malformed_lexicon_fails_loudly(mutate, message):
    lexicon = _valid_lexicon()
    mutate(lexicon)
    with pytest.raises(ValueError, match=message):
        parse_lexicon(lexicon)


def test_valid_lexicon_parses():
    assert parse_lexicon(_valid_lexicon())["positive"] == ["good"]


# --- backend selection + aspect taxonomy override -----------------------------------


def test_get_classifier_defaults_to_rule(monkeypatch):
    monkeypatch.delenv("CRI_MODEL_BACKEND", raising=False)
    assert isinstance(get_classifier(), RuleClassifier)


def test_get_classifier_reads_env_and_rejects_unknown(monkeypatch):
    monkeypatch.setenv("CRI_MODEL_BACKEND", "Rule ")
    assert isinstance(get_classifier(), RuleClassifier)
    with pytest.raises(ValueError, match="available: rule, transformer"):
        get_classifier("gpt-9")


def test_aspects_path_override(tmp_path, monkeypatch):
    custom = tmp_path / "aspects.yaml"
    custom.write_text("aspects:\n  Spa:\n    - spa\n    - massage\n", encoding="utf-8")
    monkeypatch.setenv("CRI_ASPECTS_PATH", str(custom))
    assert list(load_aspects()) == ["Spa"]
    res = RuleClassifier().classify_review("The spa was amazing.")
    assert [(r.aspect, r.sentiment) for r in res] == [("Spa", 1)]


def test_bad_aspects_file_is_a_clear_error(tmp_path, monkeypatch):
    bad = tmp_path / "aspects.yaml"
    bad.write_text("aspects:\n  Spa: []\n", encoding="utf-8")
    monkeypatch.setenv("CRI_ASPECTS_PATH", str(bad))
    with pytest.raises(ValueError, match="non-empty list"):
        load_aspects()


def test_classify_reviews_matches_one_by_one_and_tolerates_missing_text():
    clf = RuleClassifier()
    texts = ["The food was delicious.", "The staff were rude."]
    assert clf.classify_reviews(texts) == [clf.classify_review(t) for t in texts]
    assert clf.classify_review(None) == []
