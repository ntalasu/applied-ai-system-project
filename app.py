"""
Streamlit web UI for VibeCheck.

Thin UI layer over the existing recommender (src/recommender.py), the
natural-language RAG feature (src/nl_interface.py), and the reliability
suite (src/reliability.py) — no scoring, parsing, or AI logic lives here;
this file only renders widgets and calls the functions those modules
already expose and test.

Run with: streamlit run app.py
"""

import os

import streamlit as st

from src.nl_interface import generate_explanation, parse_taste_description
from src.recommender import load_songs, recommend_songs
from src.reliability import run_reliability_suite

st.set_page_config(page_title="VibeCheck", page_icon="🎵", layout="wide")


@st.cache_data
def get_songs():
    return load_songs("data/songs.csv")


songs = get_songs()
known_genres = sorted({song["genre"] for song in songs})
known_moods = sorted({song["mood"] for song in songs})

st.title("🎵 VibeCheck")
st.caption(
    "A transparent, rule-based music recommender with an optional Claude-powered "
    "natural-language layer (RAG)."
)

with st.sidebar:
    st.header("Claude API")
    key_input = st.text_input(
        "ANTHROPIC_API_KEY",
        type="password",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
        help="Only kept for this browser session — never written to disk.",
    )
    if key_input:
        os.environ["ANTHROPIC_API_KEY"] = key_input
    elif "ANTHROPIC_API_KEY" in os.environ:
        del os.environ["ANTHROPIC_API_KEY"]

    model_input = st.text_input(
        "CLAUDE_MODEL (optional)",
        value=os.environ.get("CLAUDE_MODEL", ""),
        placeholder="claude-opus-5 (default)",
    )
    if model_input:
        os.environ["CLAUDE_MODEL"] = model_input

    if os.environ.get("ANTHROPIC_API_KEY"):
        st.success("AI mode active — natural-language requests will call Claude.")
    else:
        st.info("No API key set — natural-language requests will use the rule-based fallback.")

    st.divider()
    st.caption(f"Catalog: {len(songs)} songs · {len(known_genres)} genres · {len(known_moods)} moods")


def render_recommendations(recommendations) -> None:
    if not recommendations:
        st.warning("No recommendations to show.")
        return
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        with st.container(border=True):
            st.markdown(
                f"**{rank}. {song['title']} — {song['artist']}**  \n"
                f"`{song['genre']}` · `{song['mood']}` · score **{score:.2f}**"
            )
            st.caption(explanation)


tab_structured, tab_nl, tab_reliability = st.tabs(
    ["🎯 Structured Profile", "💬 Natural Language (AI)", "🧪 Reliability Report"]
)

# --- Tab 1: the original structured-profile scorer, no AI involved ----------

with tab_structured:
    st.subheader("Describe your taste")
    col1, col2 = st.columns(2)

    with col1:
        genre = st.selectbox("Favorite genre", ["(any)"] + known_genres)
        mood = st.selectbox("Favorite mood", ["(any)"] + known_moods)
        k = st.slider("Number of results", 1, 10, 5)

    with col2:
        use_energy = st.checkbox("Target energy")
        energy = st.slider("Energy", 0.0, 1.0, 0.7, disabled=not use_energy)
        use_tempo = st.checkbox("Target tempo (BPM)")
        tempo = st.slider("Tempo", 40, 220, 120, disabled=not use_tempo)
        use_acoustic = st.checkbox("Target acousticness")
        acoustic = st.slider("Acousticness", 0.0, 1.0, 0.3, disabled=not use_acoustic)
        use_valence = st.checkbox("Target valence (mood positivity)")
        valence = st.slider("Valence", 0.0, 1.0, 0.7, disabled=not use_valence)
        use_dance = st.checkbox("Target danceability")
        dance = st.slider("Danceability", 0.0, 1.0, 0.7, disabled=not use_dance)

    profile = {}
    if genre != "(any)":
        profile["favorite_genre"] = genre
    if mood != "(any)":
        profile["favorite_mood"] = mood
    if use_energy:
        profile["target_energy"] = energy
    if use_tempo:
        profile["target_tempo_bpm"] = tempo
    if use_acoustic:
        profile["target_acousticness"] = acoustic
    if use_valence:
        profile["target_valence"] = valence
    if use_dance:
        profile["target_danceability"] = dance

    st.subheader("Top recommendations")
    render_recommendations(recommend_songs(profile, songs, k=k))

# --- Tab 2: the RAG feature — free text in, grounded recommendation out ----

with tab_nl:
    st.subheader("Describe your taste in plain English")

    example_queries = [
        "I want something to pump me up before a workout, high energy and loud",
        "Something mellow and acoustic for a rainy afternoon of studying",
        "Upbeat happy pop, kind of like a summer road trip",
    ]
    clicked_example = None
    for col, query in zip(st.columns(len(example_queries)), example_queries):
        if col.button(query, use_container_width=True):
            clicked_example = query

    text = st.text_area(
        "Your request",
        value=clicked_example or "",
        placeholder="e.g. something moody for a rainy day",
    )

    if st.button("Get recommendation", type="primary"):
        if not text.strip():
            st.warning("Enter a request first.")
        else:
            with st.spinner("Thinking..."):
                try:
                    profile, used_llm, confidence = parse_taste_description(
                        text, known_genres, known_moods
                    )
                except Exception as exc:
                    st.error(f"Parsing failed: {exc}")
                    profile, used_llm, confidence = {}, False, 0.0

                mode_label = "Claude (LLM)" if used_llm else "keyword fallback"
                st.caption(f"Mode: **{mode_label}** · Confidence: **{confidence:.2f}**")
                st.json(profile)

                recommendations = recommend_songs(profile, songs, k=3)

                explanation = None
                try:
                    explanation = generate_explanation(text, recommendations)
                except Exception as exc:
                    st.error(f"Explanation generation failed: {exc}")

                if explanation:
                    st.markdown("### Recommendation")
                    st.write(explanation)

                st.markdown("### Retrieved songs (grounding data)")
                render_recommendations(recommendations)

# --- Tab 3: the reliability harness, runnable live from the UI --------------

with tab_reliability:
    st.subheader("AI feature reliability report")
    st.caption("Runs the same fixed test cases as `scripts/reliability_report.py` — live, right now.")

    if st.button("Run reliability suite"):
        with st.spinner("Running..."):
            results = run_reliability_suite()

        passed = sum(1 for r in results if r["passed"])
        avg_confidence = sum(r["confidence"] for r in results) / len(results) if results else 0.0

        col1, col2 = st.columns(2)
        col1.metric("Tests passed", f"{passed}/{len(results)}")
        col2.metric("Average confidence", f"{avg_confidence:.2f}")

        st.table(
            [
                {
                    "Input": result["text"] or "(empty string)",
                    "Criteria": result["criteria"],
                    "Mode": result["mode"],
                    "Confidence": f"{result['confidence']:.2f}",
                    "Result": "✅ Pass" if result["passed"] else "❌ Fail",
                }
                for result in results
            ]
        )
