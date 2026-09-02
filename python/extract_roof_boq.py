"""
Roof structure (โครงสร้างหลังคา) BOQ calculator.

Calculation logic here is specific to ONE roof topology, confirmed with the
project owner over several rounds against their own SketchUp model (not
re-derived from AI vision reads of the dense S-03/S-04 roof plan, which
proved unreliable for this drawing set): two full-length simple gables (a
main spine + a front extension wing) that overlap near the front, forming
exactly ONE valley -- both gables are plain (gable-end) everywhere else, not
a full hip roof. A project with a different roof shape (full hip, single
gable, etc.) needs new calculation functions, not just different numbers.

All the NUMBERS (levels, grid coordinates, overhangs, spacing, stock length)
are project-specific and live in <project>/MD/roof_geometry.md, not in this
file -- see project_md_data.py for the loader. Only the geometry FORMULAS
and the general cutting-list mechanics (FFD bin-packing, splicing a
continuous run from stock) are generic code here.

Explicitly OUT OF SCOPE (per user instruction): แผ่นมุงหลังคา (roofing sheet/tile)
and เชิงชายชัวร์ (fascia trim) -- both are architectural/finish items.

Usage:
    python extract_roof_boq.py "../../new house"
"""

import argparse
import math
from pathlib import Path

from project_md_data import load_keyvalue_section


def load_geometry(project_dir):
    md_path = Path(project_dir) / "markdown" / "roof_geometry.md"
    if not md_path.exists():
        md_path = Path(project_dir) / "MD" / "roof_geometry.md"
    if not md_path.exists():
        raise FileNotFoundError(
            f"ไม่พบ roof_geometry.md ใน {project_dir}/markdown/ หรือ MD/ -- โปรเจกต์นี้ยังไม่มีข้อมูลรูปทรงหลังคาที่ยืนยันแล้ว"
        )
    levels = load_keyvalue_section(md_path, "ระดับและมุมเอียง")
    grid = load_keyvalue_section(md_path, "กริดอ้างอิง (ม., จากคอลัมน์1/แถวA — ใช้ชุดเดียวกับ MD/floor_data.md)")
    overhang = load_keyvalue_section(md_path, "ชายคายื่นและระยะห่าง")
    stock = load_keyvalue_section(md_path, "สต๊อกเหล็ก")
    return {**levels, **grid, **overhang, **stock}


def derive_geometry(g):
    """Turn the raw confirmed facts (g) into every derived value the two-gable
    -plus-one-valley topology needs. Returns a dict consumed by compute_*()."""
    rise = g["ridge_level_m"] - g["eave_level_m"]
    pitch_angle_rad = math.atan(rise / g["pitch_reference_run_m"])
    slope_factor = 1.0 / math.cos(pitch_angle_rad)

    col1, col2, col4, col6 = g["col1"], g["col2"], g["col4"], g["col6"]
    row_a, row_b = g["rowA"], g["rowB"]
    ov_col, ov_row = g["overhang_col_m"], g["overhang_row_m"]

    # Main gable (spine): ridge at x=col2, plain gable both ends
    main_ridge_x = col2
    main_ridge_y_start = row_a - ov_row
    main_ridge_y_end = None  # filled below once we know the far row; see note
    # NOTE: this topology's main-gable south end is a free plain gable, whose
    # position (row E, or wherever the spine physically ends) is NOT part of
    # the valley/extension geometry -- it must come from the grid too.
    row_e = g.get("rowE")
    if row_e is None:
        raise KeyError(
            "roof_geometry.md ขาด 'rowE' ในหัวข้อกริดอ้างอิง -- ต้องมีตำแหน่งปลายจั่วหลักฝั่งอิสระ"
        )
    main_ridge_y_end = row_e + ov_row
    main_ridge_length = main_ridge_y_end - main_ridge_y_start
    main_west_run = (main_ridge_x - col1) + ov_col

    # Extension gable (front wing): ridge at row A-B midpoint, plain gable both ends
    ext_ridge_y = (row_a + row_b) / 2.0
    ext_ridge_x_start = col4
    ext_ridge_x_end = col6 + ov_col
    ext_ridge_length = ext_ridge_x_end - ext_ridge_x_start
    ext_north_run = (ext_ridge_y - row_a) + ov_row
    ext_south_run = (row_b - ext_ridge_y) + ov_row

    # Valley: apex where main ridge meets ext ridge; corners at (col4-ov_col, rowA/rowB)
    valley_apex = (main_ridge_x, ext_ridge_y)
    valley_corner_north = (col4 - ov_col, row_a)
    valley_corner_south = (col4 - ov_col, row_b)
    valley_north_half_depth = valley_apex[1] - row_a
    valley_south_half_depth = row_b - valley_apex[1]
    valley_run = valley_corner_north[0] - valley_apex[0]

    return {
        "rise_m": rise,
        "pitch_angle_deg": math.degrees(pitch_angle_rad),
        "slope_factor": slope_factor,
        "spacing_m": g["spacing_m"],
        "stock_length_m": g["stock_length_m"],
        "main_ridge_length_m": main_ridge_length,
        "main_west_run_m": main_west_run,
        "ext_ridge_length_m": ext_ridge_length,
        "ext_north_run_m": ext_north_run,
        "ext_south_run_m": ext_south_run,
        "valley_apex": valley_apex,
        "valley_corner_north": valley_corner_north,
        "valley_corner_south": valley_corner_south,
        "valley_north_half_depth_m": valley_north_half_depth,
        "valley_south_half_depth_m": valley_south_half_depth,
        "valley_run_m": valley_run,
    }


def taper_positions(depth, spacing):
    """Jack rafter positions (distance from the zero-length point) within a taper zone."""
    n = int(math.floor(depth / spacing + 1e-9))
    return [spacing * i for i in range(1, n + 1)]  # exclude the 0-length point at the apex


def compute_main_gable(geo):
    spacing = geo["spacing_m"]
    slope_factor = geo["slope_factor"]
    ridge_length = geo["main_ridge_length_m"]
    west_run = geo["main_west_run_m"]

    west_common_count = int(round(ridge_length / spacing)) + 1
    west_rafters = [west_run * slope_factor] * west_common_count

    # East "slope" only exists inside the valley zone, tapering from 0 at the
    # apex up to valley_run at each end (rowA and rowB).
    north_half = [
        geo["valley_run_m"] * (pos / geo["valley_north_half_depth_m"]) * slope_factor
        for pos in taper_positions(geo["valley_north_half_depth_m"], spacing)
    ]
    south_half = [
        geo["valley_run_m"] * (pos / geo["valley_south_half_depth_m"]) * slope_factor
        for pos in taper_positions(geo["valley_south_half_depth_m"], spacing)
    ]
    east_valley_rafters = north_half + south_half

    return {
        "ridge_length_m": ridge_length,
        "west_run_m": west_run,
        "west_rafter_count": west_common_count,
        "west_rafter_length_m": west_run * slope_factor,
        "west_rafters_total_m": sum(west_rafters),
        "east_valley_rafter_count": len(east_valley_rafters),
        "east_valley_rafters_lengths_m": sorted(east_valley_rafters, reverse=True),
        "east_valley_rafters_total_m": sum(east_valley_rafters),
    }


def compute_ext_gable(geo):
    spacing = geo["spacing_m"]
    slope_factor = geo["slope_factor"]
    ridge_length = geo["ext_ridge_length_m"]
    common_count = int(round(ridge_length / spacing)) + 1
    north_run, south_run = geo["ext_north_run_m"], geo["ext_south_run_m"]
    north_rafters = [north_run * slope_factor] * common_count
    south_rafters = [south_run * slope_factor] * common_count
    return {
        "ridge_length_m": ridge_length,
        "north_run_m": north_run,
        "south_run_m": south_run,
        "rafter_count_per_side": common_count,
        "north_rafter_length_m": north_run * slope_factor,
        "south_rafter_length_m": south_run * slope_factor,
        "north_rafters_total_m": sum(north_rafters),
        "south_rafters_total_m": sum(south_rafters),
    }


def compute_valley_rafters(geo):
    apex = geo["valley_apex"]
    corner_n = geo["valley_corner_north"]
    corner_s = geo["valley_corner_south"]
    dx = corner_n[0] - apex[0]
    dy_n = apex[1] - corner_n[1]
    dy_s = corner_s[1] - apex[1]
    horiz_n = math.hypot(dx, dy_n)
    horiz_s = math.hypot(dx, dy_s)
    slope_factor = geo["slope_factor"]
    return {
        "count": 2,
        "horizontal_lengths_m": [horiz_n, horiz_s],
        "slope_lengths_m": [horiz_n * slope_factor, horiz_s * slope_factor],
    }


def compute_ridge_and_kingpost(geo):
    spacing = geo["spacing_m"]
    main_len = geo["main_ridge_length_m"]
    ext_len = geo["ext_ridge_length_m"]
    total_ridge = main_len + ext_len
    kingpost_count = int(round(main_len / spacing)) + 1 + int(round(ext_len / spacing)) + 1
    return {
        "total_ridge_length_m": total_ridge,
        "main_ridge_m": main_len,
        "ext_ridge_m": ext_len,
        "kingpost_count": kingpost_count,
    }


def compute_eave_perimeter(geo):
    # Long-side eaves only (structural อะเส bearing lines); gable-end walls are not
    # counted here (no rafters bear on a gable end -- flagged as an assumption).
    main_west_eave = geo["main_ridge_length_m"]
    ext_north_eave = geo["ext_ridge_length_m"]
    ext_south_eave = geo["ext_ridge_length_m"]
    total = main_west_eave + ext_north_eave + ext_south_eave
    return {
        "main_west_eave_m": main_west_eave,
        "ext_north_eave_m": ext_north_eave,
        "ext_south_eave_m": ext_south_eave,
        "total_m": total,
    }


def compute_battens(sloped_area_m2, batten_spacing=0.32):
    # Practical shortcut: total batten length ~= sloped roof area / spacing between rows.
    return sloped_area_m2 / batten_spacing


def sloped_area(geo, main, ext, valley_run_zone_area_m2):
    main_west_area = main["ridge_length_m"] * main["west_run_m"]
    ext_north_area = ext["ridge_length_m"] * ext["north_run_m"]
    ext_south_area = ext["ridge_length_m"] * ext["south_run_m"]
    horizontal_total = main_west_area + ext_north_area + ext_south_area + valley_run_zone_area_m2
    return horizontal_total * geo["slope_factor"]


def report(geo):
    print(f"Pitch angle: {geo['pitch_angle_deg']:.3f} deg, slope factor: {geo['slope_factor']:.5f}\n")

    main_g = compute_main_gable(geo)
    ext_g = compute_ext_gable(geo)
    valley = compute_valley_rafters(geo)
    ridge = compute_ridge_and_kingpost(geo)
    eave = compute_eave_perimeter(geo)

    print("=== จันทัน (rafters, C 100x50x20x2.3mm @1.00m) ===")
    print(f"Main gable west slope: {main_g['west_rafter_count']} pcs x {main_g['west_rafter_length_m']:.3f}m "
          f"= {main_g['west_rafters_total_m']:.2f}m")
    print(f"Main gable east valley-taper zone: {main_g['east_valley_rafter_count']} pcs, "
          f"lengths(m)={[round(x,3) for x in main_g['east_valley_rafters_lengths_m']]}, "
          f"total={main_g['east_valley_rafters_total_m']:.2f}m")
    print(f"Extension gable north slope: {ext_g['rafter_count_per_side']} pcs x {ext_g['north_rafter_length_m']:.3f}m "
          f"= {ext_g['north_rafters_total_m']:.2f}m")
    print(f"Extension gable south slope: {ext_g['rafter_count_per_side']} pcs x {ext_g['south_rafter_length_m']:.3f}m "
          f"= {ext_g['south_rafters_total_m']:.2f}m")

    total_jantan_count = (main_g['west_rafter_count'] + main_g['east_valley_rafter_count']
                           + 2 * ext_g['rafter_count_per_side'])
    total_jantan_length = (main_g['west_rafters_total_m'] + main_g['east_valley_rafters_total_m']
                            + ext_g['north_rafters_total_m'] + ext_g['south_rafters_total_m'])
    print(f"--> total จันทัน: {total_jantan_count} pcs, {total_jantan_length:.2f} m\n")

    print("=== ตะเข้ราง / Valley rafters (2-C 150x50x20x2.3mm, same size as อะเส/ดั้ง) ===")
    for i, (h, s) in enumerate(zip(valley["horizontal_lengths_m"], valley["slope_lengths_m"]), 1):
        print(f"Valley rafter {i}: horizontal={h:.3f}m, slope length={s:.3f}m")
    print(f"--> total ตะเข้ราง: {valley['count']} pcs, {sum(valley['slope_lengths_m']):.2f} m\n")

    print("=== อกไก่ (ridge, 2-C 100x50x20x2.3mm) ===")
    print(f"Main ridge: {ridge['main_ridge_m']:.2f} m")
    print(f"Extension ridge: {ridge['ext_ridge_m']:.2f} m")
    print(f"--> total อกไก่: {ridge['total_ridge_length_m']:.2f} m\n")

    print("=== ดั้ง (king post, 2-C 150x50x20x2.3mm) @1.00m along ridge ===")
    print(f"--> total ดั้ง: {ridge['kingpost_count']} pcs\n")

    print("=== อะเส (eave beam, 2-C 150x50x20x2.3mm) -- long-side eaves only ===")
    print(f"Main gable west eave: {eave['main_west_eave_m']:.2f} m")
    print(f"Extension gable north eave: {eave['ext_north_eave_m']:.2f} m")
    print(f"Extension gable south eave: {eave['ext_south_eave_m']:.2f} m")
    print(f"--> total อะเส: {eave['total_m']:.2f} m\n")

    valley_zone_area = 2 * 0.5 * geo["valley_run_m"] * geo["valley_north_half_depth_m"]  # two triangles
    area = sloped_area(geo, main_g, ext_g, valley_zone_area)
    print("=== ระแนง (battens, box 25x25x1.6mm @0.32m) ===")
    print(f"Approx sloped roof area: {area:.2f} m^2")
    batten_len = compute_battens(area)
    print(f"--> total ระแนง (length shortcut, area/spacing): {batten_len:.2f} m\n")

    print("=== หมายเหตุ / assumptions flagged for review ===")
    print("- อะเส นับเฉพาะขอบชายคายาว (ฝั่งที่จันทันวางพาด) ไม่รวมผนังหน้าจั่ว (gable-end wall)")
    print("- ตะเข้เกิดเฉพาะจุดเดียว (โซนคอลัมน์2 ถึง col4-ชายคายื่น, แถวA-B) ตามที่ confirm แล้ว")
    print("- ไม่รวม แผ่นมุงหลังคา และ เชิงชายชัวร์ (งานสถาปัตย์/finish ตามที่ตกลงไว้)")

    return main_g, ext_g, ridge, eave


# ---------------------------------------------------------------------------
# Cutting list -- proper piece-based FFD, NOT total-length / stock-length
# (that undercounts whenever an individual piece is longer than one stock
# length, as the metasheet-roof Excel comparison exposed on 2569-09-01).
# ---------------------------------------------------------------------------

def splice_continuous_run(length_m, stock):
    """A continuous beam run (อะเส/อกไก่) spliced from stock: full-length
    segments plus one remainder segment (butt-jointed, normal practice for
    a straight beam -- unlike splicing a single-span rafter mid-length)."""
    full = int(length_m // stock)
    remainder = round(length_m - full * stock, 4)
    pieces = [stock] * full
    if remainder > 1e-6:
        pieces.append(remainder)
    return pieces


def ffd_pack(piece_lengths, stock):
    expanded = sorted(piece_lengths, reverse=True)
    bins = []
    for length in expanded:
        placed = False
        for i, remaining in enumerate(bins):
            if remaining >= length - 1e-9:
                bins[i] -= length
                placed = True
                break
        if not placed:
            bins.append(stock - length)
    return len(bins), sum(expanded), len(bins) * stock


def cutting_list_report(geo, main_g, ext_g, ridge, eave):
    stock = geo["stock_length_m"]
    print("\n" + "=" * 60)
    print(f"=== Cutting list (สต๊อก {stock}ม., ยืนยันแล้ว) ===")
    print("=" * 60)

    # --- Group 1: 2-C150x50x20x2.3 -- อะเส + ดั้ง ---
    eave_runs = [eave["main_west_eave_m"], eave["ext_north_eave_m"], eave["ext_south_eave_m"]]
    eave_pieces = []
    for run in eave_runs:
        eave_pieces += splice_continuous_run(run, stock)
    kingpost_pieces = [geo["rise_m"]] * ridge["kingpost_count"]  # each ดั้ง = rise height, own piece

    g1_pieces = eave_pieces + kingpost_pieces
    g1_bars, g1_used, g1_bought = ffd_pack(g1_pieces, stock)
    print(f"\n[2-C150x50x20x2.3mm] อะเส (splice {eave_pieces}) + ดั้ง ({len(kingpost_pieces)} x {geo['rise_m']}m)")
    print(f"  ชิ้นทั้งหมด: {len(g1_pieces)} ชิ้น, ใช้จริง {g1_used:.2f}m")
    print(f"  --> ต้องซื้อ {g1_bars} ท่อน ({g1_bought:.1f}m), ของเสีย {100*(g1_bought-g1_used)/g1_bought:.1f}%")

    # --- Group 2: 2-C100x50x20x2.3 -- อกไก่ only ---
    ridge_pieces = splice_continuous_run(main_g["ridge_length_m"], stock) + splice_continuous_run(ext_g["ridge_length_m"], stock)
    g2_bars, g2_used, g2_bought = ffd_pack(ridge_pieces, stock)
    print(f"\n[2-C100x50x20x2.3mm] อกไก่ (splice {ridge_pieces})")
    print(f"  --> ต้องซื้อ {g2_bars} ท่อน ({g2_bought:.1f}m), ของเสีย {100*(g2_bought-g2_used)/g2_bought:.1f}%")

    # --- Group 3: C100x50x20x2.3 (single) -- จันทัน only ---
    jantan_pieces = ([main_g["west_rafter_length_m"]] * main_g["west_rafter_count"]
                      + main_g["east_valley_rafters_lengths_m"]
                      + [ext_g["north_rafter_length_m"]] * ext_g["rafter_count_per_side"]
                      + [ext_g["south_rafter_length_m"]] * ext_g["rafter_count_per_side"])
    over_length = [p for p in jantan_pieces if p > stock + 1e-9]
    fits = [p for p in jantan_pieces if p <= stock + 1e-9]
    g3_bars, g3_used, g3_bought = ffd_pack(fits, stock)
    print(f"\n[C100x50x20x2.3mm เดี่ยว] จันทัน {len(jantan_pieces)} ชิ้น")
    if over_length:
        print(f"  ⚠️ {len(over_length)} ชิ้น ยาวเกินสต๊อก {stock}ม. (แต่ละชิ้นยาว {over_length[0]:.3f}ม.) "
              f"-- รอยต่อกลางเส้นจันทันไม่เหมาะ (จันทันรับแรงดัดตลอดช่วง) "
              f"ต้องสั่งสต๊อกยาวพิเศษ หรือใช้สต๊อกยาวกว่าตัดแบ่งแทน ไม่รวมในยอด cutting-list ด้านล่าง")
    print(f"  ชิ้นที่พอดีสต๊อก ({len(fits)} ชิ้น): --> ต้องซื้อ {g3_bars} ท่อน ({g3_bought:.1f}m), "
          f"ของเสีย {100*(g3_bought-g3_used)/g3_bought:.1f}%")

    print("\n⚠️ ระแนง (กล่อง25x25x1.6) — ยังทำ cutting list ไม่ได้ เพราะความยาวรวมมาจากการประมาณ"
          " (พื้นที่÷ระยะห่าง) ไม่มีรายชิ้นความยาวจริงให้ pack")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project_dir", help='path ไปยังโฟลเดอร์โปรเจกต์ เช่น "../../new house"')
    args = ap.parse_args()

    raw = load_geometry(args.project_dir)
    geo = derive_geometry(raw)
    main_g, ext_g, ridge, eave = report(geo)
    cutting_list_report(geo, main_g, ext_g, ridge, eave)


if __name__ == "__main__":
    main()
