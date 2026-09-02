"""ไพน้อย — รวม Bar Cutting List ข้ามหมวดทั้งโครงการ (ฐานราก+ตอม่อ-เสา+คาน)

Every earlier script (extract_footing_boq.py, extract_pier_column_boq.py,
extract_beam_boq.py) optimises its own cutting list independently, per
category. That leaves real waste on the table: a leftover piece of stock bar
too short for that category's own longest length might be exactly enough for
a shorter piece needed by ANOTHER category. This script pools every DB12,
DB16, and RB6 piece needed project-wide (using the already-confirmed
piece lists baked into claude_boq.md / the per-category scripts - no new
API calls) and runs a First-Fit-Decreasing bin-packing pass per size to see
how many fewer 10m stock bars are actually needed.

Confirmed piece data as of 2569-08-31 (see project/new house/claude_boq.md):
- ฐานราก (extract_footing_boq.py): DB12 only
- ตอม่อ-เสา (extract_pier_column_boq.py): DB12 (main bars), RB6 (stirrups)
- คาน (extract_beam_boq.py, final 38-segment list): DB12 + DB16 (main bars),
  RB6 (stirrups)

Usage:
    python combine_cutting_list.py
"""
import math

STOCK_BAR_LENGTH_M = 10.0

# (piece_length_m, pieces_needed) per size, pooled from every category's
# already-confirmed cutting list (see claude_boq.md หมวด 1 §1-3)
PIECES_BY_SIZE = {
    "DB12": [
        # footing
        (0.65, 32), (0.90, 176), (1.20, 128),
        # pier+column main bars
        (4.90, 66), (5.05, 48), (1.575, 16),
        # beam main bars
        (0.175, 4), (0.7, 10), (0.875, 4), (1.125, 5), (1.25, 2),
        (1.9, 8), (2.0, 12), (3.5, 10), (4.5, 50), (5.0, 14),
    ],
    "DB16": [
        # beam main bars only (no other category uses DB16)
        (0.25, 2), (0.4, 2), (0.475, 2), (0.5, 2), (0.625, 2),
        (1.0, 6), (1.125, 8), (1.25, 2), (1.6, 6), (1.9, 6),
        (2.0, 6), (2.5, 6), (4.5, 72), (5.0, 30),
    ],
    "RB6": [
        # pier+column stirrups
        (0.90, 644),
        # beam stirrups
        (1.30, 1164),
    ],
}

# what each size's pieces would need if cut PER-CATEGORY separately (the old
# way) - taken directly from each script's own already-confirmed output, for
# the "before" comparison. Grouped by (size, category) -> bars_needed.
SEPARATE_BARS_BY_CATEGORY = {
    ("DB12", "ฐานราก"): 3 + 16 + 16,       # 0.65->3, 0.90->16, 1.20->16 (from claude_boq.md §1)
    ("DB12", "ตอม่อ-เสา"): 33 + 48 + 3,     # 4.90->33, 5.05->48, 1.575->3
    ("DB12", "คาน"): 1+1+1+1+1+2+3+5+25+7,  # from the beam cutting-list rows above
    ("DB16", "คาน"): 1+1+1+1+1+1+1+1+1+2+2+2+36+15,
    ("RB6", "ตอม่อ-เสา"): 59,
    ("RB6", "คาน"): 167,
}


def first_fit_decreasing(pieces):
    """pieces: [(length_m, count), ...]. Returns (bars_needed, used_m, purchased_m)."""
    expanded = []
    for length, count in pieces:
        expanded.extend([length] * count)
    expanded.sort(reverse=True)

    bins = []  # remaining capacity per open stock bar
    for length in expanded:
        placed = False
        for i, remaining in enumerate(bins):
            if remaining >= length:
                bins[i] -= length
                placed = True
                break
        if not placed:
            bins.append(STOCK_BAR_LENGTH_M - length)

    bars_needed = len(bins)
    used_m = sum(expanded)
    purchased_m = bars_needed * STOCK_BAR_LENGTH_M
    return bars_needed, used_m, purchased_m


def main():
    grand_old_bars = 0
    grand_new_bars = 0
    for size, pieces in PIECES_BY_SIZE.items():
        old_bars = sum(v for (s, _), v in SEPARATE_BARS_BY_CATEGORY.items() if s == size)
        new_bars, used_m, purchased_m = first_fit_decreasing(pieces)
        waste_pct = (purchased_m - used_m) / purchased_m * 100
        saved = old_bars - new_bars
        print(f"=== {size} ===")
        print(f"  ตัดแยกทีละหมวด (เดิม): {old_bars} เส้น")
        print(f"  ตัดรวมข้ามหมวด (ใหม่, First-Fit-Decreasing): {new_bars} เส้น "
              f"(ใช้จริง {used_m:.1f}ม. ของเสีย {waste_pct:.1f}%)")
        print(f"  ประหยัดได้: {saved} เส้น ({saved*STOCK_BAR_LENGTH_M:.0f}ม.)")
        print()
        grand_old_bars += old_bars
        grand_new_bars += new_bars

    print(f"=== รวมทั้งโครงการ ===")
    print(f"เดิม (ตัดแยกทีละหมวด): {grand_old_bars} เส้น")
    print(f"ใหม่ (ตัดรวมข้ามหมวด): {grand_new_bars} เส้น")
    print(f"ประหยัดได้: {grand_old_bars - grand_new_bars} เส้น "
          f"({(grand_old_bars - grand_new_bars) * STOCK_BAR_LENGTH_M:.0f} ม.)")


if __name__ == "__main__":
    main()
