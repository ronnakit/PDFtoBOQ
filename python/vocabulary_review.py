"""
vocabulary_review -- the low-friction human-in-the-loop worklist for terms
"ไพน้อย" doesn't recognize yet. See ../../../09-vocabulary-review-workflow.md
for the full design and why this exists (short version: every drafter/company
names things differently, and the person running this tool shouldn't have to
hand-edit JSON or Python to teach the system a new word).

record_unknowns() is called by classify_layers.py every run. It appends any
newly-seen unknown term to ../../../vocabulary_review.csv (a plain CSV so it
opens directly in Excel) and bumps the occurrence count for ones already
there -- it never overwrites columns a human has already filled in.

apply_vocabulary_review.py is the other half: it reads rows the human has
filled in (status=confirmed) and merges them into 04-category-schema.md
automatically, so the whole loop -- scan, review in a spreadsheet, apply --
never requires touching code or hand-editing JSON.
"""

import csv
from pathlib import Path

CSV_PATH = Path(__file__).parent / ".." / ".." / ".." / "vocabulary_review.csv"

FIELDNAMES = [
    "term", "kind", "first_seen_file", "last_seen_file", "times_seen",
    "target_category", "action", "status", "notes",
]


def _load_rows() -> dict[tuple[str, str], dict]:
    if not CSV_PATH.exists():
        return {}
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return {(row["term"], row["kind"]): row for row in csv.DictReader(f)}


def _save_rows(rows: dict[tuple[str, str], dict]) -> None:
    ordered = sorted(rows.values(), key=lambda r: (r["status"] != "pending", r["kind"], r["term"]))
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(ordered)


def record_unknowns(kind: str, terms: list[str], source_file: str) -> None:
    """kind: 'layer' or 'block'. Never overwrites target_category/action/status/notes
    once a human has set them -- only bumps times_seen/last_seen_file for repeats."""
    rows = _load_rows()
    for term in terms:
        key = (term, kind)
        if key in rows:
            row = rows[key]
            row["times_seen"] = str(int(row.get("times_seen", "1") or 1) + 1)
            row["last_seen_file"] = source_file
        else:
            rows[key] = {
                "term": term,
                "kind": kind,
                "first_seen_file": source_file,
                "last_seen_file": source_file,
                "times_seen": "1",
                "target_category": "",
                "action": "",
                "status": "pending",
                "notes": "",
            }
    _save_rows(rows)
