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

import fitz

import grid_utils
from project_md_data import load_keyvalue_section, load_table_section

# --- physical steel weight, applies to any project using these bar sizes ---
RB9_KG_PER_M = 0.499
RB6_KG_PER_M = 0.222

# ค่ามาตรฐานงานพื้น S1 บ้านพักอาศัยทั่วไปเมื่อไม่มีตารางสเปคให้อ่าน (สมมติฐาน ไม่ใช่ค่ายืนยันเฉพาะ
# โปรเจกต์ -- ใช้เมื่อ auto_extract_floor_boq หาสเปคจริงจากแบบไม่ได้เท่านั้น ต้องระบุในผลลัพธ์เสมอว่า
# เป็นค่าประมาณ)
DEFAULT_S1_THICKNESS_M = 0.10
DEFAULT_TOPPING_THICKNESS_M = 0.05
DEFAULT_MAIN_MESH_SPACING_M = 0.20
DEFAULT_S1_COVER_M = 0.025
DEFAULT_CHAIR_LENGTH_M = 0.10

ROOM_PLAN_DESCRIPTION_KEYWORDS = ("แปลนพื",)  # ตัดท้ายคำ "แปลนพื้น" เพราะบางไฟล์ฟอนต์เพี้ยนตัวท้ายหาย

ROOM_VISION_PROMPT = """ภาพนี้คือแปลนพื้นบ้าน (architectural floor plan) วาดตามมาตราส่วนที่ระบุไว้ในภาพ
(ดูข้อความ SCALE หรือ "1 : N") มีเส้นกริด (วงกลมมีตัวอักษร/ตัวเลข) และเส้นบอกระยะ (หน่วยเมตร) รอบขอบและ
ภายในแปลน

งานของคุณ: อ่านทุกห้องในแปลนนี้ (ห้องนอน, ห้องนํ้า, ครัว, รับแขก, ทานอาหาร, เฉลียง, ระเบียง, โถง ฯลฯ) แล้ว:
1. ชื่อห้อง (name_th) -- อ่านจากป้ายชื่อในห้องนั้น
2. รหัสวัสดุพื้น (floor_material_code) -- ป้ายเล็กใต้ชื่อห้อง เช่น "F1", "F2", "F3" (ถ้าไม่มีให้เป็น null)
3. ขนาดห้องโดยประมาณเป็นสี่เหลี่ยมผืนผ้าครอบ (bounding box) -- width_m (แนวนอน) และ length_m (แนวตั้ง)
   หน่วยเมตร คำนวณจากเส้นบอกระยะที่ล้อมรอบห้องนั้นจริง ไม่ใช่กะด้วยสายตาเฉยๆ ถ้าห้องเป็นรูปตัว L หรือไม่
   เป็นสี่เหลี่ยมสมบูรณ์ ให้ใช้กรอบสี่เหลี่ยมที่ครอบทั้งห้องพอดี (จะได้พื้นที่มากกว่าจริงเล็กน้อยสำหรับ
   ห้องรูปตัว L -- ยอมรับได้เพราะเผื่องานก่อสร้างอยู่แล้ว)
4. confidence ("measured" ถ้าคำนวณจากเส้นบอกระยะได้ครบ, "estimated" ถ้าต้องกะบางส่วน)

ตอบเป็น JSON ล้วนๆ เท่านั้น ไม่มีข้อความอื่น:
{"scale": "อ่านจากภาพ เช่น 1:75", "rooms": [{"name_th": "...", "floor_material_code": "F1"|null, "width_m": 0.0, "length_m": 0.0, "confidence": "measured"|"estimated"}]}"""


def find_room_plan_page(doc):
    """หาแผ่นแปลนพื้นสถาปัตย์ผ่านสารบัญแบบของไฟล์นั้นเอง (ดู grid_utils.find_sheet_code_by_description
    -- ไม่ hardcode รหัสแผ่น เพราะยืนยันแล้วว่าไม่เหมือนกันข้ามโปรเจกต์) คืน (pno, sheet_code) หรือ
    (None, None) ถ้าหาไม่เจอ"""
    code, _desc = grid_utils.find_sheet_code_by_description(doc, list(ROOM_PLAN_DESCRIPTION_KEYWORDS))
    if code is None:
        return None, None
    pno = grid_utils.find_drawing_page_by_title_block(doc, code)
    return pno, code


def read_rooms_via_vision(doc, pno, dpi=250):
    """ส่งภาพแปลนพื้นทั้งหน้าให้ AI vision อ่านชื่อห้อง+รหัสวัสดุพื้น+พื้นที่ -- ต้องใช้ AI vision เพราะ
    ป้ายชื่อห้องบนแปลนสถาปัตย์เกือบทุกไฟล์ถูก flatten เป็น vector/curve อ่านด้วย page.get_text() ไม่ได้
    เลย (ยืนยันแล้วกับทั้ง 116-69 และไฟล์อื่น -- ตัวเลขบอกระยะยังอ่านได้ปกติ แต่ป้ายชื่อห้องอ่านไม่ได้)"""
    import ai_vision_fallback
    page = doc[pno]
    pix = page.get_pixmap(dpi=dpi)
    return ai_vision_fallback.call_vision_json(pix.tobytes("png"), ROOM_VISION_PROMPT,
                                                model="claude-sonnet-5", max_tokens=16000)


def auto_extract_floor_boq(pdf_path):
    """ถอดปริมาณพื้นแบบอัตโนมัติเต็มรูปแบบ ไม่ต้องรอ MD/floor_data.md ที่ยืนยันกับเจ้าของโปรเจกต์ก่อน --
    หาแผ่นแปลนพื้นเองผ่านสารบัญแบบ แล้วให้ AI vision อ่านชื่อห้อง+พื้นที่+วัสดุพื้นจากแปลนโดยตรง

    ข้อจำกัดที่ทราบ (ต้องระบุในผลลัพธ์เสมอ ไม่ปิดบัง):
    - พื้นที่ห้องเป็น**ค่าประมาณจาก AI vision อ่านเส้นบอกระยะในแปลนภาพรวม** ไม่ใช่การวัดละเอียดจากแบบขยาย
      เฉพาะห้อง (ห้องเล็ก/ซับซ้อนอย่างห้องน้ำอาจคลาดเคลื่อนได้มากกว่าห้องสี่เหลี่ยมง่ายๆ)
    - ระบบพื้นโครงสร้าง (HC พื้นสำเร็จรูป vs S1 พื้นหล่อในที่) **ไม่มีทางอ่านได้จากแปลนสถาปัตย์** (เป็น
      ข้อมูลจากแปลนวิศวกรรมโครงสร้างคนละแผ่น ที่ป้ายกำกับมักไม่ตรงกับขอบเขตห้องสถาปัตย์ตรงๆ) -- กำหนด
      เป็น S1 (พื้นหล่อในที่) ทุกห้องเป็นค่าเริ่มต้นแบบอนุรักษ์นิยม (ปลอดภัยกว่าเพราะคำนวณคอนกรีต+เหล็ก
      เต็มปริมาณ ไม่ใช่แค่ topping เหมือน HC) พร้อมระบุชัดว่าเป็นค่าสมมติ ต้องตรวจกับแบบวิศวกรรมจริงก่อน
      ใช้งานจริง
    - หนา/ระยะห่างเหล็กเสริมใช้ค่ามาตรฐานทั่วไป (DEFAULT_* ด้านบน) ไม่ใช่ค่าที่อ่านจากตารางสเปคของไฟล์นี้
      โดยตรง (ยังไม่ได้ทำส่วนหาตารางสเปคพื้นอัตโนมัติ)"""
    doc = fitz.open(pdf_path)
    pno, sheet_code = find_room_plan_page(doc)
    if pno is None:
        return {"status": "room_plan_not_found",
                "notes": ["หาแผ่นแปลนพื้นสถาปัตย์ผ่านสารบัญแบบไม่เจอ -- อาจไม่มีคำว่า 'แปลนพื้น' ในสารบัญ"
                          " หรือหาหน้าสารบัญเองไม่เจอ"]}

    try:
        import ai_vision_fallback  # noqa: F401
    except ImportError as e:
        return {"status": "blocked_no_ai_vision", "notes": [f"import ai_vision_fallback ไม่สำเร็จ: {e}"]}

    try:
        vision_result = read_rooms_via_vision(doc, pno)
    except Exception as e:
        return {"status": "vision_call_failed", "notes": [f"AI vision เรียกไม่สำเร็จ (หน้า {pno + 1}): {e}"]}

    if vision_result.get("_parse_error") or not vision_result.get("rooms"):
        return {"status": "vision_parse_failed",
                "notes": [f"AI vision อ่านผลไม่สำเร็จ (หน้า {pno + 1})", str(vision_result.get("_raw"))[:300]]}

    room_list = []
    for r in vision_result["rooms"]:
        w, l = r.get("width_m"), r.get("length_m")
        if not w or not l:
            continue
        room_list.append({
            "name": r.get("name_th") or "?",
            "system": "S1",
            "width_m": round(float(w), 2), "length_m": round(float(l), 2),
            "floor_material_code": r.get("floor_material_code"),
            "area_confidence": r.get("confidence", "estimated"),
        })
    if not room_list:
        return {"status": "no_rooms_read", "notes": ["AI vision อ่านหน้าแปลนพื้นได้แต่ไม่พบห้องที่มีพื้นที่เลย"]}

    params = {
        "s1_thickness_m": DEFAULT_S1_THICKNESS_M,
        "topping_thickness_m": DEFAULT_TOPPING_THICKNESS_M,
        "main_mesh_spacing_m": DEFAULT_MAIN_MESH_SPACING_M,
        "s1_cover_m": DEFAULT_S1_COVER_M,
        "chair_length_m": DEFAULT_CHAIR_LENGTH_M,
    }
    result = compute_floor_boq(room_list, params)
    result["status"] = "computed_auto"
    result["source"] = "ai_vision_estimate"
    result["room_plan_page"] = pno + 1
    result["room_plan_sheet_code"] = sheet_code
    result["notes"] = [
        "ถอดอัตโนมัติจากแปลนพื้นด้วย AI vision (ไม่ผ่านการยืนยันกับเจ้าของโปรเจกต์) -- พื้นที่ต่อห้องเป็น"
        "ค่าประมาณจากเส้นบอกระยะในแปลนภาพรวม ไม่ใช่แบบขยายเฉพาะห้อง คลาดเคลื่อนได้โดยเฉพาะห้องเล็ก/ซับซ้อน",
        f"กำหนดระบบพื้นเป็น S1 (พื้นหล่อในที่) ทุกห้องเป็นค่าเริ่มต้น เพราะแปลนสถาปัตย์ไม่มีข้อมูลระบบพื้น"
        f"โครงสร้าง -- หนา {DEFAULT_S1_THICKNESS_M}ม. เป็นค่ามาตรฐานทั่วไป ไม่ใช่ค่าที่อ่านจากไฟล์นี้",
    ]
    return result





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
