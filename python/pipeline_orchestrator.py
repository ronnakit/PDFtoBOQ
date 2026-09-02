"""PDFtoBOQ -- Pipeline orchestrator: เรียกทุกหมวดที่มี แล้วประกอบเป็นผลลัพธ์เดียว (confirm_boq.json)

Phase A (2569-09-02): ฐานราก + ตอม่อ-เสา เท่านั้น (โค้ดล้วน 100%, ไม่มีต้นทุน AI) -- คาน/พื้น/
หลังคา ยังไม่เชื่อมเข้ามา (Phase C ต่อไป) เพื่อไม่ให้ /api/takeoff ต้องรอทุกหมวดเสร็จพร้อมกัน

คำนวณคอนกรีต/เหล็กด้วยสูตร/ค่าคงที่มาตรฐาน (ค่าฟิสิกส์วัสดุ ใช้ร่วมได้ทุกโปรเจกต์ -- ตรงกับกฎที่
เอกสารพิมพ์เขียวยึดไว้: ห้ามฝังค่าที่ยืนยันเฉพาะโปรเจกต์เป็นค่าคงที่ในสคริปต์ แต่สูตร/ค่าฟิสิกส์วัสดุ
ใส่ในโค้ดได้ปกติ)

Usage:
    python pipeline_orchestrator.py <pdf_path> [--project-dir <dir>]
"""
import argparse
import json
import math
import os
import sys
from datetime import datetime

import fitz

from extract_footing_boq import extract_footing_takeoff
from extract_pier_column_boq import extract_pier_column_takeoff

STRUCTURAL_CONCRETE_WASTE = 0.03
REBAR_WEIGHT_WASTE = 0.05
DB12_KG_PER_M = 0.888
RB6_KG_PER_M = 0.222
COVER_IN_SOIL_M = 0.05
STIRRUP_HOOK_ALLOWANCE_M = 0.10
STIRRUP_SPACING_DEFAULT_M = 0.15


def compute_footing_summary(footing_result):
    """เติมปริมาตรคอนกรีตต่อรายการ -- คำนวณได้เฉพาะรายการที่มีความหนา (T) แล้วเท่านั้น (ส่วนใหญ่
    ยังไม่มีใน Phase A เพราะตารางสเปคมักถูก flatten -- ดู notes ของแต่ละรายการ)."""
    total_concrete = 0.0
    computed_any = False
    for item in footing_result.get("items", []):
        if item.get("size_m") and item.get("thickness_m"):
            vol_each = item["size_m"][0] * item["size_m"][1] * item["thickness_m"]
            item["concrete_m3_each"] = round(vol_each, 4)
            item["concrete_m3_total"] = round(vol_each * item["count"], 4)
            total_concrete += item["concrete_m3_total"]
            computed_any = True
    return {
        "concrete_m3_net": round(total_concrete, 3) if computed_any else None,
        "concrete_m3_with_waste": round(total_concrete * (1 + STRUCTURAL_CONCRETE_WASTE), 3) if computed_any else None,
        "status": "computed" if computed_any else "blocked_needs_thickness_spec",
    }


def compute_pier_column_summary(pc_result):
    """คำนวณคอนกรีต+เหล็กตอม่อ-เสา จากความสูง(ประมาณ/ยืนยัน)+หน้าตัด+สเปคเหล็กที่มี -- ใช้สูตร
    เดียวกับที่ยืนยันแล้วกับ newhouse/116-69 (เหล็กยืนเป็นเส้นเดียวต่อเนื่อง, ปลอกนับจาก spacing)."""
    total_concrete = 0.0
    total_main_bar_m = 0.0
    total_stirrup_count = 0
    total_stirrup_m = 0.0
    computed_any = False

    for item in pc_result.get("items", []):
        cross = item.get("cross_section_m")
        ph = item.get("pier_height_m")
        ch = item.get("column_height_m")
        if not (cross and ph and ch):
            continue
        computed_any = True
        w, h = cross
        length_total = ph + ch
        vol_each = w * h * length_total
        total_concrete += vol_each * item["count"]

        n_bars = 4
        if item.get("main_rebar"):
            try:
                n_bars = int(item["main_rebar"].split("-")[0])
            except (ValueError, IndexError):
                pass
        bar_len_each = length_total  # ไม่รวม hook เข้าฐานราก (ต้องรู้ขนาดฐานรากต่อจุด -- Phase B)
        total_main_bar_m += n_bars * bar_len_each * item["count"]

        spacing = STIRRUP_SPACING_DEFAULT_M
        if item.get("stirrup"):
            try:
                spacing = float(item["stirrup"].split("@")[1].rstrip("m"))
            except (ValueError, IndexError):
                pass
        tie_perimeter = 2 * (w + h) + STIRRUP_HOOK_ALLOWANCE_M
        n_ties = (math.ceil(ph / spacing) + 1) + (math.ceil(ch / spacing) + 1)
        total_stirrup_count += n_ties * item["count"]
        total_stirrup_m += n_ties * tie_perimeter * item["count"]

    if not computed_any:
        return {"status": "blocked_missing_data"}

    main_bar_kg = total_main_bar_m * DB12_KG_PER_M
    stirrup_kg = total_stirrup_m * RB6_KG_PER_M
    return {
        "status": "computed",
        "concrete_m3_net": round(total_concrete, 3),
        "concrete_m3_with_waste": round(total_concrete * (1 + STRUCTURAL_CONCRETE_WASTE), 3),
        "main_bar_kg_net": round(main_bar_kg, 2),
        "main_bar_kg_with_waste": round(main_bar_kg * (1 + REBAR_WEIGHT_WASTE), 2),
        "stirrup_count": total_stirrup_count,
        "stirrup_kg_net": round(stirrup_kg, 2),
        "stirrup_kg_with_waste": round(stirrup_kg * (1 + REBAR_WEIGHT_WASTE), 2),
        "note": "เหล็กยืนยังไม่รวมความยาวฮุคเข้าฐานราก (ต้องรู้ขนาดฐานรากต่อจุด, รอ Phase B)",
    }


def run_pipeline(pdf_path, project_dir=None):
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    doc.close()

    footing = extract_footing_takeoff(pdf_path)
    footing_summary = compute_footing_summary(footing)

    pier_column = extract_pier_column_takeoff(pdf_path)
    pier_column_summary = compute_pier_column_summary(pier_column)

    result = {
        "pdftoboq_version": "phase-a-2569-09-02",
        "generated_at": datetime.now().isoformat(),
        "pdf_path": pdf_path,
        "page_count": page_count,
        "categories": {
            "footing": {**footing, "summary": footing_summary},
            "pier_column": {**pier_column, "summary": pier_column_summary},
            "beam": {"status": "not_implemented", "notes": ["รอ Phase C"]},
            "floor": {"status": "not_implemented", "notes": ["รอ Phase C"]},
            "roof": {"status": "not_implemented", "notes": ["รอ Phase B (ตารางผู้ออกแบบมักเป็นภาพ)"]},
        },
    }

    if project_dir:
        md_dir = os.path.join(project_dir, "markdown")
        os.makedirs(md_dir, exist_ok=True)
        out_path = os.path.join(md_dir, "confirm_boq.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        result["_written_to"] = out_path

    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf_path")
    ap.add_argument("--project-dir", default=None)
    args = ap.parse_args()
    result = run_pipeline(args.pdf_path, project_dir=args.project_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
