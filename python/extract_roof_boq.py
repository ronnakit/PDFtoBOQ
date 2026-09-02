"""PDFtoBOQ -- งานโครงสร้าง: ถอดปริมาณเหล็กโครงสร้างหลังคา (Roof Steel Takeoff)

เขียนใหม่ทั้งหมด (2569-09-02) แทนเวอร์ชันเดิมที่ผูกกับโทโพโลยีหลังคาของโปรเจกต์เดียว (newhouse, อ่าน
จาก MD/roof_geometry.md) ใช้กับโปรเจกต์อื่นไม่ได้เลย -- ดู LOG.md ของฝั่งเอกสารพิมพ์เขียว 2569-09-02

ต่างจากฐานราก/ตอม่อ-เสาตรงที่**ใช้ AI vision เป็นวิธีหลัก ไม่ใช่ fallback ของโค้ดล้วน** เพราะเรขาคณิต
หลังคาซับซ้อนและแตกต่างกันมากในแต่ละหลัง -- แต่มี 2 ทางเลือกเรียงลำดับความน่าเชื่อถือ:

1. **ทางหลัก (แม่นกว่า):** ถ้าไฟล์นี้มีตาราง "ถอดปริมาณงานโครงสร้างคานเหล็กหลังคา" ที่ผู้ออกแบบสรุปความยาว
   รวมแต่ละชนิดไว้เอง (แทบทุกครั้งถูก flatten เป็น vector อ่านด้วย text ไม่ได้เลย -- ยืนยันแล้วกับ 116-69)
   ใช้ตัวเลขนั้นเลย น่าเชื่อถือกว่าให้โค้ด/AI นับเส้นเอง
2. **ทางสำรอง (เมื่อไม่มีตารางสรุปเลย):** ให้ AI vision อ่านเรขาคณิต+ตารางสเปคเหล็กจากแปลนโครงหลังคา
   โดยตรง (`_extract_roof_from_framing_plan`) -- **ไม่ใช่ข้อจำกัดที่ทำให้หยุดเป็น "not_found" อีกต่อไป**
   (แก้ 2569-09-02 ตามคำสั่งเจ้าของโปรเจกต์: "ทำไมต้องหาตารางถอดปริมาณ...เราจะให้ไพน้อยอ่านแบบและถอดอยู่
   แล้ว") -- แม่นยำต่ำกว่าทางหลัก โดยเฉพาะจันทัน/แปที่ต้องประมาณจำนวนเส้นจากระยะห่าง (@1.00ม. ฯลฯ) ไม่ได้
   นับทีละเส้นจริง ทุก item มี confidence กำกับ (measured/estimated) เสมอ

วิธีทำงานทางหลัก:
1. หาแผ่นแบบที่มีตารางนี้จาก**เนื้อหาหัวตารางเอง** (ค้นทุกหน้า ไม่ใช้เลขแผ่นเป็นตัวกรอง เพราะเลขแผ่น
   เป็นธรรมเนียมเฉพาะสำนักงานออกแบบแต่ละที่ ไม่สื่อความหมายเดียวกันข้ามโปรเจกต์ -- ยืนยันแล้วกับหมวดอื่น)
2. หาตำแหน่งตาราง**แบบ dynamic ไม่ hardcode พิกัด** -- ค้นข้อความ "ถอดปริมาณ"+"หลังคา" ที่ยังอ่านได้
   เป็นหัวตาราง (แม้ตัวข้อมูลในตารางจะ flatten แต่หัวข้อตารางมักเป็น text จริง) ใช้ตำแหน่งนั้นเป็นขอบบน
   แล้ว crop กว้างพอไปทางขวา+ลงล่างของหน้า เรนเดอร์ที่ dpi สูง (300) เพื่อให้ AI อ่านตัวเลขได้แม่นที่สุด
3. ส่งภาพที่ crop แล้วให้ AI vision อ่านทุกแถว คืนเป็นสเปคหน้าตัด (โปรไฟล์/ขนาด/ความหนา) แยกจากชื่อ
   ภาษาไทย -- ให้ AI ทำหน้าที่ OCR+parse ไปพร้อมกัน แม่นกว่าใช้ regex จับข้อความไทยที่เขียนไม่คงรูปแบบ
4. คำนวณน้ำหนักจากสูตรฟิสิกส์ (พื้นที่หน้าตัด x ความหนาแน่นเหล็ก) ไม่ใช่ตาราง kg/m ที่ลอกมา -- ใช้ได้กับ
   ทุกสเปคหน้าตัดที่ AI อ่านมา ไม่ต้องมีตาราง lookup แยก

รายการที่ profile="unknown" (ไม่มีสเปคหน้าตัดในชื่อแถว เช่นวัสดุครอบสัน/ครอบหลังคา) จะไม่ถูกคำนวณน้ำหนัก
เพราะไม่ใช่เหล็กโครงสร้างที่แปลงน้ำหนักได้แบบเดียวกัน -- รายงานความยาวแยกไว้ต่างหาก ไม่ปนกับน้ำหนักเหล็ก
โครงสร้างรวม เพื่อไม่ให้ตัวเลขสองความหมายถูกบวกกันโดยไม่รู้ตัว

ขอบเขต: เฉพาะเหล็กโครงสร้างหลังคา -- แผ่นมุงหลังคา/เชิงชายเป็นงานสถาปัตย์ ไม่รวมในนี้

Usage:
    python extract_roof_boq.py <pdf_path>
"""
import argparse
import json
import re
import sys

import fitz

import grid_utils
from thai_font_fix import extract_fixed_spans

STEEL_DENSITY_KG_PER_M3 = 7850.0
ROOF_STEEL_CUTTING_WASTE = 0.05

TABLE_TITLE_KEYWORDS = ("ถอดปริมาณ", "หลังคา")
FRAMING_PLAN_DESCRIPTION_KEYWORDS = ("แปลนโครงหลังคา",)

ROOF_FRAME_VISION_PROMPT = """ภาพนี้คือแปลนโครงสร้างหลังคา (roof framing plan) ของบ้าน วาดตามมาตราส่วนที่
ระบุในภาพ มีเส้นกริด+เส้นบอกระยะ (เมตร) และมักมีตาราง "รายการเหล็กโครงสร้างหลังคา" อยู่ในภาพเดียวกัน ระบุ
ชนิดเหล็ก (เช่น อะเส, ตั้ง, อกไก่, จันทัน, แป) คู่กับขนาดหน้าตัดและระยะห่าง (เช่น "จันทัน C-100x50x20x2.0mm.
@1.00 ม." = จันทันหน้าตัดนี้ วางห่างกันทุก 1.00 ม.)

**ไฟล์นี้ไม่มีตาราง "ถอดปริมาณ" สรุปความยาวรวมจากผู้ออกแบบ (ตรวจแล้ว) จึงต้องคำนวณความยาวรวมแต่ละชนิดเอง
จากแปลน**

งานของคุณ: สำหรับเหล็กแต่ละชนิดที่มีสเปคหน้าตัดชัดเจน (ไม่นับวัสดุมุงหลังคา/ครอบสันที่ไม่ใช่เหล็กโครงสร้าง)
1. name_th -- ชื่อชนิด (เช่น "อะเส", "จันทัน", "แป", "อกไก่", "ตั้ง")
2. profile: "C" หรือ "box" (อ่านจากสเปคหน้าตัดในตาราง) หรือ "unknown" ถ้าไม่ใช่เหล็กโครงสร้าง
3. double: true ถ้าสเปคมี "2C" นำหน้า, dim1_mm/dim2_mm/dim3_mm/thickness_mm จากสเปคหน้าตัดในตาราง
4. total_length_m -- ความยาวรวมโดยประมาณ คำนวณจาก:
   - อะเส/อกไก่: ความยาวตามแนวขอบ/สันที่วิ่งจริงในแปลน (วัดจากเส้นบอกระยะ/กริด)
   - จันทัน/แป: จำนวนเส้น (ประมาณจากความยาวขอบหลังคา ÷ ระยะห่างที่ระบุ เช่น @1.00ม.) × ความยาวเฉลี่ยต่อเส้น
     (ประมาณจากขนาดหลังคาที่เห็นในแปลน ถ้าไม่เห็นมุมลาดชัดเจนให้ใช้ระยะทางแนวราบจากขอบถึงสันเป็นค่าประมาณ
     ระบุ confidence เป็น "estimated" เสมอสำหรับกรณีนี้)
5. confidence: "measured" (คำนวณจากเส้นบอกระยะที่ชัดเจนครบ) หรือ "estimated" (ต้องประมาณเพราะไม่เห็นมุมลาด/
   เรขาคณิตที่ซับซ้อนเกินกว่าจะนับละเอียด)

ตอบเป็น JSON ล้วนๆ เท่านั้น ไม่มีข้อความอื่น:
{"rows": [{"name_th": "...", "profile": "C"|"box"|"unknown", "double": false, "dim1_mm": 0, "dim2_mm": 0,
"dim3_mm": null, "thickness_mm": 0, "total_length_m": 0.0, "confidence": "measured"|"estimated"}]}"""

ROOF_TABLE_VISION_PROMPT = """ภาพนี้คือตาราง "ถอดปริมาณงานโครงสร้างคานเหล็กหลังคา" มี 2 คอลัมน์: ชนิด
โครงสร้างเหล็กหลังคา, ความยาวโดยรวม (ม.) อ่านทุกแถว (รวมแถว Grand total ถ้ามี) แล้วตอบเป็น JSON ล้วนๆ
เท่านั้น ไม่มีข้อความอื่น:
{
  "rows": [
    {
      "name_th": "ข้อความคอลัมน์แรกตามที่เห็นเป๊ะๆ ทุกตัวอักษร",
      "total_length_m": ตัวเลขความยาว,
      "profile": "C" หรือ "box" หรือ "unknown" (unknown ถ้าไม่มีสเปคหน้าตัดเหล็กในชื่อแถว เช่นเป็นวัสดุ
                  มุงหลังคา/ครอบสัน ไม่ใช่เหล็กโครงสร้าง),
      "double": true หรือ false (true ถ้าสเปคมี "2C" นำหน้า),
      "dim1_mm": ตัวเลขแรกของสเปคหน้าตัด, "dim2_mm": ตัวเลขที่สอง,
      "dim3_mm": ตัวเลขที่สาม (null ถ้าเป็นท่อกล่องมีแค่ 2 ค่า), "thickness_mm": ความหนา
    }
  ],
  "grand_total_length_m": ตัวเลขจากแถว Grand total (null ถ้าไม่มี),
  "grand_total_count": จำนวนชิ้นรวมจากแถว Grand total (null ถ้าไม่มี)
}"""


def steel_profile_weight_kg_per_m(profile, dim1_mm, dim2_mm, dim3_mm, thickness_mm, double=False):
    """น้ำหนักเหล็กรูปพรรณเบา (cold-formed) ต่อเมตร จากสูตรฟิสิกส์ (พื้นที่หน้าตัด x ความหนาแน่นเหล็ก)
    ไม่ใช่ค่าที่ลอกมาจากแค็ตตาล็อก -- ใช้ประมาณความยาวเส้นรอบรูปจากศูนย์กลางผนัง (ลบความหนาที่มุมพับ)
    ตามหลักการมาตรฐานของเหล็กรูปพรรณเบา (cold-formed steel), มีความคลาดเคลื่อนเล็กน้อยจากค่าจริงในแค็ต
    ตาล็อกของแต่ละโรงงาน (รัศมีมุมพับ/สูตรลดพื้นที่ต่างกันเล็กน้อย) แต่เพียงพอสำหรับเป้าหมายความแม่นยำ
    95-105% ของสินค้านี้."""
    if profile == "box" and dim1_mm and dim2_mm and thickness_mm:
        centerline_perimeter_mm = 2 * dim1_mm + 2 * dim2_mm - 4 * thickness_mm
    elif profile == "C" and dim1_mm and dim2_mm and thickness_mm:
        leg3 = dim3_mm or 0
        centerline_perimeter_mm = dim1_mm + 2 * dim2_mm + 2 * leg3 - 4 * thickness_mm
    else:
        return None
    area_mm2 = centerline_perimeter_mm * thickness_mm
    kg_per_m = area_mm2 * STEEL_DENSITY_KG_PER_M3 * 1e-6
    return kg_per_m * 2 if double else kg_per_m


def _find_table_crop_region(page, spans):
    """หาตำแหน่งตาราง "ถอดปริมาณ...หลังคา" แบบ dynamic จากข้อความหัวตาราง (ยังอ่านได้แม้ตัวข้อมูลใน
    ตารางจะ flatten) -- คืน fitz.Rect ให้ crop หรือ None ถ้าหาหัวตารางไม่เจอในหน้านี้เลย."""
    title_span = None
    for s in spans:
        t = s["text"]
        if all(k in t for k in TABLE_TITLE_KEYWORDS):
            title_span = s
            break
    if title_span is None:
        return None

    x0, y0, x1, y1 = title_span["bbox"]
    page_w, page_h = page.rect.width, page.rect.height

    notes_y = None
    for s in spans:
        if s["text"].strip().startswith("หมายเหตุ") and s["bbox"][1] > y1:
            notes_y = s["bbox"][1]
            break

    crop_x0 = max(0, x0 - 90)
    crop_y0 = y1
    crop_x1 = page_w - 20
    crop_y1 = notes_y if notes_y else min(page_h, y1 + 250)
    return fitz.Rect(crop_x0, crop_y0, crop_x1, crop_y1)


SHEET_NUMBER_RE = re.compile(r"^[A-Z]{1,3}-\d{2,3}$")


def _read_sheet_number(page, spans, bottom_fraction=0.88):
    """อ่านเลขแผ่น (เช่น "S-07") จาก title block ท้ายหน้าแบบ dynamic -- ใช้แค่โชว์อ้างอิงในผลลัพธ์
    เท่านั้น ไม่ใช่ใช้หาแผ่น (หาแผ่นด้วยเนื้อหาหัวตารางแทน ดู _find_table_crop_region)"""
    h = page.rect.height
    for s in spans:
        text = s["text"].strip().upper()
        y = (s["bbox"][1] + s["bbox"][3]) / 2
        if SHEET_NUMBER_RE.match(text) and y > h * bottom_fraction:
            return text
    return None


def _extract_roof_from_framing_plan(doc):
    """เมื่อไม่มีตาราง "ถอดปริมาณ" สรุปจากผู้ออกแบบเลย -- หาแปลนโครงหลังคาเองผ่านสารบัญแบบของไฟล์นั้น
    (เช่นเดียวกับที่ extract_floor_boq.py ทำกับแปลนพื้น) แล้วให้ AI vision อ่านเรขาคณิต+ตารางสเปคเหล็ก
    ที่มักอยู่ในแปลนเดียวกัน คำนวณความยาวรวมเอง -- ความแม่นยำต่ำกว่าทางตารางสรุปของผู้ออกแบบ (โดยเฉพาะ
    จันทัน/แป ที่ต้องประมาณจากระยะห่าง@ ไม่ใช่นับทีละเส้น) แต่ให้ตัวเลขออกมาได้เสมอแทนที่จะหยุดเป็น
    not_found -- ทุก item ระบุ confidence กำกับชัดเจน"""
    code, _desc = grid_utils.find_sheet_code_by_description(doc, list(FRAMING_PLAN_DESCRIPTION_KEYWORDS))
    if code is None:
        return {"status": "not_found",
                "notes": ["ไม่พบตาราง 'ถอดปริมาณงานโครงสร้างคานเหล็กหลังคา' และไม่พบแปลนโครงหลังคาใน "
                          "สารบัญแบบเลย -- ไม่มีทางถอดปริมาณหลังคาได้จากไฟล์นี้"],
                "items": [], "non_structural_rows": []}
    pno = grid_utils.find_drawing_page_by_title_block(doc, code)
    if pno is None:
        return {"status": "not_found",
                "notes": [f"สารบัญแบบระบุแปลนโครงหลังคาเป็นแผ่น {code} แต่หาแผ่นนั้นในเอกสารไม่เจอจริง"],
                "items": [], "non_structural_rows": []}

    try:
        import ai_vision_fallback
    except ImportError as e:
        return {"status": "blocked_no_ai_vision", "notes": [f"import ai_vision_fallback ไม่สำเร็จ: {e}"],
                "items": [], "non_structural_rows": []}

    page = doc[pno]
    try:
        pix = page.get_pixmap(dpi=250)
        result = ai_vision_fallback.call_vision_json(pix.tobytes("png"), ROOF_FRAME_VISION_PROMPT,
                                                       model="claude-sonnet-5", max_tokens=8000)
    except Exception as e:
        return {"status": "vision_call_failed", "notes": [f"AI vision เรียกไม่สำเร็จ (หน้า {pno + 1}): {e}"],
                "items": [], "non_structural_rows": []}

    if result.get("_parse_error") or not result.get("rows"):
        return {"status": "vision_parse_failed",
                "notes": [f"AI vision อ่านแปลนโครงหลังคาไม่สำเร็จ (หน้า {pno + 1})", str(result.get("_raw"))[:300]],
                "items": [], "non_structural_rows": []}

    items, non_structural = [], []
    total_length_structural = 0.0
    total_weight_net = 0.0
    estimated_count = 0
    for row in result["rows"]:
        name = row.get("name_th") or "?"
        length = row.get("total_length_m")
        if row.get("profile") in ("C", "box") and length:
            if row.get("confidence") == "estimated":
                estimated_count += 1
            kg_per_m = steel_profile_weight_kg_per_m(
                row.get("profile"), row.get("dim1_mm"), row.get("dim2_mm"),
                row.get("dim3_mm"), row.get("thickness_mm"), bool(row.get("double")),
            )
            weight = round(kg_per_m * length, 2) if kg_per_m else None
            items.append({
                "name_th": name, "profile": row.get("profile"), "double": bool(row.get("double")),
                "dim1_mm": row.get("dim1_mm"), "dim2_mm": row.get("dim2_mm"),
                "dim3_mm": row.get("dim3_mm"), "thickness_mm": row.get("thickness_mm"),
                "total_length_m": length, "weight_kg_net": weight,
                "confidence": row.get("confidence", "estimated"),
            })
            total_length_structural += length
            if weight:
                total_weight_net += weight
        else:
            non_structural.append({"name_th": name, "total_length_m": length})

    if not items:
        return {"status": "vision_parse_failed",
                "notes": [f"อ่านแปลนโครงหลังคาได้ (หน้า {pno + 1}) แต่ไม่พบเหล็กโครงสร้างที่มีสเปคหน้าตัดเลย"],
                "items": [], "non_structural_rows": non_structural}

    return {
        "status": "computed_from_framing_plan",
        "drawing_page": pno + 1,
        "drawing_no": code,
        "items": items,
        "non_structural_rows": non_structural,
        "total_length_structural_m": round(total_length_structural, 2),
        "total_weight_kg_net": round(total_weight_net, 2),
        "total_weight_kg_with_waste": round(total_weight_net * (1 + ROOF_STEEL_CUTTING_WASTE), 2),
        "notes": [
            "ไม่มีตาราง 'ถอดปริมาณ' สรุปจากผู้ออกแบบ -- ให้ AI vision อ่านเรขาคณิต+ตารางสเปคจากแปลนโครง"
            "หลังคาโดยตรงแทน ความแม่นยำต่ำกว่าทางตารางสรุป โดยเฉพาะรายการที่ confidence=\"estimated\" "
            f"({estimated_count}/{len(items)} รายการ) ซึ่งประมาณจากระยะห่าง@ ไม่ได้นับทีละเส้นจริง",
            "น้ำหนักคำนวณจากสูตรฟิสิกส์ (พื้นที่หน้าตัด x ความหนาแน่นเหล็ก 7850 กก./ลบ.ม.)",
        ],
    }


def extract_roof_takeoff(pdf_path):
    """หาแผ่นที่มีตาราง "ถอดปริมาณ...หลังคา" **จากเนื้อหาหัวตารางเอง** (`_find_table_crop_region`
    ค้นด้วย `TABLE_TITLE_KEYWORDS` อยู่แล้ว) ไล่ทุกหน้าในเอกสาร -- ไม่ใช้เลขแผ่น (`S-07`/`S-08` เดิม)
    เป็นตัวกรองหน้าอีกต่อไป เพราะเลขแผ่นเป็นธรรมเนียมเฉพาะสำนักงานออกแบบแต่ละที่ ไม่สื่อความหมายเดียวกัน
    ข้ามโปรเจกต์ (ยืนยันแล้วกับหมวดอื่นในไฟล์นี้ -- ดู grid_utils.py)"""
    doc = fitz.open(pdf_path)

    for pno in range(len(doc)):
        page = doc[pno]
        spans = extract_fixed_spans(page)
        clip = _find_table_crop_region(page, spans)
        if clip is None:
            continue

        try:
            import ai_vision_fallback
        except ImportError as e:
            return {"status": "blocked_no_ai_vision", "notes": [f"import ai_vision_fallback ไม่สำเร็จ: {e}"],
                    "items": [], "non_structural_rows": []}

        try:
            pix = page.get_pixmap(dpi=300, clip=clip)
            result = ai_vision_fallback.call_vision_json(pix.tobytes("png"), ROOF_TABLE_VISION_PROMPT)
        except Exception as e:
            return {"status": "vision_call_failed", "notes": [f"AI vision เรียกไม่สำเร็จ (หน้า {pno + 1}): {e}"],
                    "items": [], "non_structural_rows": []}

        if result.get("_parse_error") or not result.get("rows"):
            continue

        items, non_structural = [], []
        total_length_structural = 0.0
        total_weight_net = 0.0
        for row in result["rows"]:
            name = row.get("name_th") or "?"
            length = row.get("total_length_m")
            if row.get("profile") in ("C", "box") and length:
                kg_per_m = steel_profile_weight_kg_per_m(
                    row.get("profile"), row.get("dim1_mm"), row.get("dim2_mm"),
                    row.get("dim3_mm"), row.get("thickness_mm"), bool(row.get("double")),
                )
                weight = round(kg_per_m * length, 2) if kg_per_m else None
                items.append({
                    "name_th": name, "profile": row.get("profile"), "double": bool(row.get("double")),
                    "dim1_mm": row.get("dim1_mm"), "dim2_mm": row.get("dim2_mm"),
                    "dim3_mm": row.get("dim3_mm"), "thickness_mm": row.get("thickness_mm"),
                    "total_length_m": length, "weight_kg_net": weight,
                })
                total_length_structural += length
                if weight:
                    total_weight_net += weight
            else:
                non_structural.append({"name_th": name, "total_length_m": length})

        notes = [
            "น้ำหนักคำนวณจากสูตรฟิสิกส์ (พื้นที่หน้าตัด x ความหนาแน่นเหล็ก 7850 กก./ลบ.ม.) ไม่ใช่ตาราง "
            "kg/m จากแค็ตตาล็อก -- คลาดเคลื่อนเล็กน้อยได้จากรัศมีมุมพับจริงของแต่ละโรงงาน",
            "รายการที่ไม่มีสเปคหน้าตัดเหล็ก (เช่นวัสดุครอบสัน/ครอบหลังคา) แยกไว้ใน non_structural_rows "
            "ไม่รวมในน้ำหนักเหล็กโครงสร้าง",
        ]
        grand_total = result.get("grand_total_length_m")
        if grand_total and abs(grand_total - (total_length_structural + sum(
                r["total_length_m"] or 0 for r in non_structural))) > 1.0:
            notes.append(f"ความยาวรวมที่อ่านได้ไม่ตรงกับ Grand total ในตาราง ({grand_total}ม.) -- ควรตรวจสอบ")

        return {
            "status": "computed",
            "drawing_page": pno + 1,
            "drawing_no": _read_sheet_number(page, spans),
            "items": items,
            "non_structural_rows": non_structural,
            "total_length_structural_m": round(total_length_structural, 2),
            "total_weight_kg_net": round(total_weight_net, 2),
            "total_weight_kg_with_waste": round(total_weight_net * (1 + ROOF_STEEL_CUTTING_WASTE), 2),
            "grand_total_length_m_per_designer": grand_total,
            "notes": notes,
        }

    # ไม่พบตารางสรุปของผู้ออกแบบเลยทั้งเอกสาร -- fallback ไปให้ AI vision อ่านเรขาคณิต+ตารางสเปคจาก
    # แปลนโครงหลังคาโดยตรงแทน (ตรงกับที่เจ้าของโปรเจกต์ยืนยัน 2569-09-02: "ทำไมต้องหาตารางถอดปริมาณ...
    # เราจะให้ไพน้อยอ่านแบบและถอดอยู่แล้ว" -- ไม่ใช้ "ไม่มีตาราง" เป็นจุดจบอีกต่อไป)
    return _extract_roof_from_framing_plan(doc)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf_path")
    args = ap.parse_args()
    result = extract_roof_takeoff(args.pdf_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
