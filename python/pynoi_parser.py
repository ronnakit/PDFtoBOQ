"""
pynoi_parser -- prototype DXF inspector for "ไพน้อย" (Py-Noi)

Phase 1 prototype (see ../../../06-roadmap.md). Reads a DXF file and reports
layers, block definitions, and basic geometric takeoff primitives (line
lengths, closed-polyline lengths/areas) per layer -- the SOP steps 3-5 in
../../../03-ai-boq-procedure.md (legend/spec parsing, scale calibration,
sheet classification). It does not compute a priced BOQ yet -- that is the
next stage, once this output is calibrated against the ground-truth BOQ in
../../new house/boq/BOQ - new house.xls.

Caveat: length/area for LWPOLYLINE entities treats bulges (arc segments) as
straight lines. Fine for the rectilinear walls in the reference house; will
under/over-count anything with curved geometry (e.g. round stair treads).

Usage:
    python pynoi_parser.py "../../new house/cad/newhouse 2569.dxf"
    python pynoi_parser.py "../../welcome maerem/cad/Kadfarang Drawing.dxf" --scan-block "X ref Kad Plan 1st" --scan-pattern "FL\\s*([0-9]+)"
"""

import argparse
import re
import sys
from pathlib import Path

import ezdxf
import ezdxf.units
from ezdxf.math import area as polygon_area

from schema_loader import load_schema

# Windows console defaults to cp1252, which can't print Thai text in this file's
# own print() calls -- force utf-8 so it works regardless of how it's invoked.
if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# Layer Exclusion -- loaded from 04-category-schema.md's "exclusion_rules" key
# (see ../../../07-drawing-signal-vs-noise.md §5.2, §11, §15) instead of being
# hardcoded here, so a new noise pattern only ever means editing that markdown
# file, never this code (see ../../../09-vocabulary-review-workflow.md).
#
# ⚠️ TWO TIERS, not to be confused (§15): "not relevant to BOQ quantities" does
# NOT mean "not relevant to the drawing." Dimensions, grid lines, title blocks,
# specs, hatch patterns are legitimate, human-intended drawing content -- just
# not something to count as material. is_excluded_layer() (this function) is
# used for QUANTITY SKIPPING ONLY -- it combines both tiers, since for takeoff
# purposes we want to skip both. is_safe_to_delete() below checks ONLY the
# narrow safe_to_delete tier (confirmed zero-value software artifacts) and is
# the only check clean_dxf.py's Pass 1 may use to physically remove entities.
#
# This is a first-pass filter only -- it will have false positives/negatives
# (e.g. "DIMEN" gets excluded even if it turns out to hold real geometry) and
# must be combined with the other heuristics in §7 before anything is trusted
# for pricing. Extend with --extra-exclude per file for one-off cases rather
# than editing the schema.
_EXCLUSION_RULES = load_schema()["exclusion_rules"]
_QUANTITY_EXCLUSION = _EXCLUSION_RULES["quantity_exclusion"]
_SAFE_TO_DELETE = _EXCLUSION_RULES["safe_to_delete"]

EXCLUDED_LAYER_KEYWORDS = _QUANTITY_EXCLUSION["keywords"]
EXCLUDED_LAYER_EXACT = set(_QUANTITY_EXCLUSION["exact"])
EXCLUDED_LAYER_PATTERNS = [re.compile(p, re.I) for p in _QUANTITY_EXCLUSION["patterns"]]

SAFE_TO_DELETE_KEYWORDS = _SAFE_TO_DELETE["keywords"]
SAFE_TO_DELETE_PATTERNS = [re.compile(p, re.I) for p in _SAFE_TO_DELETE["patterns"]]


def _token_aware_match(needle: str, name: str) -> bool:
    """substring match for needle len >= 4; token-prefix match for shorter needles.

    Short keywords like "AC"/"DB"/"LP" match almost anything as a bare substring --
    confirmed false positives in practice: "A$C69AC065E" wrongly tagged as Air
    Conditioning (contains "AC"), "_ClosedBlank" wrongly tagged as Electrical
    (contains "dB" mid-word). Tokens are split on any non-alphanumeric/non-Thai
    character, matching how layer names are actually delimited (-, _, space, $).
    Prefix (not exact-equality) match on tokens so "DIM" still catches "DIMENSION"/
    "DIMS" -- those are the same word family, unlike the coincidental-substring cases
    above, and requiring exact equality broke that real match during testing.
    """
    needle_u = needle.upper()
    if len(needle_u) >= 4:
        return needle_u in name.upper()
    tokens = re.split(r"[^0-9A-Za-zก-๙]+", name.upper())
    return any(token.startswith(needle_u) for token in tokens if token)


def is_excluded_layer(layer_name: str, extra_keywords: list[str] | None = None) -> bool:
    """Skip this name when SUMMING BOQ QUANTITIES. Does not imply it's safe to
    delete from a file -- see is_safe_to_delete() for that, a much narrower check."""
    name = layer_name.strip().upper()
    if name in EXCLUDED_LAYER_EXACT:
        return True
    if any(pattern.match(layer_name.strip()) for pattern in EXCLUDED_LAYER_PATTERNS):
        return True
    if is_safe_to_delete(layer_name):
        return True
    keywords = EXCLUDED_LAYER_KEYWORDS + (extra_keywords or [])
    return any(_token_aware_match(kw, name) for kw in keywords)


def is_safe_to_delete(layer_name: str) -> bool:
    """True only for confirmed zero-value software-internal artifacts (AutoCAD's
    own auto-generated names -- never human-authored drawing content). This is
    deliberately much narrower than is_excluded_layer(): DIM/GRID/TITLE/SPEC/HATCH/
    decorative blocks are excluded from quantity counting but are NOT safe to
    delete -- they're real, human-intended parts of the drawing. clean_dxf.py's
    Pass 1 must use this function, never is_excluded_layer(), to decide what to
    physically remove."""
    name = layer_name.strip().upper()
    if any(pattern.match(layer_name.strip()) for pattern in SAFE_TO_DELETE_PATTERNS):
        return True
    return any(_token_aware_match(kw, name) for kw in SAFE_TO_DELETE_KEYWORDS)


def load(file_path: Path):
    if not file_path.exists():
        raise FileNotFoundError(file_path)
    return ezdxf.readfile(str(file_path))


def report_header(doc) -> None:
    insunits = doc.header.get("$INSUNITS", 0)
    unit_name = ezdxf.units.decode(insunits) if insunits else "unitless"
    print(f"DXF version: {doc.dxfversion}")
    print(f"$INSUNITS: {insunits} ({unit_name})")
    print(
        "  -> มาตรฐานไทย: 1 หน่วยใน CAD = 1 เมตรจริง "
        "(ต้องสอบทานกับเส้นกริด/ตัวเลขบอกขนาดจริงในแบบเสมอ อย่าเชื่อ $INSUNITS อย่างเดียว)"
    )


def report_layers(doc, extra_exclude: list[str] | None = None) -> dict:
    msp = doc.modelspace()
    counts: dict[str, dict[str, int]] = {}
    for e in msp:
        by_type = counts.setdefault(e.dxf.layer, {})
        by_type[e.dxftype()] = by_type.get(e.dxftype(), 0) + 1
    excluded_n = sum(1 for layer in counts if is_excluded_layer(layer, extra_exclude))
    print(f"\nLayers in modelspace ({len(counts)}, {excluded_n} excluded by Layer Exclusion):")
    for layer, types in sorted(counts.items()):
        summary = ", ".join(f"{t}={n}" for t, n in sorted(types.items()))
        flag = " [EXCLUDED]" if is_excluded_layer(layer, extra_exclude) else ""
        print(f"  {layer}: {summary}{flag}")
    return counts


def report_blocks(doc) -> list:
    names = [b.name for b in doc.blocks if not b.name.startswith("*")]
    print(f"\nBlock definitions ({len(names)}):")
    for name in sorted(names):
        print(f"  {name}")
    return names


def scan_text_in_block(doc, block_name: str, pattern: str) -> dict:
    """สแกน TEXT/MTEXT ใน block ตาม regex -- ต้นแบบ generalize จาก cad_analyzer-1.py เดิม"""
    if block_name not in doc.blocks:
        print(f"[Error] ไม่พบ Block เป้าหมาย: {block_name}")
        return {}
    block = doc.blocks[block_name]
    regex = re.compile(pattern, re.IGNORECASE)
    counts: dict[str, int] = {}
    scanned = 0
    for entity in block:
        if entity.dxftype() in ("TEXT", "MTEXT"):
            text = entity.plain_text() if hasattr(entity, "plain_text") else getattr(entity, "text", "")
            scanned += 1
            match = regex.search(text)
            if match:
                code = match.group(0).upper().replace(" ", "")
                counts[code] = counts.get(code, 0) + 1
    print(f"\nสแกน TEXT/MTEXT ใน block '{block_name}': {scanned} จุด")
    if counts:
        for code, n in sorted(counts.items()):
            print(f"  {code}: พบ {n} จุด")
    else:
        print("  ⚠️ ไม่พบข้อความที่ตรง pattern -- อาจถูกห่อหุ้มไว้ใน block ย่อย/attribute ของสัญลักษณ์")
    return counts


def report_takeoff_primitives(doc, extra_exclude: list[str] | None = None) -> None:
    """ความยาวเส้น/พื้นที่รูปปิดต่อเลเยอร์ -- ต้นแบบสำหรับ net-deduction engine ในอนาคต

    เลเยอร์ที่ผ่าน Layer Exclusion (is_excluded_layer) จะถูกแยกออกไปพิมพ์ต่างหาก
    ไม่ปนกับตัวเลขที่จะใช้คำนวณ BOQ จริง -- ยังคงพิมพ์ให้เห็นเพื่อ audit ว่า filter
    ตัดอะไรทิ้งไปบ้าง (ตรวจ false positive/negative ได้) ไม่ใช่ซ่อนเงียบ
    """
    msp = doc.modelspace()
    layer_length: dict[str, float] = {}
    layer_area: dict[str, float] = {}

    for e in msp:
        layer = e.dxf.layer
        if e.dxftype() == "LINE":
            length = e.dxf.start.distance(e.dxf.end)
            layer_length[layer] = layer_length.get(layer, 0.0) + length
        elif e.dxftype() == "LWPOLYLINE":
            points = list(e.get_points("xy"))
            if len(points) < 2:
                continue
            length = sum(
                Vec2Distance(points[i], points[i + 1]) for i in range(len(points) - 1)
            )
            if e.closed and len(points) >= 3:
                length += Vec2Distance(points[-1], points[0])
                layer_area[layer] = layer_area.get(layer, 0.0) + abs(polygon_area(points))
            layer_length[layer] = layer_length.get(layer, 0.0) + length

    all_layers = sorted(set(layer_length) | set(layer_area))
    included = [l for l in all_layers if not is_excluded_layer(l, extra_exclude)]
    excluded = [l for l in all_layers if is_excluded_layer(l, extra_exclude)]

    def _print(layers: list[str]) -> None:
        for layer in layers:
            length = layer_length.get(layer, 0.0)
            area = layer_area.get(layer)
            area_str = f", area(closed)={area:.2f}" if area is not None else ""
            print(f"  {layer}: length={length:.2f}{area_str}")

    print(f"\nTakeoff primitives -- INCLUDED ({len(included)} เลเยอร์, ผ่าน Layer Exclusion):")
    _print(included)
    print(
        f"\nTakeoff primitives -- EXCLUDED ({len(excluded)} เลเยอร์, ตัดทิ้งโดย Layer Exclusion "
        "-- ดู 07-drawing-signal-vs-noise.md §5.2, ตรวจ false positive ได้จากรายการนี้):"
    )
    _print(excluded)


def Vec2Distance(p1, p2) -> float:
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5


def main() -> None:
    ap = argparse.ArgumentParser(description="ไพน้อย prototype DXF inspector")
    ap.add_argument("file", type=Path, help="path to a .dxf file")
    ap.add_argument("--scan-block", help="block name to scan for text codes")
    ap.add_argument(
        "--scan-pattern", default=r"FL\s*([0-9]+)", help="regex to match inside the block text"
    )
    ap.add_argument(
        "--extra-exclude",
        default="",
        help="comma-separated extra layer-name keywords to exclude for this file "
        "(on top of the built-in EXCLUDED_LAYER_KEYWORDS), e.g. --extra-exclude=XREF,SETBACK",
    )
    args = ap.parse_args()
    extra_exclude = [kw.strip() for kw in args.extra_exclude.split(",") if kw.strip()]

    doc = load(args.file)
    report_header(doc)
    report_layers(doc, extra_exclude)
    report_blocks(doc)
    report_takeoff_primitives(doc, extra_exclude)
    if args.scan_block:
        scan_text_in_block(doc, args.scan_block, args.scan_pattern)


if __name__ == "__main__":
    main()
