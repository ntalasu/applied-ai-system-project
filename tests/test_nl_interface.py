import pytest

from src.nl_interface import (
    FALLBACK_NOTICE,
    _keyword_fallback_parse,
    _sanitize_profile,
    generate_explanation,
    parse_taste_description,
)

KNOWN_GENRES = ["pop", "lofi", "rock", "ambient"]
KNOWN_MOODS = ["happy", "chill", "intense", "relaxed"]


def test_keyword_fallback_parse_extracts_genre_mood_and_energy():
    profile, confidence = _keyword_fallback_parse(
        "I want something loud and intense, like rock but energetic",
        KNOWN_GENRES,
        KNOWN_MOODS,
    )
    assert profile["favorite_genre"] == "rock"
    assert profile["favorite_mood"] == "intense"
    assert profile["target_energy"] > 0.7
    assert confidence == pytest.approx(3 / 7, abs=0.01)


def test_keyword_fallback_parse_handles_no_signal():
    profile, confidence = _keyword_fallback_parse("play me some music", KNOWN_GENRES, KNOWN_MOODS)
    assert profile == {}
    assert confidence == 0.0


def test_parse_taste_description_without_api_key_uses_fallback(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    profile, used_llm, confidence = parse_taste_description(
        "something chill and acoustic for studying", KNOWN_GENRES, KNOWN_MOODS
    )
    assert used_llm is False
    assert profile["favorite_mood"] == "chill"
    assert 0.0 <= confidence <= 1.0


def test_sanitize_profile_drops_unknown_genre_and_clamps_numbers():
    raw = {
        "favorite_genre": "kpop",  # not in known_genres -> dropped
        "favorite_mood": "happy",
        "target_energy": 1.5,  # out of range -> clamped to 1.0
        "target_tempo_bpm": 999,  # out of range -> dropped
        "target_acousticness": None,
        "target_valence": 0.4,
        "target_danceability": None,
    }
    profile = _sanitize_profile(raw, KNOWN_GENRES, KNOWN_MOODS)
    assert "favorite_genre" not in profile
    assert profile["favorite_mood"] == "happy"
    assert profile["target_energy"] == 1.0
    assert "target_tempo_bpm" not in profile
    assert profile["target_valence"] == 0.4


def test_generate_explanation_without_api_key_falls_back_to_summary(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    song = {"title": "Test Song", "artist": "Test Artist", "genre": "pop", "mood": "happy"}
    recommendations = [(song, 4.5, "genre match: pop (+2.0)")]

    explanation = generate_explanation("upbeat happy pop", recommendations)

    assert FALLBACK_NOTICE in explanation
    assert "Test Song" in explanation
    assert "Test Artist" in explanation
