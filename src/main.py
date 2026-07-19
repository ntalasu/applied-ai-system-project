"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

from src.recommender import load_songs, recommend_songs


def main() -> None:
    songs = load_songs("data/songs.csv") 

    # Taste profile: "high-energy rock" listener.
    # Categorical anchors (genre/mood) set intent; continuous targets
    # (energy/tempo/acousticness/valence/danceability) let the recommender
    # rank by *degree* of fit instead of exact-match only.
    user_prefs = {
        "favorite_genre": "rock",
        "favorite_mood": "intense",
        "target_energy": 0.90,        # loud, driving
        "target_tempo_bpm": 150,      # fast
        "target_acousticness": 0.10,  # electric, not acoustic
        "target_valence": 0.50,       # emotionally neutral-to-dark
        "target_danceability": 0.60,  # groove present but not a dance track
    }

    recommendations = recommend_songs(user_prefs, songs, k=5)

    genre = user_prefs.get("favorite_genre", "any")
    mood = user_prefs.get("favorite_mood", "any")
    energy = user_prefs.get("target_energy", "n/a")
    print(f"\nTaste profile: genre={genre}, mood={mood}, target_energy={energy}")
    print(f"\nTop {len(recommendations)} recommendations")
    print("=" * 64)

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n{rank}. {song['title']} — {song['artist']}")
        print(f"   genre: {song['genre']}  |  mood: {song['mood']}  |  score: {score:.2f}")
        print("   reasons:")
        for reason in explanation.split("; "):
            print(f"     • {reason}")
    print()


if __name__ == "__main__":
    main()
