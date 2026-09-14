"""Build evals/contracts/*.txt from real repo materials (no invented text).

- employment_sample.txt: the 10 clauses of documents/sample_employment_contract.html
- fair_sample.txt: 10 fair clauses from backend/clause_library/fair_clauses.json
- supplier_sample.txt: 10 supplier_* fair clauses from the same library

Usage (from repo root):
    python3 evals/build_contracts.py
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "evals" / "contracts"
OUT.mkdir(parents=True, exist_ok=True)


def build_employment():
    html = (REPO_ROOT / "documents" / "sample_employment_contract.html").read_text(encoding="utf-8")
    items = re.findall(r"<li>(.*?)</li>", html, re.DOTALL)
    assert len(items) == 10, f"expected 10 clauses, found {len(items)}"
    blocks = ["EMPLOYMENT AGREEMENT between ABC Corp Ltd. (Employer) and the undersigned (Employee).", ""]
    for i, item in enumerate(items, start=1):
        title = re.search(r"<h2>(.*?)</h2>", item, re.DOTALL).group(1).strip()
        body = re.search(r"<p>(.*?)</p>", item, re.DOTALL).group(1).strip()
        body = re.sub(r"<.*?>", "", body)
        blocks.append(f"{i}. {title}\n{body}")
    (OUT / "employment_sample.txt").write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    print(f"employment_sample.txt: {len(items)} clauses")


def build_from_library(filename, wanted_types):
    clauses = json.loads(
        (REPO_ROOT / "backend" / "clause_library" / "fair_clauses.json").read_text(encoding="utf-8")
    )
    picked = [c for c in clauses if c.get("type") in wanted_types]
    assert len(picked) >= 10, f"only {len(picked)} clauses for {wanted_types}"
    picked = picked[:10]
    blocks = [f"SAMPLE CONTRACT (fair clauses from clause_library/fair_clauses.json).", ""]
    for i, c in enumerate(picked, start=1):
        blocks.append(f"{i}. {c['title']}\n{c['content']}")
    (OUT / filename).write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    print(f"{filename}: {len(picked)} clauses")


def main():
    build_employment()
    build_from_library("fair_sample.txt", [
        "payment", "termination", "liability", "confidentiality",
        "intellectual_property", "employment_notice", "employment_salary",
        "employment_confidentiality", "employment_termination", "employment_hours",
    ])
    build_from_library("supplier_sample.txt", [
        "supplier_payment", "supplier_delivery", "supplier_pricing",
        "supplier_quality", "supplier_warranty", "supplier_dlp",
        "supplier_liability", "supplier_indemnity", "supplier_termination",
        "supplier_force_majeure",
    ])


if __name__ == "__main__":
    main()
