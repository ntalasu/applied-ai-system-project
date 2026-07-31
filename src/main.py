"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

import logging

from src.recommender import load_songs, recommend_songs
from src.nl_interface import generate_explanation, parse_taste_description

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# Distinct taste profiles plus adversarial / edge-case profiles used to
# evaluate the scoring logic. Categorical anchors (genre/mood) set intent;
# continuous targets let the recommender rank by *degree* of fit.
PROFILES = {
    # --- Three distinct, well-formed profiles ---
    "High-Energy Pop": {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.85,
        "target_tempo_bpm": 125,
        "target_acousticness": 0.15,
        "target_valence": 0.85,
        "target_danceability": 0.85,
    },
    "Chill Lofi": {
        "favorite_genre": "lofi",
        "favorite_mood": "chill",
        "target_energy": 0.35,
        "target_tempo_bpm": 75,
        "target_acousticness": 0.80,
        "target_valence": 0.55,
        "target_danceability": 0.55,
    },
    "Deep Intense Rock": {
        "favorite_genre": "rock",
        "favorite_mood": "intense",
        "target_energy": 0.90,
        "target_tempo_bpm": 150,
        "target_acousticness": 0.10,
        "target_valence": 0.40,
        "target_danceability": 0.60,
    },
    # --- Adversarial / edge-case profiles ---
    # Conflicting signals: wants maximum energy/tempo but a "sad" mood that
    # doesn't exist in the catalog (mood match can never fire).
    "Adversarial: Loud but Sad": {
        "favorite_mood": "sad",
        "target_energy": 0.95,
        "target_tempo_bpm": 160,
        "target_valence": 0.10,
    },
    # Empty profile: no preferences at all. Every song scores 0.0, so the
    # energy tie-break alone decides the order (loudest songs win).
    "Edge: Empty Profile": {},
    # Unknown genre: a genre string not present in the catalog, so the +2.0
    # genre bonus can never be awarded.
    "Edge: Unknown Genre (kpop)": {
        "favorite_genre": "kpop",
        "favorite_mood": "happy",
        "target_energy": 0.50,
    },
}


def print_recommendations(name: str, user_prefs: dict, songs: list, k: int = 5) -> None:
    """Run the recommender for one named profile and pretty-print the top k."""
    recommendations = recommend_songs(user_prefs, songs, k=k)

    genre = user_prefs.get("favorite_genre", "any")
    mood = user_prefs.get("favorite_mood", "any")
    energy = user_prefs.get("target_energy", "n/a")
    print(f"\n{'#' * 64}")
    print(f"# {name}")
    print(f"# profile: genre={genre}, mood={mood}, target_energy={energy}")
    print(f"{'#' * 64}")
    print(f"\nTop {len(recommendations)} recommendations")

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n{rank}. {song['title']} — {song['artist']}")
        print(f"   genre: {song['genre']}  |  mood: {song['mood']}  |  score: {score:.2f}")
        print("   reasons:")
        for reason in explanation.split("; "):
            print(f"     • {reason}")
    print()


# Free-text taste descriptions for the natural-language (RAG) mode. Unlike
# PROFILES above, these aren't pre-structured — the system has to figure out
# genre/mood/energy targets from plain English before it can even call the
# recommender.
NL_QUERIES = [
    "I want something to pump me up before a workout, high energy and loud",
    "Something mellow and acoustic for a rainy afternoon of studying",
    "Upbeat happy pop, kind of like a summer road trip",
]


def run_natural_language_mode(songs: list) -> None:
    """
    Demonstrates the RAG layer: parse a free-text request into a taste
    profile (retrieval query), score/rank the catalog against it (retrieval),
    then have the model write a recommendation grounded in those retrieved
    results rather than just printing them.
    """
    known_genres = sorted({song["genre"] for song in songs})
    known_moods = sorted({song["mood"] for song in songs})

    print(f"\n{'#' * 64}")
    print("# Natural Language Mode (RAG)")
    print(f"{'#' * 64}")

    for query in NL_QUERIES:
        print(f"\nRequest: \"{query}\"")
        try:
            profile, used_llm, confidence = parse_taste_description(query, known_genres, known_moods)
        except Exception:
            logger.exception("Failed to parse taste description; skipping this request")
            continue

        mode = "LLM" if used_llm else "keyword fallback"
        print(f"Parsed profile ({mode}, confidence={confidence:.2f}): {profile}")

        recommendations = recommend_songs(profile, songs, k=3)
        try:
            explanation = generate_explanation(query, recommendations)
        except Exception:
            logger.exception("Failed to generate explanation; skipping this request")
            continue

        print(explanation)
    print()


def main() -> None:
    songs = load_songs("data/songs.csv")
    for name, prefs in PROFILES.items():
        print_recommendations(name, prefs, songs)

    run_natural_language_mode(songs)


if __name__ == "__main__":
    main()
