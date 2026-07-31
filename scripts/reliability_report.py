"""
Standalone reliability report for the natural-language (RAG) parsing feature.

Run with:
    python -m scripts.reliability_report

Prints a per-case pass/fail table (Test Input | Evaluation Criteria | Mode |
Confidence | Result) plus a one-line summary — this is the "prove it works"
artifact for the AI feature, runnable in seconds with no API key required
(it exercises the live LLM path automatically if ANTHROPIC_API_KEY is set).
"""

from src.reliability import run_reliability_suite


def main() -> None:
    results = run_reliability_suite()

    print("| Test Input | Evaluation Criteria | Mode | Confidence | Result |")
    print("|---|---|---|---|---|")
    for result in results:
        text = result["text"] if result["text"] else "(empty string)"
        status = "Pass" if result["passed"] else "Fail"
        print(
            f"| {text} | {result['criteria']} | {result['mode']} | "
            f"{result['confidence']:.2f} | {status} |"
        )

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    avg_confidence = sum(r["confidence"] for r in results) / total if total else 0.0

    print()
    print(f"{passed} out of {total} tests passed. Confidence scores averaged {avg_confidence:.2f}.")

    failures = [r for r in results if not r["passed"]]
    if failures:
        print("\nFailed cases:")
        for r in failures:
            print(f"  - {r['label']}: got {r['profile']} (mode={r['mode']})")


if __name__ == "__main__":
    main()
