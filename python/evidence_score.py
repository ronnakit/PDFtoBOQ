"""
evidence_score -- code version of the principle in 07-drawing-signal-vs-noise.md
§14: default every ambiguous block to "not counted" until it earns inclusion.

Implements 2 of the 3 evidence criteria (the third, matching a human-authored
Legend/Schedule table, needs Step 3 of the SOP -- legend parsing -- which
isn't built yet; this deliberately does NOT try to fake that one):

  (2) has clear descriptive text near an instance (not a dimension number or
      a short generic scribble)
  (3) shows a consistent repeating placement pattern (several instances,
      all on the same layer -- not scattered across unrelated contexts)

verdict() defaults to "insufficient_evidence" (= not counted) unless at
least one criterion is met -- the burden of proof is on the geometry, not
on us to prove it's garbage.

Usage:
    python evidence_score.py "../../new house/cad/newhouse 2569.dxf" C812F ct0150p B-3
"""

import argparse
import re
import sys
from pathlib import Path

import ezdxf

sys.path.insert(0, str(Path(__file__).parent))
from investigate_terms import nearest_text  # noqa: E402
from pynoi_parser import EXCLUDED_LAYER_EXACT  # noqa: E402

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

DESCRIPTIVE_TEXT_MAX_DISTANCE = 5.0  # DXF units -- close enough to be "next to" the instance
_NUMERIC_OR_TINY = re.compile(r"^[\d.\s,]+$")
_SIZE_OR_SPEC_MARKER = re.compile(r'["\u00d8\u00f8]|(?i:\bmm\b|\bsq\.?\b|\bcw\b|\bhw\b)')  # ", Ø, ø, mm, sq., CW/HW pipe callouts
_SHORT_CODE_LIKE = re.compile(r"^[A-Za-z]{1,3}\.?\d*\.?$")  # "MH.", "W2", "D5", "RS" -- abbreviation/code shape, not a description


def is_descriptive(text: str) -> bool:
    """Reject dimension numbers ('0.60'), pipe/size callouts ('CW Ø3/4"'), short
    abbreviation-shaped codes ('MH.', 'W2', 'D5'), and anything too short to carry
    meaning. First cut at this was too permissive -- confirmed false positive:
    'MH.' (a project nickname, per the project owner) and 'CW Ø3/4"' (a pipe size
    callout) both slipped through and wrongly flagged ct0150p (a known drafter
    mistake) as descriptive. This is a heuristic, not a guarantee -- still needs
    human review, see verdict()."""
    text = text.strip()
    if len(text) < 3:
        return False
    if _NUMERIC_OR_TINY.match(text):
        return False
    if _SIZE_OR_SPEC_MARKER.search(text):
        return False
    if _SHORT_CODE_LIKE.match(text):
        return False
    return True


def gather_evidence(doc, block_name: str) -> dict:
    msp = doc.modelspace()
    texts = []
    for e in msp:
        if e.dxftype() in ("TEXT", "MTEXT"):
            t = e.plain_text() if hasattr(e, "plain_text") else getattr(e, "text", "")
            if t.strip():
                texts.append((t.strip(), tuple(e.dxf.insert)))

    inserts = [e for e in msp if e.dxftype() == "INSERT" and e.dxf.name == block_name]
    layers_used = {e.dxf.layer for e in inserts}
    descriptive_hits = 0
    for e in inserts:
        hit = nearest_text(msp, tuple(e.dxf.insert), texts)
        if hit and hit[1] <= DESCRIPTIVE_TEXT_MAX_DISTANCE and is_descriptive(hit[0]):
            descriptive_hits += 1

    return {
        "instance_count": len(inserts),
        "layers_used": layers_used,
        "descriptive_text_hits": descriptive_hits,
        # a lone consistent layer is only meaningful evidence if that layer isn't
        # itself a true dumping ground (just "0" -- the default layer nobody
        # assigned on purpose). Deliberately NOT using the full Layer Exclusion
        # denylist here: DIM/WALL are "excluded" for name-based entity filtering,
        # but confirmed real product blocks (C805P, CT002P) legitimately live
        # there too (§12.1) -- that denylist answers a different question than
        # "is this layer meaningless," so reusing it here would wrongly zero out
        # real evidence.
        "consistent_layer": (
            len(layers_used) == 1
            and len(inserts) >= 3
            and next(iter(layers_used)).strip().upper() not in EXCLUDED_LAYER_EXACT
        ),
    }


def verdict(evidence: dict) -> str:
    """⚠️ Known limitation, confirmed by testing against ct0150p (a real drafter
    mistake, per the project owner): criterion 3 alone can't tell "real, repeated
    design element" apart from "one drafter's habitual, repeated mistake" -- both
    look identical from pure geometry/repetition (ct0150p sits on DIM 12 times,
    exactly like the confirmed-real C805P/CT002P/DR090SL1). Criterion 1 (matching
    a human-authored Legend/Schedule count) is the only thing that would close
    this gap, and it isn't built yet (needs Step 3 legend parsing). Until then:
    treat every "likely_signal" verdict as a hint for human review, never as an
    auto-applied final answer -- this triages obvious noise (see B-3) well, but
    does not replace judgment for genuinely ambiguous mid-cases."""
    if evidence["descriptive_text_hits"] >= 1:
        return "likely_signal (criterion 2: descriptive text nearby) -- still needs human confirmation"
    if evidence["consistent_layer"]:
        return "likely_signal (criterion 3: repeats consistently, same layer) -- still needs human confirmation"
    return "insufficient_evidence -- default: do not count"


def main() -> None:
    ap = argparse.ArgumentParser(description="evidence-based verdict for ambiguous block names")
    ap.add_argument("file", type=Path)
    ap.add_argument("terms", nargs="+")
    args = ap.parse_args()

    doc = ezdxf.readfile(str(args.file))
    for name in args.terms:
        ev = gather_evidence(doc, name)
        print(f"{name}: instances={ev['instance_count']} layers={sorted(ev['layers_used'])} "
              f"descriptive_hits={ev['descriptive_text_hits']} -> {verdict(ev)}")


if __name__ == "__main__":
    main()
