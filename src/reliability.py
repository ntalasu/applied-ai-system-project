"""
Reliability suite for the natural-language (RAG) taste-parsing feature.

Each case is a free-text taste request plus a checkable expectation about
the structured profile parse_taste_description() should produce. This is
the single source of truth for those cases — both the automated pytest
suite (tests/test_reliability.py) and the standalone report script
(scripts/reliability_report.py) run the exact same list, so "run the
tests" and "see the reliability numbers" are never two different things.

Includes edge cases (empty input, no clear signal, contradictory requests)
specifically because those are where a rule-based fallback and an LLM are
most likely to diverge or fail outright.
"""

import os
from dataclasses import dataclass
from typing import Callable, Dict, List

from src.nl_interface import parse_taste_description
from src.recommender import load_songs

_DEFAULT_SONGS_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "songs.csv")

_ALLOWED_PROFILE_KEYS = {
    "favorite_genre",
    "favorite_mood",
    "target_energy",
    "target_tempo_bpm",
    "target_acousticness",
    "target_valence",
    "target_danceability",
}


@dataclass
class ReliabilityCase:
    label: str
    text: str
    criteria: str
    check: Callable[[Dict], bool]


CASES: List[ReliabilityCase] = [
    ReliabilityCase(
        label="workout request -> high energy",
        text="I want something to pump me up before a workout, high energy and loud",
        criteria="target_energy >= 0.7",
        check=lambda p: p.get("target_energy", 0.0) >= 0.7,
    ),
    ReliabilityCase(
        label="mellow acoustic request -> low energy, high acousticness",
        text="Something mellow and acoustic for a rainy afternoon of studying",
        criteria="target_energy <= 0.5 and target_acousticness >= 0.6",
        check=lambda p: p.get("target_energy", 1.0) <= 0.5 and p.get("target_acousticness", 0.0) >= 0.6,
    ),
    ReliabilityCase(
        label="explicit genre + mood -> extracted verbatim",
        text="Upbeat happy pop, kind of like a summer road trip",
        criteria="favorite_genre == 'pop' and favorite_mood == 'happy'",
        check=lambda p: p.get("favorite_genre") == "pop" and p.get("favorite_mood") == "happy",
    ),
    ReliabilityCase(
        label="vague request, no clear signal -> no crash, no invented keys",
        text="play me some music",
        criteria="returns a dict with only known profile keys",
        check=lambda p: isinstance(p, dict) and set(p).issubset(_ALLOWED_PROFILE_KEYS),
    ),
    ReliabilityCase(
        label="empty string -> handled gracefully",
        text="",
        criteria="returns a dict, does not raise",
        check=lambda p: isinstance(p, dict),
    ),
    ReliabilityCase(
        label="contradictory request -> handled without crashing",
        text="sad rainy lofi vibes but I also want to dance all night",
        criteria="returns a dict with only known profile keys, does not raise",
        check=lambda p: isinstance(p, dict) and set(p).issubset(_ALLOWED_PROFILE_KEYS),
    ),
]


def _known_genres_and_moods(songs_csv: str):
    songs = load_songs(songs_csv)
    genres = sorted({song["genre"] for song in songs})
    moods = sorted({song["mood"] for song in songs})
    return genres, moods


def run_reliability_suite(songs_csv: str = _DEFAULT_SONGS_CSV) -> List[Dict]:
    """
    Runs every case in CASES through parse_taste_description() and returns
    one result dict per case, each with: label, text, criteria, mode
    (LLM/keyword fallback), confidence, the parsed profile, and pass/fail.
    """
    known_genres, known_moods = _known_genres_and_moods(songs_csv)
    results = []

    for case in CASES:
        profile, used_llm, confidence = parse_taste_description(case.text, known_genres, known_moods)
        try:
            passed = bool(case.check(profile))
        except Exception:
            passed = False

        results.append(
            {
                "label": case.label,
                "text": case.text,
                "criteria": case.criteria,
                "mode": "LLM" if used_llm else "keyword fallback",
                "confidence": confidence,
                "profile": profile,
                "passed": passed,
            }
        )

    return results
