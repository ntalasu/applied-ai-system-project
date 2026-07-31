import pytest

from src.reliability import run_reliability_suite

# Runs once at collection time. In fallback mode (no ANTHROPIC_API_KEY) this
# is fully deterministic and offline; with a key set, the exact same cases
# exercise the live LLM parsing path instead.
_RESULTS = run_reliability_suite()


@pytest.mark.parametrize("result", _RESULTS, ids=[r["label"] for r in _RESULTS])
def test_reliability_case(result):
    assert result["passed"], (
        f"criteria failed: {result['criteria']!r} for input {result['text']!r} -> "
        f"parsed profile {result['profile']} (mode={result['mode']}, "
        f"confidence={result['confidence']:.2f})"
    )


def test_confidence_scores_are_in_valid_range():
    for result in _RESULTS:
        assert 0.0 <= result["confidence"] <= 1.0, result
