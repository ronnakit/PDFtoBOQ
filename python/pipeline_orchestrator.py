"""PDFtoBOQ -- Pipeline orchestrator: เรียกทุกหมวดที่มี แล้วประกอบเป็นผลลัพธ์เดียว (confirm_boq.json)

Phase C (2569-09-02): เพิ่มคาน (โค้ดล้วนสำหรับสเปค + AI vision สำหรับเรขาคณิต, ครอบคลุมเฉพาะคานระหว่าง
จุดเสาที่ยืนยันแล้ว -- status "partial_coverage" เสมอ) -- พื้นยังไม่เชื่อมเข้ามา

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
import re
import sys
from datetime import datetime

import fitz

from extract_beam_boq import extract_beam_takeoff
from extract_footing_boq import extract_footing_takeoff
from extract_pier_column_boq import extract_pier_column_takeoff
from extract_roof_boq import extract_roof_takeoff

STRUCTURAL_CONCRETE_WASTE = 0.03
REBAR_WEIGHT_WASTE = 0.05
DB12_KG_PER_M = 0.888
RB6_KG_PER_M = 0.222
FOOTING_REBAR_COVER_M = 0.05
STIRRUP_HOOK_ALLOWANCE_M = 0.10
STIRRUP_SPACING_DEFAULT_M = 0.15

FOOTING_REBAR_RE = re.compile(r"^(\d+)\+(\d+)-DB\s*(\d+)", re.IGNORECASE)


def compute_footing_summary(footing_result):
    """เติมปริมาตรคอนกรีต+น้ำหนักเหล็กต่อรายการ -- คำนวณคอนกรีตได้เฉพาะรายการที่มีความหนา (T) แล้ว
    เท่านั้น (เติมจาก AI vision fallback ใน extract_footing_boq.py ถ้าตารางสเปคไม่ถูก flatten ก็ไม่ต้อง
    พึ่ง AI เลย) -- เหล็กเสริมพาร์สจากรูปแบบ "N+N-DBxx mm." (จำนวนเหล็กแต่ละทิศ x ขนาด) ความยาวเหล็กต่อ
    เส้นประมาณจากด้านของฐานรากลบ cover 2 ด้าน (ค่าประมาณ safe-side เพราะยังไม่รู้ทิศทางวางเหล็กจริงจาก
    แบบ, ต่างจากที่คำนวณตอม่อ-เสาที่รู้ทิศทางชัดเจนกว่า)."""
    total_concrete = 0.0
    total_rebar_kg = 0.0
    concrete_computed = False
    rebar_computed = False

    for item in footing_result.get("items", []):
        if item.get("size_m") and item.get("thickness_m"):
            vol_each = item["size_m"][0] * item["size_m"][1] * item["thickness_m"]
            item["concrete_m3_each"] = round(vol_each, 4)
            item["concrete_m3_total"] = round(vol_each * item["count"], 4)
            total_concrete += item["concrete_m3_total"]
            concrete_computed = True

        m = FOOTING_REBAR_RE.match(item.get("rebar") or "")
        if m and item.get("size_m"):
            n1, n2, db_size = int(m.group(1)), int(m.group(2)), m.group(3)
            bar_len = max(item["size_m"][0], item["size_m"][1]) - 2 * FOOTING_REBAR_COVER_M
            kg_per_m = DB12_KG_PER_M if db_size == "12" else DB12_KG_PER_M  # เผื่อไซส์อื่นในอนาคต
            rebar_kg_each = (n1 + n2) * bar_len * kg_per_m
            item["rebar_kg_each"] = round(rebar_kg_each, 2)
            item["rebar_kg_total"] = round(rebar_kg_each * item["count"], 2)
            total_rebar_kg += item["rebar_kg_total"]
            rebar_computed = True

    computed_any = concrete_computed or rebar_computed
    return {
        "concrete_m3_net": round(total_concrete, 3) if concrete_computed else None,
        "concrete_m3_with_waste": round(total_concrete * (1 + STRUCTURAL_CONCRETE_WASTE), 3) if concrete_computed else None,
        "rebar_kg_net": round(total_rebar_kg, 2) if rebar_computed else None,
        "rebar_kg_with_waste": round(total_rebar_kg * (1 + REBAR_WEIGHT_WASTE), 2) if rebar_computed else None,
        "status": "computed" if (concrete_computed and rebar_computed) else ("partial" if computed_any else "blocked_needs_thickness_spec"),
        "note": "ความยาวเหล็กประมาณจากด้านฐานรากลบ cover -- ยังไม่รู้ทิศทางวางจริงจากแบบ (safe-side estimate)" if rebar_computed else None,
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


def compute_roof_summary(roof_result):
    """แปลงผลลัพธ์จาก extract_roof_boq.py (คำนวณน้ำหนักในตัวอยู่แล้วเพราะเป็นหมวดที่ใช้ AI vision เป็น
    วิธีหลัก ไม่ใช่ fallback) ให้เข้ารูปแบบ summary เดียวกับหมวดอื่น (concrete_m3.../steel_kg...)."""
    if roof_result.get("status") != "computed":
        return {"status": roof_result.get("status", "not_implemented")}
    return {
        "status": "computed",
        "concrete_m3_net": None,
        "concrete_m3_with_waste": None,
        "steel_kg_net": roof_result.get("total_weight_kg_net"),
        "steel_kg_with_waste": roof_result.get("total_weight_kg_with_waste"),
        "note": f"เหล็กโครงสร้างหลังคารวม {roof_result.get('total_length_structural_m')}ม. "
                f"(ไม่รวมวัสดุครอบสัน/ครอบหลังคา {sum(r.get('total_length_m') or 0 for r in roof_result.get('non_structural_rows', [])):.2f}ม. ที่ไม่มีสเปคหน้าตัดเหล็ก)",
    }


def compute_beam_summary(beam_result):
    """แปลงผลลัพธ์จาก extract_beam_boq.py (คำนวณคอนกรีต/เหล็กในตัวอยู่แล้วต่อ item) รวมเป็น summary
    เดียว -- สถานะ "partial" เสมอเพราะครอบคลุมเฉพาะคานระหว่างจุดเสาที่ยืนยันแล้ว (ดู notes ของ
    extract_beam_takeoff สำหรับรายละเอียดข้อจำกัด)."""
    if beam_result.get("status") != "partial_coverage" or not beam_result.get("items"):
        return {"status": beam_result.get("status", "not_implemented")}
    total_concrete, total_main_kg, total_stirrup_kg = 0.0, 0.0, 0.0
    for item in beam_result["items"]:
        total_concrete += item.get("concrete_m3_with_waste") or 0
        total_main_kg += item.get("main_bar_kg_with_waste") or 0
        total_stirrup_kg += item.get("stirrup_kg_with_waste") or 0
    return {
        "status": "partial",
        "concrete_m3_net": None,
        "concrete_m3_with_waste": round(total_concrete, 3),
        "main_bar_kg_with_waste": round(total_main_kg, 2),
        "stirrup_kg_with_waste": round(total_stirrup_kg, 2),
        "note": f"ครอบคลุมเฉพาะคานระหว่างจุดเสาที่ยืนยันแล้ว ({beam_result.get('matched_segment_count')}/"
                f"{beam_result.get('candidate_segment_count')} ช่วง) -- คานช่วงสั้นนอกจุดเสาหลักยังไม่นับ "
                f"ตัวเลขจึงต่ำกว่าความเป็นจริงได้",
    }


def run_pipeline(pdf_path, project_dir=None):
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    doc.close()

    footing = extract_footing_takeoff(pdf_path)
    footing_summary = compute_footing_summary(footing)

    pier_column = extract_pier_column_takeoff(pdf_path)
    pier_column_summary = compute_pier_column_summary(pier_column)

    roof = extract_roof_takeoff(pdf_path)
    roof_summary = compute_roof_summary(roof)

    beam = extract_beam_takeoff(pdf_path)
    beam_summary = compute_beam_summary(beam)

    result = {
        "pdftoboq_version": "phase-c-2569-09-02",
        "generated_at": datetime.now().isoformat(),
        "pdf_path": pdf_path,
        "page_count": page_count,
        "categories": {
            "footing": {**footing, "summary": footing_summary},
            "pier_column": {**pier_column, "summary": pier_column_summary},
            "beam": {**beam, "summary": beam_summary},
            "floor": {
                "status": "not_implemented",
                "notes": [
                    "ลองแล้ว (2569-09-02): จับคู่ป้าย S1/PS บนแผ่นคาน-พื้น (S-06) เข้ากับ 'ช่องกริดโครงสร้าง' "
                    "ที่ใกล้ที่สุด แล้วคำนวณพื้นที่จากขนาดช่องกริด -- ผลออกมาคลาดเคลื่อนมาก (S1 ได้ 19.25 "
                    "ตร.ม. เทียบกับพื้นที่จริงที่วัดจากขอบเขตห้องบนแบบสถาปัตย์ 14.34 ตร.ม. คลาดเคลื่อน "
                    "+34%) เพราะห้องน้ำ/ห้องเล็กไม่ได้มีขอบเขตตรงกับช่องกริดโครงสร้าง (เป็นผนังภายในที่ไม่ "
                    "ปรากฏในแบบคาน) -- ไม่ปล่อยตัวเลขที่รู้อยู่แล้วว่าคลาดเคลื่อนสูง ต้องอ่านขอบเขตห้องจริง "
                    "จากแบบสถาปัตย์ (A-05 หรือเทียบเท่า) ด้วย AI vision ก่อน ยังไม่ได้ทำ (รอ Phase C ต่อ)",
                ],
            },
            "roof": {**roof, "summary": roof_summary},
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
