"""
apply_vocabulary_review -- merge human-confirmed rows from vocabulary_review.csv
into 04-category-schema.md automatically. This is the second half of the loop
described in vocabulary_review.py / 09-vocabulary-review-workflow.md: fill in
target_category/action/status in the CSV (in Excel or any text editor), run
this script, and the schema file's ```json block is updated in place --
no hand-editing of JSON, no code changes.

Row contract (see vocabulary_review.CSV columns):
  status must be exactly "confirmed" to be picked up.
  action:
    "classify" -- append `term` to the keywords list of `target_category`
                  (a master category code like "3", or "3.1" for a sub_category)
    "exclude"  -- append `term` to exclusion_rules.keywords (it's noise, not signal)
    "ignore"   -- no schema change; just marks the row applied (e.g. confirmed-unused
                  block definitions that don't need classifying at all)
Rows are marked status="applied" after a successful merge so re-running this
script is safe (idempotent) -- already-applied rows are skipped.

Usage:
    python apply_vocabulary_review.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from schema_loader import SCHEMA_PATH, load_schema  # noqa: E402
from vocabulary_review import _load_rows, _save_rows  # noqa: E402

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def find_category(schema: dict, target_category: str) -> tuple[dict, str]:
    """target_category '3' -> master category dict; '3.1' -> its sub_category dict.
    Returns (dict_to_append_keywords_to, human-readable label) or raises KeyError."""
    top_code = target_category.split(".")[0]
    for cat in schema["master_categories"]:
        if cat["code"] == top_code:
            if "." in target_category:
                for sub in cat.get("sub_categories", []):
                    if sub["code"] == target_category:
                        return sub, f"{cat['name']} > {sub['code']} {sub['name']}"
                raise KeyError(f"sub_category {target_category} not found under category {top_code}")
            return cat, cat["name"]
    raise KeyError(f"master category {top_code} not found")


def apply_row(schema: dict, row: dict) -> str:
    """Mutates schema in place. Returns a short log message."""
    term, action, target = row["term"], row["action"], row["target_category"]
    if action == "ignore":
        return f"{term}: ignored (no schema change)"
    if action == "exclude":
        keywords = schema["exclusion_rules"]["keywords"]
        if term not in keywords:
            keywords.append(term)
        return f"{term}: added to exclusion_rules.keywords"
    if action == "classify":
        if not target:
            raise ValueError(f"{term}: action=classify but target_category is empty")
        node, label = find_category(schema, target)
        keywords = node.setdefault("keywords", [])
        if term not in keywords:
            keywords.append(term)
        return f"{term}: added to {label}"
    raise ValueError(f"{term}: unknown action {action!r} (expected classify/exclude/ignore)")


def write_schema(schema: dict, path: Path = SCHEMA_PATH) -> None:
    """Splice the new JSON in by string position, NOT re.sub(pattern, string, text) --
    re.sub interprets backslashes in a *string* replacement specially (\\1, \\g<...>),
    which silently halves every literal backslash in regex patterns stored in the
    schema (this corrupted the file once already: '\\.' became '\\' -> invalid JSON,
    caught only because the next validation run happened to fail loudly)."""
    text = path.read_text(encoding="utf-8")
    match = re.search(r"```json\n.*?\n```", text, flags=re.S)
    if not match:
        raise ValueError(f"no ```json fenced block found in {path}")
    new_json = json.dumps(schema, ensure_ascii=False, indent=2)
    new_text = text[: match.start()] + f"```json\n{new_json}\n```" + text[match.end() :]
    path.write_text(new_text, encoding="utf-8")


def main() -> None:
    rows = _load_rows()
    to_apply = [r for r in rows.values() if r["status"] == "confirmed"]
    if not to_apply:
        print("No rows with status=confirmed -- nothing to apply.")
        return

    schema = load_schema()
    applied = []
    for row in to_apply:
        try:
            msg = apply_row(schema, row)
        except (KeyError, ValueError) as e:
            print(f"[skip] {e}")
            continue
        print(f"[applied] {msg}")
        row["status"] = "applied"
        applied.append(row)

    if not applied:
        print("Nothing applied (all rows failed validation -- see [skip] messages above).")
        return

    write_schema(schema)
    _save_rows(rows)
    print(f"\n{len(applied)} row(s) merged into 04-category-schema.md and marked status=applied in vocabulary_review.csv")


if __name__ == "__main__":
    main()
