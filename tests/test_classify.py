"""The rule classifier should recover aspect + sentiment on known clauses."""

from cri.classify import RuleClassifier


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
