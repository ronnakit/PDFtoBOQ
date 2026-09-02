"""
investigate_terms -- the numeric version of "a human looks at a shape and
reads the label sitting next to it." For a given list of block names, reports:
  - geometric signature (bounding box size, aspect ratio) of the block
    definition itself
  - the nearest TEXT/MTEXT entity to each instance actually placed in the
    drawing, and how far away it is

This does NOT decide anything or touch the schema -- it only gathers
evidence for a human to review (see 09-vocabulary-review-workflow.md).
Scoped deliberately to a short, explicit list of terms per run rather than
"investigate everything" -- see BACKLOG.md for why (pacing).

Usage:
    python investigate_terms.py "../../new house/cad/newhouse 2569.dxf" C053S C106P C112S
"""

import argparse
import sys
from pathlib import Path

import ezdxf
import ezdxf.bbox as bbox

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def block_signature(doc, name: str) -> str:
    if name not in doc.blocks:
        return "(not a block definition)"
    entities = list(doc.blocks[name])
    if not entities:
        return "(empty block)"
    try:
        box = bbox.extents(entities)
    except Exception:
        return f"({len(entities)} entities, bbox unavailable)"
    if box is None or not box.has_data:
        return f"({len(entities)} entities, no measurable geometry)"
    w = box.extmax.x - box.extmin.x
    h = box.extmax.y - box.extmin.y
    ratio = (w / h) if h else float("inf")
    shape = "square-ish" if 0.7 <= ratio <= 1.4 else ("wide" if ratio > 1.4 else "tall")
    return f"{len(entities)} entities, bbox {w:.1f}x{h:.1f} ({shape}, ratio {ratio:.2f})"


def nearest_text(msp, point, texts: list) -> tuple[str, float] | None:
    best = None
    for txt, pos in texts:
        d = ((pos[0] - point[0]) ** 2 + (pos[1] - point[1]) ** 2) ** 0.5
        if best is None or d < best[1]:
            best = (txt, d)
    return best


def main() -> None:
    ap = argparse.ArgumentParser(description="geometric signature + nearest-text evidence for block names")
    ap.add_argument("file", type=Path)
    ap.add_argument("terms", nargs="+", help="block names to investigate")
    args = ap.parse_args()

    doc = ezdxf.readfile(str(args.file))
    msp = doc.modelspace()

    texts = []
    for e in msp:
        if e.dxftype() in ("TEXT", "MTEXT"):
            txt = e.plain_text() if hasattr(e, "plain_text") else getattr(e, "text", "")
            if txt.strip():
                texts.append((txt.strip(), tuple(e.dxf.insert)))

    for name in args.terms:
        print(f"\n=== {name} ===")
        print(f"  shape: {block_signature(doc, name)}")
        inserts = [e for e in msp if e.dxftype() == "INSERT" and e.dxf.name == name]
        if not inserts:
            print("  no INSERT instances found in modelspace")
            continue
        print(f"  {len(inserts)} instance(s), layers used: {sorted({e.dxf.layer for e in inserts})}")
        for e in inserts[:3]:
            hit = nearest_text(msp, tuple(e.dxf.insert), texts)
            if hit:
                print(f"    @ {tuple(round(v, 1) for v in e.dxf.insert)} -- nearest text: {hit[0]!r} ({hit[1]:.1f} units away)")
            else:
                print(f"    @ {tuple(round(v, 1) for v in e.dxf.insert)} -- no text found anywhere in the file")
        if len(inserts) > 3:
            print(f"    ... and {len(inserts) - 3} more instance(s), not shown")


if __name__ == "__main__":
    main()
