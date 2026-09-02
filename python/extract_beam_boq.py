"""ไพน้อย — งานโครงสร้าง: ถอดปริมาณคอนกรีต+เหล็กคาน (Beam, B1-B6)

Reads S-02 (แบบแปลนคานคอดิน+พื้น - beam+floor plan, grid of beam segments each
with a code B1-B6 and a length implied by the dimension chain) via Claude vision,
then computes concrete volume and rebar (bar-cutting-list from 10m stock,
including the "ADD." extra bars whose length = L/4 of THAT segment's own length)
in plain Python - never asks the model to do the arithmetic itself.

Rules encoded here, confirmed by the project owner 2569-08-30 (03-ai-boq-procedure.md
หมวด 1, "กฎงานคาน"):
- all of B1-B6 share the same 0.20 x 0.40 m cross-section (read directly off S-08)
- "ADD." bars extend L/4 from the support, where L = that beam SEGMENT's own
  length (not a project-wide constant) - e.g. a 4m beam gets a 1m ADD. bar
- rebar spec per code (main bars top/bottom, stirrup) is read once from S-08
  (schedule table, reliable) - NOT re-derived per segment

⚠️ Unlike S-01 (a repeating point grid), S-02 is an irregular beam+floor plan -
segment lengths vary per bay and are not a simple repeating pattern. The model's
per-segment length read here should be spot-checked against a manual crop of at
least one bay before trusting the totals (see 12-extraction-quality-log.md).

Usage:
    python extract_beam_boq.py <pdf_path> --s02-page 15
"""
import argparse
import math
import os
import re
import sys

import anthropic
import fitz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_foundation_data import call_single, render_page

S02_PROMPT = """This is a Thai residential ground-tie-beam + floor plan (แบบแปลนคานคอดิน, พื้น),
drawn on a structural grid (columns 1-6 left-right, rows A-E top-bottom, all dimensions in
meters). Every physical beam MEMBER is a straight line segment between two points on the grid
(usually between two adjacent grid intersections, but sometimes a shorter segment within one
bay when a dimension chain subdivides it - e.g. a 4.50m bay might be split into 1.20m + 3.30m
by two different beams). Each beam segment is labeled with a code (B1, B2, B3, B4, B5, or B6)
printed next to it.

For EVERY beam segment, read: (1) its code, (2) its length in meters (read the printed
dimension number(s) along that exact segment from the dimension chains around the plan's
perimeter - do not guess or compute from unrelated dimensions), (3) which two grid points it
connects (e.g. "A1-A2" for a segment along row A between columns 1 and 2, or "1A-1B" for a
vertical segment along column 1 between rows A and B).

Also separately note every "S1" symbol (a square with a diagonal cross/X hatch pattern,
usually with a circled "S1" label) and every "CS" circled label you see - report their
approximate grid-bay location (e.g. "bay between A1-A2/A-B") - these mark cast-in-place slab
zones, not beams, but the count/location matters for a later floor takeoff. Do NOT count these
as beams.

If a segment's length is genuinely illegible or you are not confident, say so in "notes"
instead of guessing a number.

Respond with ONLY JSON: {"beam_segments": [{"code": "B5", "length_m": 4.50,
"grid": "A1-A2"}, ...], "s1_zones": ["bay A1-A2/top-offset", ...], "cs_zones": ["..."],
"notes": "..."}"""


# --- confirmed constants (03-ai-boq-procedure.md หมวด 1, 2569-08-30, read off S-08) ---
CROSS_SECTION_M = (0.20, 0.40)  # width x depth, same for all of B1-B6
STRUCTURAL_CONCRETE_WASTE = 0.03
DB12_KG_PER_M = 0.888
DB16_KG_PER_M = 1.578  # standard d^2/162 table value
RB6_KG_PER_M = 0.222
STOCK_BAR_LENGTH_M = 10.0
STIRRUP_HOOK_ALLOWANCE_M = 0.10

# read directly off S-08 (schedule table, reliable - not re-derived per segment)
# main_top / main_bottom: (count, size) at SECTION A-A (support) and SECTION B-B (midspan)
# add_bar: (count, size) or None - the "ADD." extra bars, length = L/4 of the segment
# stirrup: (legs, size, spacing_m)
BEAM_SCHEDULE = {
    "B1": {"main_top": (2, "DB12"), "main_bottom": (2, "DB12"), "add_bar": None,
           "stirrup": (1, "RB6", 0.15)},
    "B2": {"main_top": (2, "DB12"), "main_bottom": (4, "DB12"), "add_bar": None,
           "stirrup": (1, "RB6", 0.15)},
    "B3": {"main_top": (2, "DB12"), "main_bottom": (2, "DB12"), "add_bar": (1, "DB12"),
           "stirrup": (1, "RB6", 0.15)},
    "B4": {"main_top": (2, "DB12"), "main_bottom": (3, "DB12"), "add_bar": (2, "DB12"),
           "stirrup": (1, "RB6", 0.15)},
    "B5": {"main_top": (3, "DB16"), "main_bottom": (3, "DB16"), "add_bar": (2, "DB16"),
           "stirrup": (1, "RB6", 0.15)},
    "B6": {"main_top": (6, "DB16"), "main_bottom": (6, "DB16"), "add_bar": None,
           "stirrup": (2, "RB6", 0.15)},
}
KG_PER_M = {"DB12": DB12_KG_PER_M, "DB16": DB16_KG_PER_M, "RB6": RB6_KG_PER_M}


def stirrup_perimeter_m(cross_section_m):
    w, h = cross_section_m
    return 2 * (w + h) + STIRRUP_HOOK_ALLOWANCE_M


def compute_beam_boq(beam_segments):
    """beam_segments: [{"code", "length_m", "grid"}, ...] - one row per PHYSICAL segment
    (not grouped by code yet - each segment has its own L for the ADD. bar rule)."""
    rows = []
    total_concrete = 0.0
    main_pieces_by_key = {}  # {(size, round(length,3)): piece count}
    stirrup_pieces_by_key = {}

    w, h = CROSS_SECTION_M
    cross_area = w * h
    stirrup_len = round(stirrup_perimeter_m(CROSS_SECTION_M), 3)

    for seg in beam_segments:
        code = seg["code"]
        L = seg["length_m"]
        if code not in BEAM_SCHEDULE:
            rows.append({"code": code, "length_m": L, "grid": seg.get("grid"), "flag": f"unknown beam code '{code}' - skipped"})
            continue
        sched = BEAM_SCHEDULE[code]

        vol = cross_area * L
        total_concrete += vol

        top_n, top_size = sched["main_top"]
        bot_n, bot_size = sched["main_bottom"]
        main_pieces_by_key[(top_size, round(L, 3))] = main_pieces_by_key.get((top_size, round(L, 3)), 0) + top_n
        main_pieces_by_key[(bot_size, round(L, 3))] = main_pieces_by_key.get((bot_size, round(L, 3)), 0) + bot_n

        add_len = None
        if sched["add_bar"]:
            add_n, add_size = sched["add_bar"]
            add_len = round(L / 4, 3)
            main_pieces_by_key[(add_size, add_len)] = main_pieces_by_key.get((add_size, add_len), 0) + add_n

        legs, stir_size, spacing = sched["stirrup"]
        n_stirrups = math.ceil(L / spacing) + 1
        stirrup_pieces_by_key[(stir_size, stirrup_len)] = stirrup_pieces_by_key.get((stir_size, stirrup_len), 0) + n_stirrups * legs

        rows.append({
            "code": code, "length_m": L, "grid": seg.get("grid"),
            "concrete_m3": round(vol, 4),
            "main_top": f"{top_n}-{top_size}", "main_bottom": f"{bot_n}-{bot_size}",
            "add_bar": f"{sched['add_bar'][0]}-{sched['add_bar'][1]} @ {add_len}m" if sched["add_bar"] else None,
            "stirrups": n_stirrups * legs,
        })

    def cutting_list_from(pieces_by_key):
        cl = []
        total_bars = 0
        total_purchased_m = 0.0
        total_used_m = 0.0
        for (size, length), n_pieces in sorted(pieces_by_key.items()):
            pieces_per_bar = math.floor(STOCK_BAR_LENGTH_M / length)
            if pieces_per_bar < 1:
                cl.append({"size": size, "piece_length_m": length, "pieces_needed": n_pieces,
                           "flag": f"length {length}m exceeds one 10m stock bar - needs a splice, not computed"})
                continue
            bars_needed = math.ceil(n_pieces / pieces_per_bar)
            purchased_m = bars_needed * STOCK_BAR_LENGTH_M
            used_m = n_pieces * length
            cl.append({"size": size, "piece_length_m": length, "pieces_needed": n_pieces,
                       "pieces_per_stock_bar": pieces_per_bar, "bars_needed": bars_needed,
                       "used_m": round(used_m, 2), "purchased_m": purchased_m})
            total_bars += bars_needed
            total_purchased_m += purchased_m
            total_used_m += used_m
        return cl, total_bars, total_purchased_m, total_used_m

    main_cl, main_bars, main_purch, main_used = cutting_list_from(main_pieces_by_key)
    stir_cl, stir_bars, stir_purch, stir_used = cutting_list_from(stirrup_pieces_by_key)

    return {
        "rows": rows,
        "total_concrete_m3": round(total_concrete, 3),
        "total_concrete_with_waste_m3": round(total_concrete * (1 + STRUCTURAL_CONCRETE_WASTE), 3),
        "main_bar_cutting_list": {"rows": main_cl, "total_bars": main_bars,
                                    "total_purchased_m": main_purch, "total_used_m": round(main_used, 2)},
        "stirrup_cutting_list": {"rows": stir_cl, "total_bars": stir_bars,
                                   "total_purchased_m": stir_purch, "total_used_m": round(stir_used, 2)},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf_path")
    ap.add_argument("--s02-page", type=int, required=True)
    args = ap.parse_args()

    client = anthropic.Anthropic()
    doc = fitz.open(args.pdf_path)

    print("Reading S-02 (beam+floor plan) - beam segments, S1/CS zones...")
    s02_data, u1 = call_single(client, render_page(doc, args.s02_page - 1), S02_PROMPT, max_tokens=24000)

    cost = (u1.input_tokens * 2.00 + u1.output_tokens * 10.00) / 1_000_000

    all_segments = s02_data.get("beam_segments", [])
    segments = [s for s in all_segments if s.get("length_m") is not None]
    unconfirmed = [s for s in all_segments if s.get("length_m") is None]
    print(f"\nไพน้อย อ่านได้ {len(all_segments)} segments ({len(segments)} มีความยาวยืนยัน, {len(unconfirmed)} ยังไม่ยืนยัน)")
    for s in segments:
        print(f"  {s}")
    if unconfirmed:
        print("\n⚠️ segments ที่ยังไม่มีความยาว (ไม่รวมคำนวณ รอตรวจสอบเพิ่ม):")
        for s in unconfirmed:
            print(f"  {s}")
    print(f"\ns1_zones: {s02_data.get('s1_zones')}")
    print(f"cs_zones: {s02_data.get('cs_zones')}")
    print(f"notes: {s02_data.get('notes')}")

    result = compute_beam_boq(segments)

    print("\n=== ผลคำนวณ (โค้ด Python ล้วน ไม่ใช่ AI คิดเลข) ===")
    for row in result["rows"]:
        print(f"  {row}")
    print(f"\nคอนกรีตคาน รวม: {result['total_concrete_m3']} m3 (+waste3% = {result['total_concrete_with_waste_m3']} m3)")
    print(f"\nเหล็กยืน (cutting list): {result['main_bar_cutting_list']}")
    print(f"เหล็กปลอก (cutting list): {result['stirrup_cutting_list']}")
    print(f"\ncost: ${cost:.5f} (~{cost*36.5:.2f} THB)")


if __name__ == "__main__":
    main()
