"""PDFtoBOQ -- Stage 0: สารบัญแบบ + สถานะความเป็นไปได้เบื้องต้น (feasibility scan)

ก่อนถอดแบบจริง (Stage 1) ต้อง:
1. อ่านสารบัญแบบของไฟล์นี้ (grid_utils.list_all_sheets) ให้ครบทุกหมวด **รวมพื้นและหลังคาด้วย** ไม่ใช่แค่
   ฐานราก/ตอม่อ-เสา/คาน -- สารบัญเป็นข้อมูลเฉพาะไฟล์นั้น ต้องอ่านใหม่ทุกครั้ง ห้าม hardcode รหัสแผ่น
2. ไล่**ทั้งเอกสาร** ด้วยตัวหาแผ่นของแต่ละหมวด (ที่มีอยู่แล้วในแต่ละ extract_*.py) เพื่อบอกว่าหมวดไหน
   "น่าจะถอดปริมาณได้" กับหมวดไหน "ยังหาแผ่น/ตารางที่จำเป็นไม่เจอเลย" -- ใช้แค่โค้ดล้วน (page-finder ของ
   แต่ละหมวดเอง) ไม่เรียก AI vision เลยในขั้นตอนนี้ เพราะเป็นแค่การเช็คความเป็นไปได้เบื้องต้น ไม่ใช่การ
   ถอดปริมาณจริง (ประหยัดต้นทุน/เวลา)
3. เขียนผลลัพธ์ทั้งสองข้อลง foundation_data.md ของโปรเจกต์นั้นเสมอ (อัปเดตถ้ามีไฟล์อยู่แล้ว)

Usage:
    python stage0_feasibility.py <pdf_path> [--project-dir <dir>]
"""
import argparse
import os
import re

import fitz

import extract_beam_boq
import extract_floor_boq
import extract_footing_boq
import extract_roof_boq
import grid_utils
from thai_font_fix import extract_fixed_spans

CATEGORY_LABELS = {
    "footing": "ฐานราก",
    "pier_column": "ตอม่อ-เสา",
    "beam": "คาน",
    "floor": "พื้น",
    "roof": "หลังคา",
}


def assess_structural_feasibility(pdf_path):
    """เช็คว่าแต่ละหมวดโครงสร้างน่าจะถอดปริมาณได้ไหม โดยใช้แค่ตัวหาแผ่น/ตารางของแต่ละหมวดเอง (โค้ดล้วน
    ไม่เรียก AI vision) ไล่ทั้งเอกสาร -- คืน dict {category: {feasible, page, note}}"""
    doc = fitz.open(pdf_path)
    result = {}

    footing_pno = grid_utils.find_page_by_content(doc, extract_footing_boq.FOOTING_PLAN_TITLE_KEYWORDS, require_grid=True)
    if footing_pno is None:
        footing_pno = grid_utils.find_page_with_most_markers(doc, extract_footing_boq.PIER_OR_COMBINED_RE, min_count=3)
    result["footing"] = {"feasible": footing_pno is not None,
                          "page": (footing_pno + 1) if footing_pno is not None else None}
    result["pier_column"] = {"feasible": footing_pno is not None,
                              "page": (footing_pno + 1) if footing_pno is not None else None,
                              "note": "ใช้ตำแหน่งแผ่นเดียวกับฐานราก (ป้ายเสา/ฐานรากมักอยู่แผ่นเดียวกัน)"}

    beam_schedule = extract_beam_boq.parse_beam_schedule(doc)
    result["beam"] = {"feasible": beam_schedule is not None,
                       "page": beam_schedule["page"] if beam_schedule else None,
                       "note": f"พบรหัสคาน {sorted(beam_schedule['schedule'].keys())}" if beam_schedule else None}

    floor_pno, floor_code = extract_floor_boq.find_room_plan_page(doc)
    result["floor"] = {"feasible": floor_pno is not None,
                        "page": (floor_pno + 1) if floor_pno is not None else None,
                        "note": f"แผ่น {floor_code}" if floor_code else None}

    roof_pno = None
    for pno in range(len(doc)):
        page = doc[pno]
        spans = extract_fixed_spans(page)
        if extract_roof_boq._find_table_crop_region(page, spans) is not None:
            roof_pno = pno
            break
    result["roof"] = {"feasible": roof_pno is not None,
                       "page": (roof_pno + 1) if roof_pno is not None else None,
                       "note": "พบหัวตาราง 'ถอดปริมาณ...หลังคา'" if roof_pno is not None else
                               "ไม่พบตาราง 'ถอดปริมาณ...หลังคา' ในหน้าไหนเลย -- อาจไม่มีตารางนี้ในโปรเจกต์นี้"}
    return result


def floor_roof_standards_notes(feasibility):
    """สร้างข้อสังเกตธรรมเนียม/ข้อจำกัดของหมวดพื้นและหลังคาที่เจอจริงจากการสแกน -- เขียนต่อท้ายส่วน
    "มาตรฐานและข้อกำหนด" ที่มีอยู่แล้ว (ไม่ทับของเดิม)"""
    notes = []
    floor = feasibility.get("floor", {})
    if floor.get("feasible"):
        notes.append(
            f"พื้น: พบแปลนพื้นสถาปัตย์ที่{floor.get('note', '')} (หน้า {floor.get('page')}) -- "
            "ป้ายชื่อห้องบนแปลนถูก flatten เป็น vector/curve อ่านด้วย text ไม่ได้เลย ต้องใช้ AI vision "
            "อ่านชื่อห้อง+ขนาดจากภาพโดยตรง (ยืนยันแล้วทั้ง 116-69 และไฟล์นี้)")
    else:
        notes.append("พื้น: ไม่พบแปลนพื้นสถาปัตย์ในสารบัญแบบ/เอกสารนี้เลย")

    roof = feasibility.get("roof", {})
    if roof.get("feasible"):
        notes.append(f"หลังคา: พบตาราง 'ถอดปริมาณงานโครงสร้างคานเหล็กหลังคา' ที่หน้า {roof.get('page')} "
                      "(ผู้ออกแบบสรุปความยาวรวมไว้เอง น่าเชื่อถือกว่าให้โค้ดนับเส้นเอง)")
    else:
        notes.append("หลังคา: ไม่พบตาราง 'ถอดปริมาณงานโครงสร้างคานเหล็กหลังคา' ในหน้าไหนของเอกสารเลย "
                      "(ไล่ครบทุกหน้าแล้ว) -- ผู้ออกแบบรายนี้อาจไม่สรุปตารางนี้ให้ ต้องนับเส้นจากแบบเอง "
                      "(ยังไม่รองรับ)")
    return notes


def _md_table_sheets(sheets):
    lines = ["| รหัสแผ่น | คำอธิบาย |", "|---|---|"]
    for code, desc in sheets:
        lines.append(f"| {code} | {desc or '(อ่านคำอธิบายไม่ได้)'} |")
    return "\n".join(lines)


def _md_table_feasibility(feasibility):
    lines = ["| หมวด | ถอดปริมาณได้ไหม (เบื้องต้น, ยังไม่ได้ลองจริง) | แผ่น | หมายเหตุ |", "|---|---|---|---|"]
    for key, label in CATEGORY_LABELS.items():
        f = feasibility.get(key, {})
        mark = "✅ น่าจะได้" if f.get("feasible") else "⛔ ยังหาแผ่น/ตารางที่จำเป็นไม่เจอ"
        lines.append(f"| {label} | {mark} | {f.get('page') or '-'} | {f.get('note') or '-'} |")
    return "\n".join(lines)


def write_stage0_sections(foundation_md_path, sheets, feasibility):
    """เขียน/อัปเดตส่วน 'สารบัญแบบ (ทุกหมวด)' และ 'สถานะความเป็นไปได้เบื้องต้น (Stage 0)' ลง
    foundation_data.md -- ถ้าไฟล์ยังไม่มีให้สร้างใหม่แบบย่อ (Stage 0 ตัวหลัก คือ extract_foundation_data.py
    ยังต้องรันแยกสำหรับข้อมูลปก/ผังบริเวณ/สัญลักษณ์ -- ไฟล์นี้เติมเฉพาะสารบัญ+feasibility)"""
    header = "## สารบัญแบบ (ทุกหมวด, อ่านจากสารบัญของไฟล์นี้เอง)"
    fea_header = "## สถานะความเป็นไปได้เบื้องต้น (Stage 0 -- ยังไม่ได้ถอดจริง แค่เช็คว่าน่าจะทำได้ไหม)"
    sheets_block = f"{header}\n\n{_md_table_sheets(sheets)}\n"
    fea_block = f"{fea_header}\n\n{_md_table_feasibility(feasibility)}\n"

    if os.path.exists(foundation_md_path):
        with open(foundation_md_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "# foundation_data.md -- ผล Stage 0\n"

    def replace_or_append(content, header_text, block):
        pattern = re.compile(rf"{re.escape(header_text)}.*?(?=\n## |\Z)", re.DOTALL)
        if pattern.search(content):
            return pattern.sub(block.rstrip() + "\n", content)
        return content.rstrip() + "\n\n" + block

    content = replace_or_append(content, header, sheets_block)
    content = replace_or_append(content, fea_header, fea_block)

    # เติมข้อสังเกตพื้น/หลังคาต่อท้าย "มาตรฐานและข้อกำหนด" ถ้ามีส่วนนี้อยู่แล้ว (ไม่ทับของเดิม, ไม่เติมซ้ำ
    # ถ้ารันซ้ำแล้วข้อความเดิมยังอยู่) -- ถ้าไม่มีส่วนนี้เลยให้สร้างใหม่
    std_header = "## มาตรฐานและข้อกำหนด"
    new_notes = [n for n in floor_roof_standards_notes(feasibility) if n not in content]
    if new_notes:
        bullet_block = "\n".join(f"- {n}" for n in new_notes)
        pattern = re.compile(rf"({re.escape(std_header)}\n(?:.*\n)*?)(?=\n## |\Z)")
        m = pattern.search(content)
        if m:
            content = content[:m.end()].rstrip("\n") + "\n" + bullet_block + "\n" + content[m.end():]
        else:
            content = content.rstrip() + f"\n\n{std_header}\n\n{bullet_block}\n"

    with open(foundation_md_path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf_path")
    ap.add_argument("--project-dir", default=None, help="โฟลเดอร์โปรเจกต์ (default: โฟลเดอร์เหนือ PDF/)")
    args = ap.parse_args()

    pdf_dir = os.path.dirname(os.path.abspath(args.pdf_path))
    project_dir = args.project_dir or (
        os.path.dirname(pdf_dir) if os.path.basename(pdf_dir).upper() == "PDF" else pdf_dir)
    foundation_md_path = os.path.join(project_dir, "foundation_data.md")

    doc = fitz.open(args.pdf_path)
    sheets = grid_utils.list_all_sheets(doc)
    feasibility = assess_structural_feasibility(args.pdf_path)

    write_stage0_sections(foundation_md_path, sheets, feasibility)
    print(f"เขียนแล้ว: {foundation_md_path}")
    print(_md_table_feasibility(feasibility))


if __name__ == "__main__":
    main()
