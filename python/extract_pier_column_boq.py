"""ไพน้อย — งานโครงสร้าง: ถอดปริมาณคอนกรีต+เหล็กตอม่อ-เสา (pier + column, C1/Cx)

Reads S-01 (แปลนฐานราก/ตอม่อ - grid of pier_code+footing_code, same page already
used by extract_footing_boq.py), S-05 (footing schedule - for the 90° hook length,
which = half of that footing's own longest dimension), and S-06 (แบบขยายการเสริม
เหล็กเสา - the column/pier schedule: cross-section + main bar + stirrup spec per
pier code) via Claude vision, then computes concrete volume and rebar (bar-cutting-
list from 10m stock) in plain Python - never asks the model to do the arithmetic.

Rules encoded here, confirmed by the project owner 2569-08-30 (03-ai-boq-procedure.md
หมวด 1, "กฎเหล็กเสริมตอม่อ"):
- single-story house (or top-floor pier/column before roof): the vertical main bar
  is ONE continuous piece from the footing hook to the column top - no lap splice,
  cut only once at the very top end
- 90 hook length at the footing end = half of that footing's own longest dimension
- pier height comes from a mandatory site survey (never guessed) - newhouse: 1.20m
- column height = ceiling level + 10cm (minimum), rounded UP to a practical site
  figure with a safety margin - newhouse: 3.20m (confirmed by owner 2569-08-30)
- a pier code whose above-floor portion is a STEEL BOX (not concrete, e.g. Cx here)
  has NO concrete column portion and its main bar does not run the column height -
  it is flagged and excluded from the column-height bar length / concrete volume,
  not guessed

Usage:
    python extract_pier_column_boq.py <pdf_path> --s01-page 14 --s05-page 18 --s06-page 19
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
from extract_footing_boq import S01_PROMPT, S05_PROMPT, parse_rebar_count_and_size

S06_PROMPT = """This is a column/pier reinforcement detail page (แบบขยายการเสริมเหล็กเสา)
from a Thai construction PDF. Find the column schedule - it lists pier/column codes
(e.g. "C1", "Cx") each usually with TWO rows/sections: (1) the portion below the floor
level, embedded in the footing (ตอม่อ), and (2) the portion above the floor level, up to
the roof (เสา). For each code, read the cross-section size (e.g. 0.20 x 0.20 m), the main
reinforcement bar spec (e.g. "6-DB 12 mm."), and the stirrup spec (e.g. "1-STIR RB 6 mm.
@0.15 m."), for BOTH the below-floor and above-floor portions. If the above-floor portion
is NOT concrete (e.g. it is a steel box/tube column instead), say so explicitly instead of
inventing a concrete spec for it.

Respond with ONLY JSON: {"columns": [{"code": "C1", "cross_section_m": [0.20, 0.20],
"below_floor": {"main_bar": "6-DB 12 mm.", "stirrup": "1-STIR RB 6 mm. @0.15 m.",
"is_concrete": true}, "above_floor": {"main_bar": "6-DB 12 mm.", "stirrup": "1-STIR RB 6
mm. @0.15 m.", "is_concrete": true, "note": ""}}, ...], "notes": "..."}"""


# --- confirmed constants (03-ai-boq-procedure.md หมวด 1, 2569-08-30) ---
STRUCTURAL_CONCRETE_WASTE = 0.03
DB12_KG_PER_M = 0.888
RB6_KG_PER_M = 0.222  # standard d^2/162 table value
REBAR_WEIGHT_WASTE = 0.05
STOCK_BAR_LENGTH_M = 10.0
STIRRUP_HOOK_ALLOWANCE_M = 0.10  # two 90 hooks ~5cm each on a closed stirrup, standard allowance


def hook_length_m(A, B):
    """90 hook into the footing = half of that footing's own longest dimension."""
    return max(A, B) / 2


def stirrup_perimeter_m(cross_section_m):
    """Closed rectangular stirrup: perimeter of the (cover-reduced) core + hook allowance.
    Uses the outer cross-section directly (cover already reflected in the drawn schedule
    size) - flagged as an approximation, not a substitute for the actual detail drawing."""
    w, h = cross_section_m
    return 2 * (w + h) + STIRRUP_HOOK_ALLOWANCE_M


def compute_pier_column_boq(positions, footing_schedule, column_schedule, pier_height_m, column_height_m, stirrup_spacing_m):
    """positions: [{"pier_code", "footing_code"}, ...] from S-01.
    footing_schedule: {code: {A,B,...}} from S-05.
    column_schedule: {code: {...}} from S-06."""
    rows = []
    total_concrete_below = 0.0
    total_concrete_above = 0.0
    main_bar_pieces_by_length = {}  # {round(length,3): piece count} - below-floor-only codes
    main_bar_pieces_full = {}  # {round(length,3): piece count} - hook+pier+column codes
    stirrup_pieces_by_length = {}
    flagged = []

    counts = {}
    for p in positions:
        key = (p["pier_code"], p["footing_code"])
        counts[key] = counts.get(key, 0) + 1

    for (pier_code, footing_code), count in sorted(counts.items()):
        if footing_code not in footing_schedule:
            flagged.append(f"footing code '{footing_code}' (used by pier {pier_code}) has no S-05 schedule row - skipped")
            continue
        if pier_code not in column_schedule:
            flagged.append(f"pier code '{pier_code}' has no S-06 schedule row - skipped")
            continue

        fsched = footing_schedule[footing_code]
        csched = column_schedule[pier_code]
        hook = hook_length_m(fsched["A"], fsched["B"])
        w, h = csched["cross_section_m"]
        cross_area = w * h

        below = csched["below_floor"]
        above = csched["above_floor"]

        # --- concrete: below-floor (pier) portion ---
        if below.get("is_concrete", True):
            vol_below = cross_area * pier_height_m * count
            total_concrete_below += vol_below
        else:
            vol_below = 0.0
            flagged.append(f"{pier_code}: below-floor portion flagged NOT concrete - check manually")

        # --- concrete: above-floor (column) portion ---
        above_is_concrete = above.get("is_concrete", True)
        if above_is_concrete:
            vol_above = cross_area * column_height_m * count
            total_concrete_above += vol_above
        else:
            vol_above = 0.0
            flagged.append(f"{pier_code}: above-floor portion is NOT concrete ({above.get('note', 'no note')}) "
                            f"- excluded from column concrete/main-bar-length, steel box BOQ'd separately")

        # --- main bar length ---
        main_count, main_size = parse_rebar_count_and_size(below["main_bar"])
        if main_size != "DB12":
            flagged.append(f"{pier_code}: main bar size {main_size} has no confirmed kg/m table value here")

        if above_is_concrete:
            full_len = round(hook + pier_height_m + column_height_m, 3)
            main_bar_pieces_full[full_len] = main_bar_pieces_full.get(full_len, 0) + main_count * count
            reported_len = full_len
        else:
            below_len = round(hook + pier_height_m, 3)
            main_bar_pieces_by_length[below_len] = main_bar_pieces_by_length.get(below_len, 0) + main_count * count
            reported_len = below_len

        # --- stirrups (below-floor pier portion only computed here; above-floor
        # stirrups need column_height and are added below when concrete) ---
        stirrup_len = round(stirrup_perimeter_m((w, h)), 3)
        n_stirrups_below = math.ceil(pier_height_m / stirrup_spacing_m) + 1
        stirrup_pieces_by_length[stirrup_len] = stirrup_pieces_by_length.get(stirrup_len, 0) + n_stirrups_below * count
        n_stirrups_above = 0
        if above_is_concrete:
            n_stirrups_above = math.ceil(column_height_m / stirrup_spacing_m) + 1
            stirrup_pieces_by_length[stirrup_len] = stirrup_pieces_by_length.get(stirrup_len, 0) + n_stirrups_above * count

        rows.append({
            "pier_code": pier_code, "footing_code": footing_code, "count": count,
            "hook_m": round(hook, 3), "main_bar_length_m": reported_len,
            "main_bar_count_per_pier": main_count,
            "concrete_below_m3": round(vol_below, 3), "concrete_above_m3": round(vol_above, 3),
            "stirrups_below": n_stirrups_below, "stirrups_above": n_stirrups_above,
        })

    def cutting_list_from(pieces_by_length):
        cl = []
        total_bars = 0
        total_purchased_m = 0.0
        total_used_m = 0.0
        for length, n_pieces in sorted(pieces_by_length.items()):
            pieces_per_bar = math.floor(STOCK_BAR_LENGTH_M / length)
            bars_needed = math.ceil(n_pieces / pieces_per_bar)
            purchased_m = bars_needed * STOCK_BAR_LENGTH_M
            used_m = n_pieces * length
            cl.append({
                "piece_length_m": length, "pieces_needed": n_pieces,
                "pieces_per_stock_bar": pieces_per_bar, "bars_needed": bars_needed,
                "used_m": round(used_m, 2), "purchased_m": purchased_m,
            })
            total_bars += bars_needed
            total_purchased_m += purchased_m
            total_used_m += used_m
        return cl, total_bars, total_purchased_m, total_used_m

    main_cl_full, bars_full, purch_full, used_full = cutting_list_from(main_bar_pieces_full)
    main_cl_below, bars_below, purch_below, used_below = cutting_list_from(main_bar_pieces_by_length)
    stirrup_cl, stirrup_bars, stirrup_purch, stirrup_used = cutting_list_from(stirrup_pieces_by_length)

    return {
        "rows": rows,
        "flagged": flagged,
        "total_concrete_below_m3": round(total_concrete_below, 3),
        "total_concrete_above_m3": round(total_concrete_above, 3),
        "total_concrete_m3": round(total_concrete_below + total_concrete_above, 3),
        "total_concrete_with_waste_m3": round((total_concrete_below + total_concrete_above) * (1 + STRUCTURAL_CONCRETE_WASTE), 3),
        "main_bar_full_height_cutting_list": {"rows": main_cl_full, "total_bars": bars_full,
                                                "total_purchased_m": purch_full, "total_used_m": round(used_full, 2)},
        "main_bar_below_floor_only_cutting_list": {"rows": main_cl_below, "total_bars": bars_below,
                                                     "total_purchased_m": purch_below, "total_used_m": round(used_below, 2)},
        "stirrup_cutting_list": {"rows": stirrup_cl, "total_bars": stirrup_bars,
                                   "total_purchased_m": stirrup_purch, "total_used_m": round(stirrup_used, 2)},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf_path")
    ap.add_argument("--s01-page", type=int, required=True)
    ap.add_argument("--s05-page", type=int, required=True)
    ap.add_argument("--s06-page", type=int, required=True)
    ap.add_argument("--pier-height", type=float, required=True, help="from mandatory site survey (m)")
    ap.add_argument("--column-height", type=float, required=True, help="confirmed practical design height (m)")
    ap.add_argument("--stirrup-spacing", type=float, default=0.15, help="m, from S-06 schedule")
    args = ap.parse_args()

    client = anthropic.Anthropic()
    doc = fitz.open(args.pdf_path)

    print("Reading S-01 (foundation/pier plan) - pier_code+footing_code per grid point...")
    s01_data, u1 = call_single(client, render_page(doc, args.s01_page - 1), S01_PROMPT, max_tokens=10000)
    print("Reading S-05 (footing schedule table)...")
    s05_data, u2 = call_single(client, render_page(doc, args.s05_page - 1), S05_PROMPT)
    print("Reading S-06 (column/pier reinforcement schedule)...")
    s06_data, u3 = call_single(client, render_page(doc, args.s06_page - 1), S06_PROMPT, max_tokens=6000)

    cost = ((u1.input_tokens + u2.input_tokens + u3.input_tokens) * 2.00
            + (u1.output_tokens + u2.output_tokens + u3.output_tokens) * 10.00) / 1_000_000

    positions = s01_data.get("footings", [])
    footing_schedule = {row["code"]: row for row in s05_data.get("footing_schedule", [])}
    column_schedule = {row["code"]: row for row in s06_data.get("columns", [])}

    print(f"\nไพน้อย นับตำแหน่งตอม่อจาก S-01: {len(positions)} จุด")
    print(f"ไพน้อย อ่านตาราง S-06 ได้รหัสเสา: {list(column_schedule.keys())}")

    result = compute_pier_column_boq(positions, footing_schedule, column_schedule,
                                       args.pier_height, args.column_height, args.stirrup_spacing)

    print("\n=== ผลคำนวณ (โค้ด Python ล้วน ไม่ใช่ AI คิดเลข) ===")
    for row in result["rows"]:
        print(f"  {row}")
    if result["flagged"]:
        print("\n⚠️ จุดที่ flag ไว้ (ไม่ได้เดา):")
        for f in result["flagged"]:
            print(f"  - {f}")
    print(f"\nคอนกรีตตอม่อ(below floor): {result['total_concrete_below_m3']} m3")
    print(f"คอนกรีตเสา(above floor): {result['total_concrete_above_m3']} m3")
    print(f"รวม +waste3%: {result['total_concrete_with_waste_m3']} m3")
    print(f"\nเหล็กยืน (เต็มความสูง พับ+ตอม่อ+เสา): {result['main_bar_full_height_cutting_list']}")
    print(f"เหล็กยืน (เฉพาะตอม่อ - รหัสที่บนพื้นเป็นเหล็กกล่อง): {result['main_bar_below_floor_only_cutting_list']}")
    print(f"เหล็กปลอก: {result['stirrup_cutting_list']}")
    print(f"\ncost: ${cost:.5f} (~{cost*36.5:.2f} THB)")


if __name__ == "__main__":
    main()
