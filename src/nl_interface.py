"""
Natural-language interface for VibeCheck.

This is the RAG layer: a listener describes their taste in plain English,
an LLM call parses that into a structured taste profile, the existing
recommender scores and ranks the catalog against it (the retrieval step),
and a second LLM call writes a recommendation grounded only in those
retrieved scores and reasons.

If no Anthropic API key is configured, or an API call fails, everything
falls back to a rule-based path (keyword parsing + the recommender's own
explanation strings) so the app always runs end to end.
"""

import json
import logging
import os
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

MODEL_ID = os.environ.get("CLAUDE_MODEL", "claude-opus-5")

_ZERO_TO_ONE_FIELDS = (
    "target_energy",
    "target_acousticness",
    "target_valence",
    "target_danceability",
)


def _nullable(json_type: str) -> Dict:
    return {"anyOf": [{"type": json_type}, {"type": "null"}]}


_PROFILE_FIELDS = (
    "favorite_genre",
    "favorite_mood",
    "target_energy",
    "target_tempo_bpm",
    "target_acousticness",
    "target_valence",
    "target_danceability",
)

PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "favorite_genre": _nullable("string"),
        "favorite_mood": _nullable("string"),
        "target_energy": _nullable("number"),
        "target_tempo_bpm": _nullable("number"),
        "target_acousticness": _nullable("number"),
        "target_valence": _nullable("number"),
        "target_danceability": _nullable("number"),
        # Self-reported confidence (0-1) that the profile reflects the
        # request — this is the model's own reliability signal, logged
        # and surfaced by the reliability suite in src/reliability.py.
        "confidence": {"type": "number"},
    },
    "required": list(_PROFILE_FIELDS) + ["confidence"],
    "additionalProperties": False,
}

FALLBACK_NOTICE = (
    "[rule-based mode — set ANTHROPIC_API_KEY to enable natural-language understanding]"
)

# --- Keyword fallback parser (used with no API key, or if the API call fails) ---

_ENERGY_WORDS = {
    "chill": 0.30, "relax": 0.30, "calm": 0.25, "mellow": 0.30, "quiet": 0.25,
    "soft": 0.30, "sad": 0.30, "sleepy": 0.20, "study": 0.30,
    "intense": 0.90, "energetic": 0.90, "hype": 0.95, "pump": 0.92,
    "workout": 0.90, "loud": 0.85, "aggressive": 0.90, "party": 0.85,
}
_VALENCE_WORDS = {
    "sad": 0.15, "melancholy": 0.15, "moody": 0.30, "dark": 0.25,
    "happy": 0.85, "upbeat": 0.85, "joyful": 0.90, "fun": 0.80,
}
_ACOUSTIC_WORDS = {
    "acoustic": 0.85, "unplugged": 0.85, "folk": 0.75,
    "electric": 0.10, "electronic": 0.05, "synth": 0.10,
}


def _keyword_fallback_parse(text: str, known_genres: List[str], known_moods: List[str]) -> Tuple[Dict, float]:
    """
    Cheap heuristic parser used when the LLM path is unavailable.

    Returns (profile, confidence). Confidence here is a coverage proxy —
    the fraction of the 7 possible profile fields this parser managed to
    fill in — not a self-assessment like the LLM path's. It's deliberately
    capped lower than the LLM path can reach, since keyword matching can
    only ever populate 5 of the 7 fields (never tempo or danceability).
    """
    lowered = text.lower()
    profile: Dict = {}

    for genre in sorted(known_genres, key=len, reverse=True):
        if genre in lowered:
            profile["favorite_genre"] = genre
            break

    for mood in sorted(known_moods, key=len, reverse=True):
        if mood in lowered:
            profile["favorite_mood"] = mood
            break

    for word, value in _ENERGY_WORDS.items():
        if word in lowered:
            profile["target_energy"] = value
            break
    for word, value in _VALENCE_WORDS.items():
        if word in lowered:
            profile["target_valence"] = value
            break
    for word, value in _ACOUSTIC_WORDS.items():
        if word in lowered:
            profile["target_acousticness"] = value
            break

    confidence = len(profile) / len(_PROFILE_FIELDS)
    return profile, round(confidence, 2)


def _client_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _sanitize_profile(raw: Dict, known_genres: List[str], known_moods: List[str]) -> Dict:
    """
    Guardrail: validate and clamp LLM output before it ever reaches the
    scorer. Unknown genres/moods and out-of-range numbers are dropped or
    clamped rather than trusted verbatim.
    """
    profile: Dict = {}

    genre = raw.get("favorite_genre")
    if isinstance(genre, str) and genre.lower() in known_genres:
        profile["favorite_genre"] = genre.lower()

    mood = raw.get("favorite_mood")
    if isinstance(mood, str) and mood.lower() in known_moods:
        profile["favorite_mood"] = mood.lower()

    for field in _ZERO_TO_ONE_FIELDS:
        value = raw.get(field)
        if isinstance(value, (int, float)):
            profile[field] = round(_clamp01(value), 2)

    tempo = raw.get("target_tempo_bpm")
    if isinstance(tempo, (int, float)) and 40 <= tempo <= 220:
        profile["target_tempo_bpm"] = float(tempo)

    return profile


def parse_taste_description(
    text: str, known_genres: List[str], known_moods: List[str]
) -> Tuple[Dict, bool, float]:
    """
    Turn a free-text taste description into a structured taste profile.

    Returns (profile, used_llm, confidence). Tries the Claude API first;
    falls back to a keyword heuristic if no API key is configured or the
    call fails, so the recommender always has a profile to score against.

    `confidence` (0-1) is a reliability signal: on the LLM path it's the
    model's own self-assessment (part of PROFILE_SCHEMA); on the fallback
    path it's a coverage proxy computed by _keyword_fallback_parse. The two
    are not directly comparable — see src/reliability.py, which measures
    both against known-answer test cases.
    """
    if not _client_available():
        logger.info("ANTHROPIC_API_KEY not set; using keyword fallback parser")
        profile, confidence = _keyword_fallback_parse(text, known_genres, known_moods)
        return profile, False, confidence

    try:
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=MODEL_ID,
            max_tokens=1024,
            system=(
                "You convert a listener's free-text music taste description into a "
                "structured taste profile for a recommender system. Only use a genre "
                f"from this exact list, or null if none fits: {', '.join(known_genres)}. "
                "Only use a mood from this exact list, or null if none fits: "
                f"{', '.join(known_moods)}. Leave a numeric field null if the text gives "
                "no signal for it. Numeric targets are on a 0-1 scale except "
                "target_tempo_bpm, which is beats per minute, roughly 40-220. Also include "
                "a confidence field (0-1): how confident you are that this profile "
                "correctly reflects the listener's request. Use a lower value when the "
                "request is vague, contradictory, or gives little genre/mood/energy signal."
            ),
            output_config={"format": {"type": "json_schema", "schema": PROFILE_SCHEMA}},
            messages=[{"role": "user", "content": text}],
        )
        raw_text = next(b.text for b in response.content if b.type == "text")
        raw = json.loads(raw_text)
        profile = _sanitize_profile(raw, known_genres, known_moods)
        confidence = _clamp01(raw.get("confidence", 0.5))
        logger.info(
            "Parsed taste profile via %s: %s (confidence=%.2f)", MODEL_ID, profile, confidence
        )
        return profile, True, confidence
    except Exception:
        logger.warning(
            "LLM taste-profile parsing failed; falling back to keyword parser", exc_info=True
        )
        profile, confidence = _keyword_fallback_parse(text, known_genres, known_moods)
        return profile, False, confidence


def _fallback_summary(recommendations: List[Tuple[Dict, float, str]]) -> str:
    lines = [FALLBACK_NOTICE, ""]
    for rank, (song, score, reasons) in enumerate(recommendations, start=1):
        lines.append(f"{rank}. {song['title']} by {song['artist']} (score {score:.2f}) — {reasons}")
    return "\n".join(lines)


def generate_explanation(user_text: str, recommendations: List[Tuple[Dict, float, str]]) -> str:
    """
    Write a natural-language recommendation grounded in the retrieved
    (song, score, reasons) tuples. Falls back to a rule-based summary of
    those same tuples if no API key is set or the call fails.
    """
    if not _client_available():
        return _fallback_summary(recommendations)

    try:
        import anthropic

        client = anthropic.Anthropic()
        retrieved = "\n".join(
            f"{i + 1}. {song['title']} by {song['artist']} "
            f"(genre={song['genre']}, mood={song['mood']}, score={score:.2f}) — {reasons}"
            for i, (song, score, reasons) in enumerate(recommendations)
        )
        response = client.messages.create(
            model=MODEL_ID,
            max_tokens=1024,
            system=(
                "You are a friendly music recommender. You are given a listener's "
                "request and a ranked list of songs retrieved from a scoring engine, "
                "each with its numeric score and the specific reasons it earned that "
                "score. Write a short recommendation (4-6 sentences) grounded ONLY in "
                "the retrieved songs and reasons below. Do not invent songs, genres, "
                "artists, or facts that are not present in the list."
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"Listener request: {user_text}\n\nRetrieved songs:\n{retrieved}",
                }
            ],
        )
        text = next(b.text for b in response.content if b.type == "text")
        return text.strip()
    except Exception:
        logger.warning(
            "LLM explanation generation failed; falling back to rule-based summary", exc_info=True
        )
        return _fallback_summary(recommendations)
