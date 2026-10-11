"""Review explorer — filter and search reviews; see the clause each label came from."""

from __future__ import annotations

import common
import streamlit as st

from cri import api

common.configure("Explorer", icon="🔍")
d = common.load_data()

st.title("🔍 Review explorer")
common.synthetic_banner(d)
st.markdown(
    "Every classification is auditable: the **matched clause** shows exactly which words "
    "drove the aspect and sentiment."
)

# --- Try your own review (demo step 4) ----------------------------------------------
st.subheader("✍️ Try your own review")
typed = st.text_area(
    "Type a review in English, Hinglish or Devanagari (press Ctrl+Enter to classify)",
    placeholder="Khana accha tha lekin kamra ganda tha.",
    key="ex_try",
)
if typed.strip():
    found = api.classify_text(typed)
    if found.empty:
        st.info("No aspect detected in this text (the rule baseline only knows its word lists).")
    else:
        st.dataframe(
            found.assign(sentiment=found["sentiment"].map(common.sentiment_label)),
            use_container_width=True,
            hide_index=True,
            column_config={"sentence": st.column_config.TextColumn("clause it came from")},
        )
st.caption(
    "Classified live by the same rule baseline as the dashboard: aspects from "
    "`aspects.yaml`, polarity from `lexicon.yaml`. A demo aid, not an accuracy claim."
)

st.divider()
st.subheader("🔎 Search the reviews")

ANY = "— any —"
SENTIMENTS = {"— any —": None, "👍 positive": 1, "😐 neutral": 0, "👎 negative": -1}

c1, c2, c3 = st.columns(3)
prop = c1.selectbox("Property", [ANY, *api.list_properties(d)], key="ex_prop")
aspect = c2.selectbox("Aspect", [ANY, *api.list_aspects()], key="ex_aspect")
sentiment_label = c3.selectbox("Sentiment", list(SENTIMENTS), key="ex_sentiment")

start, end = common.date_bounds(d, key="ex_dates")
query = st.text_input("Search review text (literal, case-insensitive)", key="ex_query")

results = api.search_reviews(
    d,
    property_id=None if prop == ANY else prop,
    aspect=None if aspect == ANY else aspect,
    sentiment=SENTIMENTS[sentiment_label],
    start=start,
    end=end,
    query=query or None,
)

st.caption(f"{len(results):,} matched clause(s).")
if results.empty:
    st.info("No reviews match these filters. Loosen a filter or clear the search box.")
else:
    display = results.assign(sentiment=results["sentiment"].map(common.sentiment_label))
    display = display[
        ["date", "property_id", "platform", "rating", "aspect", "sentiment", "sentence", "text"]
    ]
    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "date": st.column_config.DatetimeColumn("date", format="YYYY-MM-DD"),
            "sentence": st.column_config.TextColumn("matched clause", width="medium"),
            "text": st.column_config.TextColumn("full review", width="large"),
        },
    )
    common.download_button(results, "search_results.csv", key="dl_search")
