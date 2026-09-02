"""ไพน้อย — งานโครงสร้าง: ถอดปริมาณพื้น (Floor: HC พื้นสำเร็จรูป / S1 พื้นเทในที่)

Unlike the footing/pier/beam scripts, room shapes here are NOT read via Claude
vision + API call. S-02 (the structural beam/floor plan) was tried first and
its grid-based room shapes turned out wrong (interior partition walls do not
follow the structural column/beam grid at all) - confirmed against A-04 (the
real architectural floor plan) by manually tracing each room's walls back to
the dimension chains on A-04, cross-checked with the project owner room by
room. ROOM_LIST below is that confirmed data - a lookup table, not a live
extraction - because this drawing set has no clean machine-parseable source
for small partition-wall rooms (see 03-ai-boq-procedure.md หมวด 1: "ห้ามใช้
กริดโครงสร้างสมมติรูปทรง/ขนาดห้องสถาปัตย์").

Rules encoded here, confirmed by the project owner 2569-08-30
(03-ai-boq-procedure.md หมวด 1, "กฎงานพื้น"):
- HC (precast plank, Hollow Core): floor slab is a purchased product priced
  per m^2, NOT a concrete-volume calc. Site work adds a 0.05m concrete
  topping (with 4mm wire mesh @0.20m) over it.
- S1 (cast-in-place slab): straightforward volume = area x thickness (0.10m
  here, per S-09). Includes the two exterior "ระเบียง" (terrace) zones -
  their wood/tile finish sits ON TOP of an S1 slab, confirmed by the owner,
  so they still count as S1 concrete underneath.
- No fixed HC cutting-waste % is applied here - see the retracted "5-8%"
  finding in 03-ai-boq-procedure.md: this project's real net area already
  matched the purchased quantity almost exactly (+0.8%), so no waste factor
  is baked into ROOM_LIST; add one explicitly per-project if evidence
  supports it.

Project-specific data (room list + slab parameters, confirmed with this
project's owner) lives in <project>/MD/floor_data.md, NOT in this file -
this script is meant to be reusable across projects; only the calculation
rules below (which are general Thai-construction conventions, not tied to
one house) stay as code. See project_md_data.py for the loader and
03-ai-boq-procedure.md หมวด 1 for the underlying rules this encodes.

Usage:
    python extract_floor_boq.py "../../new house"
    (reads <project>/MD/floor_data.md; no PDF/API call - see note above)
"""
import argparse
from pathlib import Path

from project_md_data import load_keyvalue_section, load_table_section

# --- physical steel weight, applies to any project using these bar sizes ---
RB9_KG_PER_M = 0.499
RB6_KG_PER_M = 0.222


def compute_s1_rebar(s1_rooms, params):
    total_bottom_len = 0.0
    total_top_len = 0.0
    total_chairs = 0
    spacing = params["main_mesh_spacing_m"]
    cover = params["s1_cover_m"]
    for room in s1_rooms:
        Lx, Ly = room["width_m"], room["length_m"]
        n_x = round(Ly / spacing)
        n_y = round(Lx / spacing)
        total_bottom_len += n_x * (Lx - 2 * cover) + n_y * (Ly - 2 * cover)
        total_top_len += 2 * n_x * (Lx / 4) + 2 * n_y * (Ly / 4)
        total_chairs += 2 * n_x + 2 * n_y

    main_mesh_len = total_bottom_len + total_top_len
    chair_len = total_chairs * params["chair_length_m"]
    return {
        "main_mesh_bottom_m": round(total_bottom_len, 1),
        "main_mesh_top_m": round(total_top_len, 1),
        "main_mesh_total_m": round(main_mesh_len, 1),
        "main_mesh_rb9_kg": round(main_mesh_len * RB9_KG_PER_M, 1),
        "chair_count": total_chairs,
        "chair_total_m": round(chair_len, 1),
        "chair_rb6_kg": round(chair_len * RB6_KG_PER_M, 1),
    }


def compute_floor_boq(room_list, params):
    rows = []
    hc_area = 0.0
    s1_area = 0.0
    for room in room_list:
        area = room.get("area_override_m2")
        if area is None:
            area = room["width_m"] * room["length_m"]
        rows.append({**room, "area_m2": round(area, 2)})
        if room["system"] == "HC":
            hc_area += area
        elif room["system"] == "S1":
            s1_area += area
        else:
            raise ValueError(f"unknown floor system '{room['system']}' for room {room['name']}")

    topping_vol = hc_area * params["topping_thickness_m"]
    s1_vol = s1_area * params["s1_thickness_m"]
    s1_rebar = compute_s1_rebar([r for r in room_list if r["system"] == "S1"], params)

    return {
        "rows": rows,
        "hc_area_m2": round(hc_area, 2),
        "s1_area_m2": round(s1_area, 2),
        "total_area_m2": round(hc_area + s1_area, 2),
        "hc_topping_concrete_m3": round(topping_vol, 3),
        "s1_concrete_m3": round(s1_vol, 3),
        "total_concrete_m3": round(topping_vol + s1_vol, 3),
        "wire_mesh_area_m2": round(hc_area, 2),
        "s1_rebar": s1_rebar,
    }


def load_project_floor_data(project_dir):
    md_path = Path(project_dir) / "markdown" / "floor_data.md"
    if not md_path.exists():
        md_path = Path(project_dir) / "MD" / "floor_data.md"
    if not md_path.exists():
        raise FileNotFoundError(
            f"ไม่พบ floor_data.md ใน {project_dir}/markdown/ หรือ MD/ -- โปรเจกต์นี้ยังไม่มีข้อมูลพื้นที่ยืนยันแล้ว"
        )
    params = load_keyvalue_section(md_path, "พารามิเตอร์พื้น")
    room_list = load_table_section(md_path, "รายการห้อง")
    return room_list, params


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project_dir", help='path ไปยังโฟลเดอร์โปรเจกต์ เช่น "../../new house"')
    args = ap.parse_args()

    room_list, params = load_project_floor_data(args.project_dir)
    result = compute_floor_boq(room_list, params)
    print("=== ผลคำนวณ (โค้ด Python ล้วน, ห้องมาจากการอ่าน A-04 ยืนยันกับเจ้าของโปรเจกต์แล้ว) ===\n")
    for row in result["rows"]:
        print(f"  {row['name']:55s} [{row['system']}] {row['area_m2']:7.2f} m2")
    print()
    print(f"พื้นที่ HC สุทธิ:        {result['hc_area_m2']} m2")
    print(f"พื้นที่ S1 สุทธิ:        {result['s1_area_m2']} m2")
    print(f"รวมทั้งบ้าน:            {result['total_area_m2']} m2")
    print(f"คอนกรีต topping (HC):   {result['hc_topping_concrete_m3']} m3")
    print(f"คอนกรีต S1:             {result['s1_concrete_m3']} m3")
    print(f"คอนกรีตพื้นรวม:         {result['total_concrete_m3']} m3")
    print(f"ไวร์เมช (topping):      {result['wire_mesh_area_m2']} m2")
    print()
    r = result["s1_rebar"]
    print(f"เหล็กตาข่ายหลัก RB9@0.15 พื้น S1: {r['main_mesh_total_m']} m "
          f"(ล่าง {r['main_mesh_bottom_m']}m + บน {r['main_mesh_top_m']}m) = {r['main_mesh_rb9_kg']} kg")
    print(f"เหล็กคอม้า RB6 พื้น S1: {r['chair_count']} ชิ้น x {params['chair_length_m']}m = {r['chair_total_m']}m = {r['chair_rb6_kg']} kg")


if __name__ == "__main__":
    main()
