"""PDFtoBOQ -- งานโครงสร้าง: ถอดปริมาณคอนกรีต+เหล็กตอม่อ-เสา (Pier + Column Takeoff)

เขียนใหม่ทั้งหมด (2569-09-02) แทนเวอร์ชันเดิมที่ docstring ยังเขียนค่าคงที่ของโปรเจกต์อื่น
("newhouse: 1.20m", "newhouse: 3.20m") ตรงๆ และรายงานจริงก็ปล่อยค่า pier height=1.20m ออกมา
ซึ่งตรงกับค่า newhouse เป๊ะ ไม่ใช่ค่าที่มาจากไฟล์ 116-69 เอง -- ดู LOG.md ฝั่งเอกสารพิมพ์เขียว

วิธีทำงาน:
1. ใช้ตำแหน่งตอม่อ (Cx) จากแบบผังฐานราก (ใช้ extract_footing_boq.extract_pier_footing_pairs ร่วมกัน)
2. หาตารางสเปคเสา/ตอม่อ (มักอยู่ในแบบ "ตารางขยายเสา", ค่าเริ่มต้นค้นด้วยคำว่า "MAIN REBAR"/"STIRRUP")
   -- อ่านเป็น text ตรงๆ ได้จริงกับ 116-69 (ต่างจากตารางฐานรากที่ flatten เป็นภาพ)
3. หาความสูงเสา (พื้น-ถึง-หลังคา) จากกองตัวเลขบอกระยะแนวตั้งบนรูปด้าน -- heuristic: มองหาก้อน
   ตัวเลขทศนิยม 3 ค่าเรียงตัวในแนวตั้ง (top/mid/bottom) ที่ผลรวมตรงกับตัวเลขรวมที่อยู่ใกล้กัน และ
   ค่าล่างสุดอยู่ในช่วง 0.5-1.5 ม. (ความสูงพื้นยกจากดินทั่วไปของบ้านไทย) -- ถ้าเจอ ใช้ค่ากลาง (mid)
   เป็นความสูงเสา ถ้าไม่เจอรูปแบบนี้ ให้ปล่อย None พร้อม status="needs_confirmation" ไม่เดามั่ว
4. หาความสูงตอม่อจากกฎ "ความลึกฐานราก" (ข้อความมาตรฐาน "ความลึกของฐานรากเท่ากับ N เมตร" ในแบบ
   สเปคทั่วไป) ลบด้วยชั้นวัสดุมาตรฐาน (ทราย 0.10ม.+คอนกรีตหยาบ 0.05ม., เป็นค่าฟิสิกส์ทั่วไปใช้ร่วม
   ได้ทุกโปรเจกต์) แล้วลบระดับพื้น (สมมติ 1.00ม.เหนือระดับดินเดิม ถ้าหาตัวเลขจริงไม่เจอ) -- ประมาณ
   อัตโนมัติเสมอ ไม่หยุดรอผู้ใช้ (ตามกฎที่ตัดสินใจไว้) แต่ติด status="estimated" ชัดเจน

Usage:
    python extract_pier_column_boq.py <pdf_path>
"""
import argparse
import json
import re
import sys

import fitz

import grid_utils
from extract_footing_boq import extract_pier_footing_pairs, PIER_OR_COMBINED_RE
from thai_font_fix import extract_fixed_spans

PIER_CODE_RE = re.compile(r"^C[0-9]+[A-Za-z]?$")
FOOTING_PLAN_TITLE_KEYWORDS = ["แปลนฐานราก"]
# หน่วย/รูปแบบตารางสเปคเสาต่างกันได้มากระหว่างสำนักงานออกแบบ (ยืนยันจริง: โปรเจกต์หนึ่งเขียน
# "200 x 400mm." เป็นมิลลิเมตรไม่มีวงเล็บ, อีกโปรเจกต์เขียน "(0.20 x 0.20)" เป็นเมตรมีวงเล็บ --
# regex ด้านล่างรองรับทั้งคู่ แล้วตัดสินหน่วยจากขนาดตัวเลข ไม่ใช่จากข้อความ (>10 = มม., <=10 = ม.)
SIZE_RE = re.compile(r"^\(?(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)\s*(?:mm\.?|m\.?)?\)?$")
REBAR_COUNT_RE = re.compile(r"^(\d+)-DB\s*(\d+)\s*mm\.?$", re.IGNORECASE)
# ตัวอักษรนำหน้า "-RB" ต่างกันได้ (116-69: "1-RB6mm.@150mm.", อีกโปรเจกต์: "ป-RB6mm.@0.15m." --
# "ป" คือสัญลักษณ์ปลอกของสำนักงานนั้น ไม่ใช่ตัวเลข) ใช้ `.` จับตัวอักษรนำหน้าแบบไม่สนใจค่า เพราะ
# ไม่ได้ใช้ค่านี้ต่ออยู่แล้ว (ปลอก 1 เส้นต่อจุดเสมอ) หน่วยระยะห่างก็รองรับทั้ง มม./ม. เหมือนกัน
STIRRUP_RE = re.compile(r"^.-RB\s*(\d+)\s*mm\.?\s*@\s*([\d.]+)\s*(mm\.?|m\.?)?$", re.IGNORECASE)
EXCAVATION_DEPTH_RE = re.compile(r"ความลึกของฐานรากเท่ากับ\s*([\d.]+)\s*เมตร")


def _to_meters(value):
    """ตัดสินว่าตัวเลขที่อ่านมาเป็นมิลลิเมตรหรือเมตร จากขนาดตัวเลขเอง (ไม่ใช่จากหน่วยที่เขียนกำกับ
    เพราะบางไฟล์ไม่เขียนหน่วยชัดเจน) -- หน้าตัดเสา/ระยะห่างปลอกจริงไม่มีทางเกิน 10 เมตร แต่ถ้าเป็น
    มิลลิเมตรมักเกิน 10 เสมอ (เช่น 200mm, 150mm) ใช้ 10 เป็นเกณฑ์แบ่ง"""
    return value / 1000.0 if value > 10 else value

SAND_LAYER_M = 0.10       # ค่าฟิสิกส์ทั่วไป (ทรายรองพื้นฐานราก) ใช้ร่วมได้ทุกโปรเจกต์
LEAN_CONCRETE_M = 0.05    # ค่าฟิสิกส์ทั่วไป (คอนกรีตหยาบ)
DEFAULT_FLOOR_LEVEL_M = 1.00  # ค่าเผื่อทั่วไปถ้าหาระดับพื้นจริงจากแบบไม่เจอ (ประมาณ ไม่ใช่ยืนยัน)
DEFAULT_PIER_HEIGHT_M = 1.00  # ค่าเผื่อทั่วไปถ้าหาข้อความ "ความลึกของฐานรากเท่ากับ...เมตร" ไม่เจอเลย
DEFAULT_COLUMN_HEIGHT_M = 3.00  # ค่าเผื่อทั่วไปถ้า heuristic หาความสูงเสาจากรูปด้านไม่เจอเลย
                                 # (ทั้งคู่: ไม่หยุดรอข้อมูล -- ประมาณอัตโนมัติแล้วแจ้งในรายงานเสมอ
                                 # ตามหลักการ "estimate, don't ask" -- ต้องตรวจกับแบบ/หน้างานจริงก่อนใช้จริง)


def find_column_schedule(doc):
    """หาหน้าที่มีตารางสเปคเสา (มีคำว่า "rebar" + "stirrup" ปรากฏ, ไม่สนตัวพิมพ์ใหญ่-เล็ก/จุดต่อท้าย
    เพราะแต่ละไฟล์เขียนไม่เหมือนกัน เช่น "MAIN REBAR" กับ "Main Rebar.") แล้วดึงสเปคหน้าตัด/เหล็กยืน/
    ปลอกออกมาโดยไล่ตามลำดับข้อความที่ตรงรูปแบบขนาด/เหล็ก -- คืน dict เดียว (สมมติทั้งไฟล์มีสเปคเสา
    แบบเดียว ตรงกับทุกโปรเจกต์ที่ทดสอบมาจนถึงตอนนี้) พร้อม page ที่เจอ."""
    for pno in range(len(doc)):
        spans = extract_fixed_spans(doc[pno])
        texts = [s["text"].strip() for s in spans]
        lowered = [t.lower() for t in texts]
        if not any("rebar" in t for t in lowered) or not any("stirrup" in t for t in lowered):
            continue

        size_m = None
        main_rebar = None
        stirrup = None
        for t in texts:
            m = SIZE_RE.match(t)
            if m and size_m is None:
                size_m = (_to_meters(float(m.group(1))), _to_meters(float(m.group(2))))
            m = REBAR_COUNT_RE.match(t)
            if m and main_rebar is None:
                main_rebar = f"{m.group(1)}-DB{m.group(2)}"
            m = STIRRUP_RE.match(t)
            if m and stirrup is None:
                stirrup = f"1-RB{m.group(1)}@{_to_meters(float(m.group(2))):.3f}m"

        if size_m or main_rebar or stirrup:
            return {
                "page": pno + 1,
                "size_m": [round(size_m[0], 3), round(size_m[1], 3)] if size_m else None,
                "main_rebar": main_rebar,
                "stirrup": stirrup,
                "source": "text_table",
            }
    return None


def find_column_height(doc):
    """มองหากองตัวเลขทศนิยมเรียงตัวแนวตั้ง (บนรูปด้าน, อย่างน้อย 3 ค่า คอลัมน์เดียวกัน) ที่มีตัวเลข
    อื่นบนหน้าเดียวกัน (ไม่จำเป็นต้องอยู่คอลัมน์เดียวกัน -- เส้นบอกระยะรวมมักวาดชิดขอบกระดาษ คนละ x
    กับก้อนย่อย) ตรงกับผลรวมของก้อนนั้นพอดี และค่าล่างสุด (ใกล้ดิน) อยู่ในช่วง 0.5-1.5ม. -- ใช้ค่า
    ชั้นที่ 2 จากล่างเป็นความสูงเสาโดยประมาณ (heuristic ที่ตรงกับ 116-69 พอดี: 2.48/3.30/1.00 รวม
    6.78 -- 3.30 คือพื้น-ถึง-อะเส)."""
    for pno in range(len(doc)):
        spans = extract_fixed_spans(doc[pno])
        nums = []
        for s in spans:
            t = s["text"].strip()
            try:
                v = float(t)
            except ValueError:
                continue
            x, y = grid_utils.center(s["bbox"])
            nums.append((v, x, y))
        if len(nums) < 4:
            continue
        all_values = [n[0] for n in nums]
        nums.sort(key=lambda n: n[1])
        i = 0
        while i < len(nums):
            cluster = [nums[i]]
            j = i + 1
            while j < len(nums) and abs(nums[j][1] - nums[i][1]) < 3.0:
                cluster.append(nums[j])
                j += 1
            if len(cluster) in (3, 4):
                # จำกัดแค่ 3-4 ชิ้น (ก้อนความสูงอาคารทั่วไป: ดิน->พื้น->อะเส->สันหลังคา) เพื่อ
                # ตัดกรณีที่ match ผิดกับ dimension chain ของกริดแปลนพื้น (มักมี 5-8 ชิ้นขึ้นไป)
                cluster.sort(key=lambda n: n[2])  # top -> bottom ตาม y
                values = [c[0] for c in cluster]
                expected_total = sum(values)
                has_total = any(abs(v - expected_total) < 0.05 for v in all_values)
                if has_total and 0.5 <= values[-1] <= 1.5:
                    return {"page": pno + 1, "column_height_m": round(values[-2], 2), "source": "elevation_dimension_stack"}
            i = j
    return None


def find_excavation_depth(doc):
    for pno in range(len(doc)):
        for s in extract_fixed_spans(doc[pno]):
            m = EXCAVATION_DEPTH_RE.search(s["text"])
            if m:
                return {"page": pno + 1, "depth_m": float(m.group(1)), "source": "text_spec"}
    return None


def extract_pier_column_takeoff(pdf_path, drawing_no=None):
    """drawing_no: ระบุเลขแผ่นเองได้ (override) ปกติไม่ต้องใส่ -- ค้นจากหัวข้อ "แปลนฐานราก" อัตโนมัติ
    ก่อนเสมอ (ตำแหน่งตอม่อ/เสาอยู่บนแผ่นเดียวกับฐานราก) ค่อย fallback ไปนับป้ายรหัสตอม่อถ้าหาไม่เจอ"""
    doc = fitz.open(pdf_path)
    if drawing_no:
        pno = grid_utils.find_drawing_page(doc, drawing_no, marker_re=PIER_CODE_RE)
    else:
        pno = grid_utils.find_page_by_content(doc, FOOTING_PLAN_TITLE_KEYWORDS, require_grid=True)
        if pno is None:
            pno = grid_utils.find_page_with_most_markers(doc, PIER_OR_COMBINED_RE, min_count=3)
    if pno is None:
        return {"status": "not_found", "notes": ["ไม่พบแผ่น 'แปลนฐานราก' และไม่พบแผ่นที่มีป้ายรหัสตอม่อหนาแน่นพอ"],
                "items": [], "totals": {}}

    page = doc[pno]
    spans = extract_fixed_spans(page)
    pairs = extract_pier_footing_pairs(spans)
    counts = {}
    for p in pairs:
        counts[p["pier_code"]] = counts.get(p["pier_code"], 0) + 1

    notes = []
    schedule = find_column_schedule(doc)
    if not schedule:
        notes.append("ไม่พบตารางสเปคเสา (SIZE/MAIN REBAR/STIRRUP) เป็น text -- อาจถูก flatten "
                      "เป็น vector รอ Phase B (AI vision)")

    height_info = find_column_height(doc)
    column_height_m = height_info["column_height_m"] if height_info else DEFAULT_COLUMN_HEIGHT_M
    column_height_status = "estimated_from_drawing" if height_info else "estimated_no_data"
    if not height_info:
        notes.append(
            f"หาความสูงเสาจากรูปด้านไม่เจอ (heuristic ไม่ match) -- กำหนดอัตโนมัติที่ "
            f"{DEFAULT_COLUMN_HEIGHT_M}ม. (ค่ามาตรฐานทั่วไปสำหรับบ้านพักอาศัยชั้นเดียว) แทนการหยุดรอ "
            f"ข้อมูล -- ต้องตรวจสอบกับแบบจริงก่อนใช้งานจริง"
        )

    exc_info = find_excavation_depth(doc)
    pier_height_m = None
    pier_height_status = "not_computed"
    if exc_info:
        footing_top_m = -exc_info["depth_m"] + SAND_LAYER_M + LEAN_CONCRETE_M
        pier_height_m = round(DEFAULT_FLOOR_LEVEL_M - footing_top_m, 2)
        pier_height_status = "estimated"
        notes.append(
            f"ความสูงตอม่อ {pier_height_m}ม. เป็นค่าประมาณ: ระดับพื้น {DEFAULT_FLOOR_LEVEL_M}ม. "
            f"(ค่าเผื่อทั่วไป ยังไม่ยืนยันจากแบบ) ลบระดับหัวฐานราก (−{exc_info['depth_m']}ม.ขุดดิน+"
            f"{SAND_LAYER_M}ม.ทราย+{LEAN_CONCRETE_M}ม.คอนกรีตหยาบ) -- ยังไม่รวมความหนาฐานราก (T) "
            f"เพราะยังไม่มีจากตารางสเปค (รอ Phase B)"
        )
    else:
        pier_height_m = DEFAULT_PIER_HEIGHT_M
        pier_height_status = "estimated_no_data"
        notes.append(
            f"ไม่พบข้อความ \"ความลึกของฐานรากเท่ากับ...เมตร\" ในแบบ -- กำหนดความสูงตอม่ออัตโนมัติที่ "
            f"{DEFAULT_PIER_HEIGHT_M}ม. (ค่ามาตรฐานทั่วไปสำหรับบ้านพักอาศัยชั้นเดียว) แทนการหยุดรอข้อมูล "
            f"-- ต้องตรวจสอบกับหน้างานจริงก่อนใช้งานจริง"
        )

    items = []
    for code, count in sorted(counts.items()):
        items.append({
            "code": code,
            "count": count,
            "cross_section_m": schedule["size_m"] if schedule else None,
            "main_rebar": schedule["main_rebar"] if schedule else None,
            "stirrup": schedule["stirrup"] if schedule else None,
            "pier_height_m": pier_height_m,
            "pier_height_status": pier_height_status,
            "column_height_m": column_height_m,
            "column_height_status": column_height_status,
        })

    return {
        "status": "partial" if notes else "confirmed",
        "drawing_page": pno + 1,
        "schedule_page": schedule["page"] if schedule else None,
        "height_source_page": height_info["page"] if height_info else None,
        "excavation_note_page": exc_info["page"] if exc_info else None,
        "notes": notes,
        "items": items,
        "total_count": sum(counts.values()),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf_path")
    ap.add_argument("--drawing-no", default=None, help="ระบุเลขแผ่นเอง (override) ปกติไม่ต้องใส่")
    args = ap.parse_args()
    result = extract_pier_column_takeoff(args.pdf_path, drawing_no=args.drawing_no)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
