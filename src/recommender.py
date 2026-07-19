import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Algorithm recipe weights (see design notes / README).
#   Genre match .......... +2.0   (primary intent, coarse bucket)
#   Mood match ........... +1.0   (refines within genre)
#   Energy similarity .... up to +2.0   (strongest differentiator)
#   Tempo similarity ..... up to +1.5   (normalized by TEMPO_RANGE)
#   Acousticness sim ..... up to +1.5
#   Valence similarity ... up to +0.5   (weak signal, low weight)
#   Danceability sim ..... up to +0.5   (weak signal, low weight)
# Categorical matches are *soft bonuses*, never hard filters, so near-genre
# songs (e.g. metal for a rock profile) still surface on the continuous axes.
# ---------------------------------------------------------------------------
W_GENRE = 2.0
W_MOOD = 1.0
TEMPO_RANGE = 108.0  # observed tempo span in the dataset (~60-168 BPM)

# (user_prefs key, song key, weight, is_tempo) for the continuous terms.
CONTINUOUS_FEATURES = [
    ("target_energy", "energy", 2.0, False),
    ("target_tempo_bpm", "tempo_bpm", 1.5, True),
    ("target_acousticness", "acousticness", 1.5, False),
    ("target_valence", "valence", 0.5, False),
    ("target_danceability", "danceability", 0.5, False),
]

NUMERIC_FIELDS = ("energy", "tempo_bpm", "valence", "danceability", "acousticness")


@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        """Store the catalog of Songs this recommender ranks over."""
        self.songs = songs

    def _score(self, user: UserProfile, song: Song) -> Tuple[float, List[str]]:
        """Score one Song against a UserProfile using the trimmed recipe."""
        score = 0.0
        reasons: List[str] = []

        if song.genre == user.favorite_genre:
            score += W_GENRE
            reasons.append(f"genre match: {song.genre} (+{W_GENRE:.1f})")
        if song.mood == user.favorite_mood:
            score += W_MOOD
            reasons.append(f"mood match: {song.mood} (+{W_MOOD:.1f})")

        energy_points = max(0.0, 1 - abs(user.target_energy - song.energy)) * 2.0
        score += energy_points
        reasons.append(
            f"energy {song.energy:.2f} vs target {user.target_energy:.2f} (+{energy_points:.2f})"
        )

        # likes_acoustic stands in for an acousticness target: True -> want 1.0,
        # False -> want 0.0. Weight matches the acousticness term in the recipe.
        acoustic_target = 1.0 if user.likes_acoustic else 0.0
        acoustic_points = max(0.0, 1 - abs(acoustic_target - song.acousticness)) * 1.5
        score += acoustic_points
        preference = "acoustic" if user.likes_acoustic else "non-acoustic"
        reasons.append(f"{preference} preference (+{acoustic_points:.2f})")

        return score, reasons

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top-k Songs ranked by score, tie-broken on energy."""
        ranked = sorted(
            self.songs,
            key=lambda s: (self._score(user, s)[0], s.energy),
            reverse=True,
        )
        return ranked[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a human-readable string of the song's score and its reasons."""
        score, reasons = self._score(user, song)
        joined = "; ".join(reasons) if reasons else "general fit"
        return f"Score {score:.2f} - {joined}"

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file, converting numeric fields to floats and id to int.
    Required by src/main.py
    """
    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["id"] = int(row["id"])
            for field in NUMERIC_FIELDS:
                row[field] = float(row[field])
            songs.append(row)
    print(f"Loaded songs: {len(songs)}")
    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences using the algorithm recipe.
    Continuous terms are only applied when the user provides that target, so
    partial profiles work too. Returns (score, reasons).
    Required by recommend_songs() and src/main.py
    """
    score = 0.0
    reasons: List[str] = []

    if user_prefs.get("favorite_genre") == song["genre"]:
        score += W_GENRE
        reasons.append(f"genre match: {song['genre']} (+{W_GENRE:.1f})")
    if user_prefs.get("favorite_mood") == song["mood"]:
        score += W_MOOD
        reasons.append(f"mood match: {song['mood']} (+{W_MOOD:.1f})")

    for pref_key, song_key, weight, is_tempo in CONTINUOUS_FEATURES:
        if pref_key not in user_prefs:
            continue
        target = user_prefs[pref_key]
        value = song[song_key]
        if is_tempo:
            similarity = 1 - abs(target - value) / TEMPO_RANGE
        else:
            similarity = 1 - abs(target - value)
        similarity = max(0.0, similarity)  # never let a far miss subtract points
        points = similarity * weight
        score += points
        label = song_key.replace("_", " ")
        reasons.append(f"{label} {value:g} vs target {target:g} (+{points:.2f})")

    return score, reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """
    Scores every song, ranks by score (tie-break on energy), returns top k as
    (song_dict, score, explanation) tuples.
    Required by src/main.py
    """
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        explanation = "; ".join(reasons) if reasons else "general fit"
        scored.append((song, score, explanation))

    scored.sort(key=lambda item: (item[1], item[0]["energy"]), reverse=True)
    return scored[:k]
