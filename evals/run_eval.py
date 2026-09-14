"""ContractGuard eval: risky-clause detection + reviewer agreement.

Pipeline per clause (same code as production):
  1. PDFExtractor.segment_clauses (deterministic, no LLM)
  2. scan_red_flags on the clause (deterministic regex)
  3. ContractAnalyzer.analyze_clause (LLM when keys exist, else the
     Medium/50 heuristic fallback with needs_human_review=True)

Labels: evals/labels.jsonl (single reviewer — the repo owner; rationale
per clause). Risky = expected High or Medium.

Metrics:
  - scanner precision/recall on risky (CRITICAL/HIGH regex hit)
  - llm reviewer agreement (risk_level == expected)
  - needs_human_review rate (the confidence-threshold path firing)

Modes:
  offline (default): no API keys needed; exercises fallback + review flag.
  --live: uses GROQ/GEMINI keys for real LLM scoring.

Usage (from repo root):
    backend/venv/bin/python evals/run_eval.py [--live] [--min-precision 0.5]
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.config import settings  # noqa: E402
from app.services.llm_service import ContractAnalyzer  # noqa: E402
from app.services.pdf_extractor import PDFExtractor  # noqa: E402
from app.skills.redflag_scanner import scan_red_flags  # noqa: E402

EVALS = REPO_ROOT / "evals"
CONTRACT_TYPES = {
    "employment_sample": "employment_contract",
    "fair_sample": "employment_contract",
    "supplier_sample": "supplier_contract",
}
RISKY_SEV = {"CRITICAL", "HIGH"}


def load_labels():
    labels = {}
    for line in (EVALS / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            labels[(item["contract"], item["clause_id"])] = item
    return labels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--min-high-recall", type=float, default=0.85)
    args = parser.parse_args()

    live = args.live and (settings.has_groq or settings.has_gemini)
    print(f"Mode: {'LIVE (keys present)' if live else 'OFFLINE (heuristic fallback)'}")
    if args.live and not live:
        print("WARNING: --live requested but no GROQ/GEMINI key configured; running offline.")
    if not live:
        # Force the fallback path in-process: backend/.env may hold real keys,
        # which would otherwise burn minutes on network retries per clause.
        settings.GROQ_API_KEY = ""
        settings.GEMINI_API_KEY = ""

    labels = load_labels()
    extractor = PDFExtractor()
    analyzer = ContractAnalyzer()
    rows = []

    for contract, ctype in CONTRACT_TYPES.items():
        text = (EVALS / "contracts" / f"{contract}.txt").read_text(encoding="utf-8")
        for clause in extractor.segment_clauses(text):
            key = (contract, clause["id"])
            if key not in labels:
                continue  # preamble/segmentation residue outside the label set
            label = labels[key]
            findings = [
                f for f in scan_red_flags(clause["content"], ctype)
                if f["category"] != "Missing Clause"
            ]
            scanner_risky = any(f["severity"] in RISKY_SEV for f in findings)
            scored = analyzer.analyze_clause(clause)
            rows.append({
                "contract": contract,
                "clause_id": clause["id"],
                "expected": label["expected"],
                "scanner_risky": scanner_risky,
                "scanner_sev": sorted({f["severity"] for f in findings}),
                "llm_level": scored["risk_level"],
                "confidence": scored["confidence"],
                "needs_review": scored["needs_human_review"],
            })

    assert len(rows) == len(labels), f"segmented {len(rows)} labeled clauses, want {len(labels)}"

    def risky(exp):
        return exp in ("High", "Medium")

    tp = sum(1 for r in rows if r["scanner_risky"] and risky(r["expected"]))
    fp = sum(1 for r in rows if r["scanner_risky"] and not risky(r["expected"]))
    fn = sum(1 for r in rows if not r["scanner_risky"] and risky(r["expected"]))
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    agreement = sum(1 for r in rows if r["llm_level"] == r["expected"]) / len(rows)
    review_rate = sum(1 for r in rows if r["needs_review"]) / len(rows)
    # Safety gate: an expected-High clause must never pass silently. Caught if
    # the scanner fires OR the LLM rates it above Low.
    highs = [r for r in rows if r["expected"] == "High"]
    high_recall = (
        sum(1 for r in highs if r["scanner_risky"] or r["llm_level"] != "Low") / len(highs)
        if highs else 1.0
    )

    print(f"\nContracts: {len(CONTRACT_TYPES)}, labeled clauses: {len(rows)}")
    print(f"Scanner risky-clause precision: {precision:.2f} ({tp}tp/{fp}fp)")
    print(f"Scanner risky-clause recall:    {recall:.2f} ({tp}tp/{fn}fn)")
    print(f"LLM reviewer agreement:         {agreement:.2f}")
    print(f"Flagged for human review:       {review_rate:.2f}")
    print("\nPer-contract agreement:")
    by_contract = Counter()
    for r in rows:
        by_contract[(r["contract"], r["llm_level"] == r["expected"])] += 1
    for contract in CONTRACT_TYPES:
        ok = by_contract[(contract, True)]
        print(f"  {contract}: {ok}/10 llm-label agreement")

    misses = [r for r in rows if (r["scanner_risky"] != risky(r["expected"]))]
    if misses:
        print(f"\nScanner disagreements ({len(misses)}):")
        for r in misses[:10]:
            print(f"  {r['contract']}/{r['clause_id']}: expected={r['expected']} "
                  f"scanner_risky={r['scanner_risky']} llm={r['llm_level']}")

    (EVALS / "results.json").write_text(json.dumps({
        "mode": "live" if live else "offline",
        "contracts": len(CONTRACT_TYPES),
        "clauses": len(rows),
        "scanner_precision": round(precision, 3),
        "scanner_recall": round(recall, 3),
        "llm_agreement": round(agreement, 3),
        "high_recall": round(high_recall, 3),
        "review_rate": round(review_rate, 3),
    }, indent=2), encoding="utf-8")

    print(f"High-risk recall (scanner OR llm != Low): {high_recall:.2f}")
    ok = high_recall >= args.min_high_recall
    print("EVAL " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
