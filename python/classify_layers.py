"""
classify_layers -- run Layer Exclusion (07-drawing-signal-vs-noise.md) and the
Master Category Schema (04-category-schema.md) against a real DXF's layer/block
names, and report what falls through both nets ("unknown"). This is the piece
of Step 1.5 / Step 6 (03-ai-boq-procedure.md) that decides what still needs a
human to look at before "ไพน้อย" is allowed to take off quantities from it.

Usage:
    python classify_layers.py "../../new house/cad/newhouse 2569.dxf"
"""

import argparse
import sys
from pathlib import Path

import ezdxf

sys.path.insert(0, str(Path(__file__).parent))
from pynoi_parser import _token_aware_match, is_excluded_layer  # noqa: E402
from schema_loader import load_schema  # noqa: E402
from vocabulary_review import record_unknowns  # noqa: E402

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def build_lookup(schema: dict) -> list[tuple[str, str, str]]:
    """-> list of (needle, category_code, category_name) -- longest needles first
    so a more specific match (e.g. a sub_category keyword) isn't shadowed."""
    entries = []
    for cat in schema["master_categories"]:
        code, name = cat["code"], cat["name"]
        for needle in cat.get("cad_search_layers", []) + cat.get("keywords", []):
            entries.append((needle, code, name))
        for sub in cat.get("sub_categories", []):
            for needle in sub.get("keywords", []):
                entries.append((needle, code, f"{name} > {sub['code']} {sub['name']}"))
    entries.sort(key=lambda e: len(e[0]), reverse=True)
    return entries


def classify(name: str, lookup: list[tuple[str, str, str]]) -> tuple[str, str] | None:
    for needle, code, cat_name in lookup:
        if _token_aware_match(needle, name):
            return code, cat_name
    return None


def collect_names(doc) -> tuple[list[str], list[str]]:
    layers = [layer.dxf.name for layer in doc.layers]
    blocks = [b.name for b in doc.blocks if not b.name.startswith("*")]
    return sorted(set(layers)), sorted(set(blocks))


def report(kind: str, names: list[str], lookup: list[tuple[str, str, str]], source_file: str, extra_exclude=None) -> list[str]:
    excluded, categorized, unknown = [], [], []
    for name in names:
        if is_excluded_layer(name, extra_exclude):
            excluded.append(name)
            continue
        hit = classify(name, lookup)
        if hit:
            categorized.append((name, *hit))
        else:
            unknown.append(name)

    print(f"\n=== {kind}: {len(names)} total -- {len(excluded)} excluded, {len(categorized)} categorized, {len(unknown)} UNKNOWN ===")
    print(f"\n-- excluded ({len(excluded)}) --")
    for n in excluded:
        print(f"  {n}")
    print(f"\n-- categorized ({len(categorized)}) --")
    for n, code, cat_name in categorized:
        print(f"  {n}  ->  [{code}] {cat_name}")
    print(f"\n-- UNKNOWN, needs a human ({len(unknown)}) --")
    for n in unknown:
        print(f"  {n}")

    record_unknowns(kind.lower().rstrip("s"), unknown, source_file)
    return unknown


def main() -> None:
    ap = argparse.ArgumentParser(description="classify DXF layers/blocks against exclusion + category schema")
    ap.add_argument("file", type=Path)
    args = ap.parse_args()

    doc = ezdxf.readfile(str(args.file))
    schema = load_schema()
    lookup = build_lookup(schema)
    layers, blocks = collect_names(doc)

    unknown_layers = report("LAYERS", layers, lookup, args.file.name)
    unknown_blocks = report("BLOCKS", blocks, lookup, args.file.name)

    print(f"\n=== SUMMARY: {len(unknown_layers)} unknown layers, {len(unknown_blocks)} unknown blocks ===")
    print(f"New/updated rows written to {'vocabulary_review.csv'} -- fill in the 'target_category'/'action' columns for status=pending rows, then run apply_vocabulary_review.py")


if __name__ == "__main__":
    main()
