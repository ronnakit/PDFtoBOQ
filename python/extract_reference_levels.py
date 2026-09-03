"""PDFtoBOQ -- อ่านระดับอ้างอิง (Reference Levels) ของโครงการ

หาว่าจุดอ้างอิง +/-0.00 ของทั้งไฟล์หมายถึงระดับอะไรจริง (เช่น "ระดับปัจจุบัน"/"ระดับดินเดิม")
แล้วดึงค่า EL= ที่กำกับสมาชิกโครงสร้างแต่ละจุด (คาน/โครงหลังคา ฯลฯ) จากแปลนโดยตรง -- ไม่ใช่จาก
ตารางสเปคกลาง เพราะค่าระดับต่างกันได้ทุกจุดที่วางจริง (เจ้าของโปรเจกต์ยืนยัน 2569-09-03: "เลขชุด
เหล่านี้มันวางชิดกับคาน เพื่อบอกว่าคานอะไร ความสูงเท่าไร")

**รองรับเฉพาะรูปแบบ (case) ที่รู้จักแล้วเท่านั้น** -- ถ้าไฟล์ไม่ตรงกับ case ไหนเลย ต้องคืนสถานะ
"case_not_recognized" ห้ามเดา/ประมาณ (ตามกฎที่เจ้าของโปรเจกต์ยืนยันไว้ 2569-09-03: "ถอดปริมาณ
ไม่ได้จะไม่มี ต้องมีทางออก แต่ต้องไม่มั่วหรือเดา") -- เมื่อเจอไฟล์ที่ case เดิมจับไม่ได้ ให้เก็บไฟล์
นั้นไว้เป็นตัวอย่างแล้วเพิ่ม case ใหม่ต่อท้าย KNOWN_CASES ทีละ case จริง ไม่ใช่พยายามเขียน
regex เดียวครอบจักรวาลทุกสำนักงานตั้งแต่แรก

Case ที่รู้จักแล้ว:
- CASE "el_inline_a8lanna" (ยืนยันจาก project/แบบบ้านสันคือ, สนง. A8 Lanna Engineering,
  2569-09-03): ป้ายระดับเขียนติดกับรหัสสมาชิกโดยตรงบนแปลนเป็น "<รหัส>(EL=x.xx)" เช่น
  "B1(EL=0.50)" (บนแปลนคานพื้น), "RB1(EL=5.50)" (บนแปลนโครงหลังคา) -- จุดอ้างอิง +/-0.00 ของ
  ทั้งไฟล์นิยามไว้ในคำอธิบายสัญลักษณ์แบบ ด้วยประโยคที่มีคำว่า "ระดับอ้างอิง" คู่กับ "+0.00" เสมอ
  ("เส้น Level แสดงระดับความสูงจากระดับอ้างอิง +0.00 - ระดับปัจจุบัน") -- ต้องอ่านผ่าน
  thai_font_fix.extract_fixed_spans() ก่อนเสมอ (ฟอนต์เดียวกับที่เพี้ยนในไฟล์ 116-69)

Usage:
    python extract_reference_levels.py <pdf_path>
"""
import argparse
import json
import re
import sys

import fitz

from thai_font_fix import extract_fixed_spans

CASE_EL_INLINE_A8LANNA = {
    "id": "el_inline_a8lanna",
    # ต้องเจอทั้งสองคำในหน้าเดียวกัน (นับช่องว่างในตัวข้อความจริงเป็นหลัก ไม่ใช่ตัวคั่นที่ใส่เพิ่มตอน
    # join spans -- ดู _joined_page_text) จึงจะถือว่าไฟล์นี้ตรง case นี้
    "signature_keywords": ["ระดับอ้างอิง", "+0.00"],
    # ความหมายของจุดอ้างอิง -- ยืนยันด้วยคนแล้ว (เจ้าของโปรเจกต์ 2569-09-03) ไม่ใช่สิ่งที่พยายาม
    # re-parse จากข้อความสดทุกครั้ง (ข้อความจริงบางจุดเพี้ยนจากบั๊กฟอนต์ที่ยังไม่ปิด ดู
    # project/แบบบ้านสันคือ/foundation_data.md หัวข้อ "ระดับอ้างอิง")
    "datum_meaning": "ระดับปัจจุบัน (ก่อนก่อสร้าง) -- เดียวกับ \"ระดับดินเดิม\" ที่ใช้คำนวณความลึกฐานราก/ความสูงตอม่อ",
    "member_tag_re": re.compile(r"^([A-Za-z]+[0-9]+)\(EL=([\d.]+)\)$"),
}

KNOWN_CASES = [CASE_EL_INLINE_A8LANNA]


def _joined_page_text(spans):
    """ต่อข้อความทุก span ในหน้าตรงๆ ไม่ใส่ตัวคั่นเพิ่ม -- คำเดียวกันที่ถูกตัดเป็นหลาย span (เช่น
    "ระดับอ" + "้างอิง ") ต้องต่อกันสนิทถึงจะยัง match keyword เป็นคำเดียวได้ (ช่องว่างที่ต้องการ
    จริงๆ อยู่ในเนื้อ span เองอยู่แล้วจากต้นฉบับ)"""
    return "".join(s["text"] for s in spans)


def detect_case(doc):
    """ไล่ทุกหน้า ทุก case ที่รู้จัก หา signature ที่ตรง -- คืน (case_dict, page_index) ของที่เจอ
    ก่อนสุด หรือ (None, None) ถ้าไม่ตรง case ไหนเลยในทั้งไฟล์"""
    for pno in range(len(doc)):
        joined = _joined_page_text(extract_fixed_spans(doc[pno]))
        for case in KNOWN_CASES:
            if all(kw in joined for kw in case["signature_keywords"]):
                return case, pno
    return None, None


def find_reference_levels(pdf_path):
    doc = fitz.open(pdf_path)
    case, datum_page = detect_case(doc)
    if case is None:
        return {
            "status": "case_not_recognized",
            "notes": [f"ไม่พบรูปแบบระดับอ้างอิงที่รู้จัก (ตรวจแล้ว {len(KNOWN_CASES)} case: "
                      f"{[c['id'] for c in KNOWN_CASES]}) -- เก็บไฟล์นี้ไว้เป็นตัวอย่าง case ใหม่ "
                      f"ห้ามประมาณค่าระดับเอง"],
        }

    members = []
    for pno in range(len(doc)):
        for s in extract_fixed_spans(doc[pno]):
            m = case["member_tag_re"].match(s["text"].strip())
            if m:
                members.append({"code": m.group(1), "el_value": float(m.group(2)), "page": pno + 1})

    return {
        "status": "recognized",
        "case_id": case["id"],
        "datum_meaning": case["datum_meaning"],
        "datum_page": datum_page + 1,
        "members": members,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf_path")
    args = ap.parse_args()
    result = find_reference_levels(args.pdf_path)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
