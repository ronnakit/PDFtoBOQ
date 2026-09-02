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
import re
from collections import defaultdict
from pathlib import Path

import fitz

import extract_footing_boq
import grid_utils
from project_md_data import load_keyvalue_section, load_table_section
from thai_font_fix import extract_fixed_spans

# --- physical steel weight, applies to any project using these bar sizes (kg/m = pi/4 * d^2 * 7850) ---
RB9_KG_PER_M = 0.499
RB6_KG_PER_M = 0.222


def bar_kg_per_m(diameter_mm):
    """น้ำหนักเหล็กเส้นกลม/ตะแกรงลวดต่อเมตร จากเส้นผ่านศูนย์กลาง (สูตรฟิสิกส์ล้วน ใช้ได้ทุกขนาด ไม่ต้อง
    มีตาราง lookup แยกทีละขนาด)"""
    d_m = diameter_mm / 1000.0
    area_m2 = 3.141592653589793 / 4 * d_m ** 2
    return area_m2 * 7850.0

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

FLOOR_SPEC_DESCRIPTION_KEYWORDS = ("แบบขยายพื้น",)

FLOOR_SPEC_VISION_PROMPT = """ภาพนี้คือแบบขยายรายละเอียดพื้น (floor detail expansion) ของบ้าน อาจมีพื้น
หลายชนิด แต่ละชนิดมีรหัสกำกับในวงกลม (เช่น "S", "GS", "PS", "S1", "HC" -- ชื่อรหัสต่างกันได้ตามแต่ละไฟล์)
พร้อมรูปตัดแสดงรายละเอียดการก่อสร้าง -- อ่านทุกชนิดที่เห็นในภาพ (ไม่ใช่แค่ชนิดเดียว)

สำหรับพื้นแต่ละชนิด:
1. code -- รหัสในวงกลมตามที่เห็นเป๊ะๆ
2. is_precast -- true ถ้ามีข้อความ "แผ่นพื้นสำเร็จรูป"/"precast" ในรูปตัด (พื้นสำเร็จรูป+เทคอนกรีตทับหน้า
   บางๆ), false ถ้าเป็นคอนกรีตหล่อในที่ล้วน
3. concrete_thickness_m -- ความหนาคอนกรีตที่ต้องเทจริง: ถ้า is_precast=true ใช้ความหนา "Topping" เท่านั้น
   (ไม่ใช่ความหนาแผ่นสำเร็จรูปเอง เพราะแผ่นสำเร็จรูปเป็นผลิตภัณฑ์ซื้อสำเร็จ ไม่ใช่คอนกรีตที่หล่อหน้างาน)
   ถ้า is_precast=false ใช้ความหนาคอนกรีตพื้นตามที่ระบุ
4. rebar_diameter_mm -- เส้นผ่านศูนย์กลางเหล็กเสริม/ตะแกรงลวดหลัก (ตัวเลขหลัง "RB" หรือ "dia." เช่น
   "RB9mm." → 9, "Wire mesh-dia.4mm." → 4)
5. rebar_spacing_m -- ระยะห่างเหล็กเสริม/ตะแกรงลวด (ตัวเลขหลัง @ หน่วยเมตร)
6. rebar_layers -- จำนวนชั้นเหล็กเสริมที่วางซ้อนกัน (ปกติ 1 ชั้น แต่ถ้าเห็นทั้งเหล็กเสริมหลักและ "เสริม
   พิเศษ" ขนาด/ระยะเดียวกันวางแยกกันคนละชั้น ให้เป็น 2)
7. supported_by -- "beam" ถ้าพื้นวางพาดบนคาน (มีคำว่า "BEAM" ในรูปตัด), "ground" ถ้าพื้นวางบนดิน/ทราย
   อัดแน่นโดยตรง ไม่ใช่พื้นที่รับน้ำหนักพาดช่วง (เช่นมีคำว่า "ทรายอัดแน่น"/"ระดับดินเดิม" ใต้พื้นโดยตรง)

ตอบเป็น JSON ล้วนๆ เท่านั้น ไม่มีข้อความอื่น:
{"systems": [{"code": "...", "is_precast": false, "concrete_thickness_m": 0.0, "rebar_diameter_mm": 0,
"rebar_spacing_m": 0.0, "rebar_layers": 1, "supported_by": "beam"|"ground"}]}"""


def read_floor_system_specs_via_vision(doc):
    """หาแผ่นแบบขยายพื้นผ่านเนื้อหาหัวข้อเอง (ไม่ hardcode รหัสแผ่น) แล้วให้ AI vision อ่านสเปคจริงของ
    พื้นทุกชนิดที่มีในไฟล์นี้ (ความหนาคอนกรีต+เหล็กเสริม+รองรับด้วยคานหรือดิน) -- แทนที่ DEFAULT_* ที่เคย
    ใช้เป็นค่าประมาณทั่วไปเมื่อยังไม่มีฟังก์ชันนี้ คืน (pno, result) หรือ (None, None) ถ้าหาแผ่นไม่เจอ"""
    pno = grid_utils.find_page_by_content(doc, list(FLOOR_SPEC_DESCRIPTION_KEYWORDS))
    if pno is None:
        return None, None
    import ai_vision_fallback
    page = doc[pno]
    pix = page.get_pixmap(dpi=250)
    result = ai_vision_fallback.call_vision_json(pix.tobytes("png"), FLOOR_SPEC_VISION_PROMPT,
                                                  model="claude-sonnet-5", max_tokens=4000)
    return pno, result


def compute_floor_zone_areas_from_structural_grid(doc, valid_codes):
    """กำหนดพื้นที่พื้นแต่ละชนิด (ตาม valid_codes ที่อ่านจากตารางสเปคจริง เช่น S/GS/PS) จากป้ายรหัสบน
    แปลนคาน-พื้นเชิงโครงสร้างเอง (แผ่นเดียวกับที่ footing/pier ใช้) -- ป้ายเหล่านี้เป็น text จริง (ไม่
    flatten เหมือนป้ายชื่อห้องสถาปัตย์) จับคู่แต่ละ "ช่องกริด" (cell ระหว่างเส้นกริดที่ติดกัน) กับป้าย
    รหัสที่ใกล้ที่สุด แล้วรวมพื้นที่ตามรหัส -- ให้พื้นที่รวม**ทั้งหมด (gross, รวมพื้นที่ใต้ผนัง)** ซึ่ง
    ถูกต้องกว่าพื้นที่ห้องสุทธิจากแปลนสถาปัตย์สำหรับคำนวณปริมาตรคอนกรีต (คอนกรีตเทเต็มช่วงคาน ไม่ใช่แค่
    ในห้อง) -- ทดสอบแล้วกับสันคือ: รวมได้ 153.69 ตร.ม. ตรงกับพื้นที่ฐานอาคารจากกริด (9.20x16.70=153.64
    ตร.ม.) เกือบเป๊ะ ยืนยันว่าวิธีนี้ใช้ได้ (ต่างจากการจับคู่ป้ายชื่อห้องสถาปัตย์กับกริดที่เคยลองแล้วผิด
    +34% เพราะผนังภายในไม่ตรงกริด -- อันนี้จับคู่รหัสโครงสร้างที่ตรงกริดโดยธรรมชาติอยู่แล้ว)

    คืน (pno, {code: area_m2}) หรือ (None, {}) ถ้าหาแผ่น/กริด/ป้ายไม่เจอ"""
    pno = grid_utils.find_page_by_content(doc, extract_footing_boq.FOOTING_PLAN_TITLE_KEYWORDS, require_grid=True)
    if pno is None:
        pno = grid_utils.find_page_with_most_markers(doc, extract_footing_boq.PIER_OR_COMBINED_RE, min_count=3)
    if pno is None:
        return None, {}

    spans = extract_fixed_spans(doc[pno])
    columns, rows = grid_utils.extract_grid(spans)
    scale = grid_utils.find_scale_denominator(spans)
    if not columns or not rows or not scale:
        return pno, {}
    pts_per_m = grid_utils.points_per_meter(scale)

    tags = [(s["text"].strip(), *grid_utils.center(s["bbox"])) for s in spans
            if s["text"].strip() in valid_codes]
    if not tags:
        return pno, {}

    # จำกัดเส้นกริดเฉพาะฝั่งที่มีป้ายรหัสอยู่ใกล้ (กันกริดฝั่งอื่นบนหน้าเดียวกัน เช่นแปลนฐานรากที่อยู่
    # คนละกริดแต่วาดรวมหน้าเดียวกับแปลนคาน-พื้น)
    tag_xs = [t[1] for t in tags]
    cols = sorted(set(x for _l, x in columns if min(tag_xs) - 150 <= x <= max(tag_xs) + 150))
    rows_y = sorted(set(y for _l, y in rows))

    area_by_code = defaultdict(float)
    for i in range(len(cols) - 1):
        for j in range(len(rows_y) - 1):
            x0, x1 = cols[i], cols[i + 1]
            y0, y1 = rows_y[j], rows_y[j + 1]
            area = ((x1 - x0) / pts_per_m) * ((y1 - y0) / pts_per_m)
            if area < 0.05:
                continue
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            nearest = min(tags, key=lambda t: (t[1] - cx) ** 2 + (t[2] - cy) ** 2)
            area_by_code[nearest[0]] += area
    return pno, dict(area_by_code)


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
    """ถอดปริมาณพื้นแบบอัตโนมัติเต็มรูปแบบ ไม่ต้องรอ MD/floor_data.md ที่ยืนยันกับเจ้าของโปรเจกต์ก่อน

    ลำดับ (ทุกขั้นอ่านจากแบบจริงของไฟล์นั้น ไม่มี default ทั่วไปอีกต่อไปถ้าอ่านสำเร็จ):
    1. หาแบบขยายพื้น อ่านสเปคจริงของพื้นทุกชนิด (ความหนาคอนกรีต+เหล็กเสริม+รองรับด้วยคานหรือดิน) --
       `read_floor_system_specs_via_vision`
    2. เอารหัสพื้นที่อ่านได้ไปหาพื้นที่แต่ละชนิดจากป้ายรหัสจริงบนแปลนคาน-พื้นเชิงโครงสร้าง (โค้ดล้วน ไม่ใช่
       AI vision, จับคู่ช่องกริดกับป้ายที่ใกล้ที่สุด) -- `compute_floor_zone_areas_from_structural_grid`
       ให้พื้นที่รวม (gross) ที่ถูกต้องสำหรับคำนวณคอนกรีต ไม่ใช่พื้นที่ห้องสุทธิ
    3. อ่านแปลนพื้นสถาปัตย์เพิ่มสำหรับชื่อห้อง (label เท่านั้น ไม่ใช่ตัวเลขที่ใช้คำนวณ)
    4. ถ้าขั้น 1-2 อ่านไม่สำเร็จ fallback ไปใช้ DEFAULT_* + พื้นที่ห้องรวมจากแปลนสถาปัตย์แทน (เดิม)
       ระบุชัดในผลลัพธ์ว่า fallback ไปทางไหน"""
    doc = fitz.open(pdf_path)

    spec_pno, spec_result = read_floor_system_specs_via_vision(doc)
    systems = {}
    if spec_pno is not None and spec_result and not spec_result.get("_parse_error"):
        for s in spec_result.get("systems", []):
            code = s.get("code")
            if not code or not s.get("concrete_thickness_m"):
                continue
            systems[code] = s

    zone_pno, zone_areas = (None, {})
    if systems:
        zone_pno, zone_areas = compute_floor_zone_areas_from_structural_grid(doc, set(systems.keys()))

    room_pno, room_sheet_code = find_room_plan_page(doc)
    room_names = []
    if room_pno is not None:
        try:
            import ai_vision_fallback  # noqa: F401
            vision_result = read_rooms_via_vision(doc, room_pno)
            if not vision_result.get("_parse_error"):
                room_names = [r.get("name_th") for r in vision_result.get("rooms", []) if r.get("name_th")]
        except Exception:
            pass

    notes = []
    if systems and zone_areas:
        # ทางหลัก: สเปคจริง + พื้นที่จริงจากป้ายรหัสบนแปลนโครงสร้าง
        zones = []
        total_area = 0.0
        total_concrete = 0.0
        total_rebar_kg = 0.0
        for code, area in zone_areas.items():
            spec = systems.get(code)
            if not spec:
                continue
            thickness = spec["concrete_thickness_m"]
            concrete_m3 = round(area * thickness, 3)
            rebar_kg = 0.0
            if spec.get("rebar_diameter_mm") and spec.get("rebar_spacing_m"):
                # สูตรความยาวตะแกรงสองทิศทางที่ระยะห่างเท่ากัน L = 2*Area/spacing ไม่ขึ้นกับสัดส่วนกว้าง/ยาว
                # (พิสูจน์ทางคณิตศาสตร์: (W/s)*L + (L/s)*W = 2WL/s = 2*Area/s พอดี)
                mesh_len_m = 2 * area / spec["rebar_spacing_m"] * (spec.get("rebar_layers") or 1)
                rebar_kg = round(mesh_len_m * bar_kg_per_m(spec["rebar_diameter_mm"]), 1)
            zones.append({
                "code": code, "area_m2": round(area, 2), "is_precast": bool(spec.get("is_precast")),
                "supported_by": spec.get("supported_by"), "concrete_thickness_m": thickness,
                "concrete_m3": concrete_m3, "rebar_diameter_mm": spec.get("rebar_diameter_mm"),
                "rebar_spacing_m": spec.get("rebar_spacing_m"), "rebar_kg": rebar_kg,
            })
            total_area += area
            total_concrete += concrete_m3
            total_rebar_kg += rebar_kg

        notes.append(
            f"พื้นที่แต่ละชนิดมาจากป้ายรหัส ({', '.join(sorted(systems.keys()))}) บนแปลนคาน-พื้นเชิง"
            f"โครงสร้างจริง (หน้า {zone_pno + 1}) จับคู่กับช่องกริด ไม่ใช่ค่าประมาณ -- เป็นพื้นที่รวม "
            "(gross ทั้งช่วงคาน) ไม่ใช่พื้นที่ห้องสุทธิ เพราะคอนกรีตเทเต็มช่วงคานจริง")
        notes.append(f"สเปคคอนกรีต+เหล็กเสริมอ่านจากแบบขยายพื้นจริง (หน้า {spec_pno + 1}) ไม่ใช่ค่ามาตรฐานทั่วไป")
        if room_names:
            notes.append(f"ชื่อห้อง (สำหรับอ้างอิงเท่านั้น ไม่ใช่ฐานคำนวณ): {', '.join(room_names)}")

        return {
            "status": "computed_auto", "source": "structural_grid_and_spec",
            "zones": zones, "room_names": room_names,
            "spec_page": spec_pno + 1, "zone_page": zone_pno + 1,
            "room_plan_page": (room_pno + 1) if room_pno is not None else None,
            "total_area_m2": round(total_area, 2),
            "total_concrete_m3": round(total_concrete, 3),
            "total_rebar_kg": round(total_rebar_kg, 1),
            "notes": notes,
        }

    # fallback: อ่านสเปคจริง/พื้นที่จริงไม่สำเร็จ -- ใช้ทางเดิม (ห้องจากแปลนสถาปัตย์ + ค่ามาตรฐานทั่วไป)
    if room_pno is None:
        return {"status": "room_plan_not_found",
                "notes": ["หาแบบขยายพื้น/แปลนพื้นสถาปัตย์ผ่านสารบัญแบบไม่เจอเลย -- อาจไม่มีคำว่า 'แปลนพื้น'"
                          "/'แบบขยายพื้น' ในสารบัญ หรือหาหน้าสารบัญเองไม่เจอ"]}
    try:
        import ai_vision_fallback  # noqa: F401
        vision_result = read_rooms_via_vision(doc, room_pno)
    except Exception as e:
        return {"status": "vision_call_failed", "notes": [f"AI vision เรียกไม่สำเร็จ (หน้า {room_pno + 1}): {e}"]}
    if vision_result.get("_parse_error") or not vision_result.get("rooms"):
        return {"status": "vision_parse_failed",
                "notes": [f"AI vision อ่านผลไม่สำเร็จ (หน้า {room_pno + 1})", str(vision_result.get("_raw"))[:300]]}

    room_list = []
    for r in vision_result["rooms"]:
        w, l = r.get("width_m"), r.get("length_m")
        if not w or not l:
            continue
        room_list.append({
            "name": r.get("name_th") or "?", "system": "S1",
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
    result["source"] = "ai_vision_estimate_fallback"
    result["room_plan_page"] = room_pno + 1
    result["room_plan_sheet_code"] = room_sheet_code
    result["notes"] = [
        "หาแบบขยายพื้น/สเปคจริงหรือป้ายรหัสบนแปลนโครงสร้างไม่สำเร็จ -- fallback มาใช้พื้นที่ห้องจากแปลน"
        "สถาปัตย์ (ค่าประมาณจากเส้นบอกระยะในแปลนภาพรวม ไม่ใช่แบบขยายเฉพาะห้อง) + ค่ามาตรฐานทั่วไปแทน",
        f"กำหนดระบบพื้นเป็น S1 (พื้นหล่อในที่) ทุกห้องเป็นค่าเริ่มต้น -- หนา {DEFAULT_S1_THICKNESS_M}ม. "
        "เป็นค่ามาตรฐานทั่วไป ไม่ใช่ค่าที่อ่านจากไฟล์นี้",
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
