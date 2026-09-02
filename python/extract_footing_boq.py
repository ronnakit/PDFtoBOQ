"""PDFtoBOQ -- งานโครงสร้าง: ถอดปริมาณคอนกรีต+เหล็กฐานราก (Footing Takeoff)

เขียนใหม่ทั้งหมด (2569-09-02) แทนเวอร์ชันเดิมที่มี CONFIRMED_GRID_MAPPING/CONFIRMED_FOOTING_SCHEDULE
เป็นค่า hardcode ที่ไม่ตรงกับไฟล์จริง (grid mapping ใช้พิกัดที่ไม่มีอยู่จริงในแบบ 116-69, และค่าที่
ปล่อยออกจากรายงานจริงก็ไม่ตรงกับค่าที่เขียนไว้ในไฟล์เองด้วยซ้ำ) -- ดู LOG.md ของฝั่งเอกสารพิมพ์เขียว
วันที่ 2569-09-02 สำหรับรายละเอียดปัญหาเดิม

วิธีทำงาน (โค้ดล้วน 100%, ไม่มีต้นทุน AI -- พิสูจน์แม่นกับ 116-69 แล้ว 3 ทาง: วัดเอง / ตาราง S-09
จริง / Revit BIM schedule):
1. หาแบบผังฐานราก (drawing_no ที่ระบุ, ค่าเริ่มต้น S-05) อัตโนมัติด้วย grid_utils.find_drawing_page
2. หาเส้นกริด A-E/1-8 + อ่านสเกลจากหัวกระดาษ ด้วย grid_utils
3. จับคู่รหัสตอม่อ (Cx) กับรหัสฐานราก (Fx) ที่ใกล้ที่สุด แปลงเป็นตำแหน่งกริด
4. วัดขนาดจริงของแต่ละฐานรากจากรูปสี่เหลี่ยมทึบสี (vector fill) ที่วาดไว้บนแบบ

**ข้อจำกัดที่ทราบอยู่แล้ว (Phase A, ยังไม่มี AI vision fallback):** ความหนา (T) และเหล็กเสริม
มักอยู่ในตาราง "แบบขยายฐานราก" ที่หลายไฟล์ (ยืนยันแล้วกับ 116-69) ถูก flatten เป็นเส้น vector ล้วน
อ่านด้วย page.get_text() ไม่ได้เลย -- ต้องรอ Phase B (AI vision fallback) ถึงจะอ่านตารางนี้ได้อัตโนมัติ
ตอนนี้จะปล่อยเป็น None พร้อม status="needs_vision" ต่อรายการ ไม่เดาค่าขึ้นมาเอง

Usage:
    python extract_footing_boq.py <pdf_path> [--drawing-no S-05]
"""
import argparse
import json
import re
import sys

import fitz

import grid_utils
from thai_font_fix import extract_fixed_spans

PIER_CODE_RE = re.compile(r"^C[0-9A-Za-z]+$")
FOOTING_CODE_RE = re.compile(r"^F[0-9]+$")

STRUCTURAL_CONCRETE_WASTE = 0.03

FOOTING_SPEC_VISION_PROMPT = """หน้านี้เป็นแบบก่อสร้างวิศวกรรมโครงสร้าง (แบบขยาย) มีหลายตารางในหน้าเดียว
หาตารางที่ชื่อ "แบบขยายฐานราก" (footing detail schedule) ซึ่งมีคอลัมน์หัวตาราง F, T, A x B, N# และแถว
ข้อมูลรหัส F1, F2, F3 (หรือรหัส Fx อื่นๆ ที่มี) อ่านค่าทุกแถวแล้วตอบเป็น JSON ล้วนๆ เท่านั้น ไม่มีข้อความ
อื่นใดๆ ในรูปแบบนี้:
{"items": [{"code": "F1", "thickness_m": 0.25, "size_m": [0.60, 0.60], "rebar": "5+5-DB12mm"}, ...]}
thickness_m และ size_m ต้องเป็นหน่วยเมตร (แปลงจากหน่วยอื่นถ้าตารางไม่ได้เขียนเป็นเมตร) ถ้าหาตารางนี้
ไม่เจอในภาพเลย ให้ตอบ {"items": [], "error": "not_found"}"""


def _apply_vision_footing_specs(pdf_path, items, drawing_no="S-09"):
    """เติม thickness_m/rebar ให้ items ที่ยังเป็น None ด้วย AI vision อ่านตารางสเปคที่ flatten เป็น
    vector (page.get_text() อ่านไม่ได้จริง) -- เรียก AI แค่ครั้งเดียวต่อไฟล์ (เรนเดอร์ทั้งหน้า S-09
    ครั้งเดียว) ไม่ใช่ครั้งละรายการ. คืน (items, notes) -- ถ้าเรียก AI ไม่สำเร็จ (ไม่มี API key, error,
    หรือ parse ไม่ได้) items จะไม่ถูกแก้ไข แค่เติม note อธิบายไว้ ไม่ทำให้ pipeline ทั้งหมดล้ม."""
    notes = []
    try:
        import ai_vision_fallback
    except ImportError as e:
        notes.append(f"ข้าม AI vision fallback: import ไม่สำเร็จ ({e})")
        return items, notes

    doc = fitz.open(pdf_path)
    pno = grid_utils.find_drawing_page_by_title_block(doc, drawing_no)
    if pno is None:
        notes.append(f"ข้าม AI vision fallback: ไม่พบหน้าแบบ {drawing_no}")
        return items, notes

    try:
        img = ai_vision_fallback.render_page_png(doc[pno], dpi=150)
        result = ai_vision_fallback.call_vision_json(img, FOOTING_SPEC_VISION_PROMPT)
    except Exception as e:
        notes.append(f"AI vision fallback ล้มเหลว: {e}")
        return items, notes

    if result.get("_parse_error") or result.get("error") or not result.get("items"):
        notes.append(f"AI vision อ่านตารางสเปคฐานรากไม่สำเร็จ (หน้า {pno + 1}): {result}")
        return items, notes

    by_code = {row["code"]: row for row in result["items"] if row.get("code")}
    filled = []
    for item in items:
        spec = by_code.get(item["code"])
        if spec and item["thickness_m"] is None:
            item["thickness_m"] = spec.get("thickness_m")
            item["rebar"] = spec.get("rebar")
            item["status"] = "confirmed_via_ai_vision"
            filled.append(item["code"])
    if filled:
        notes.append(f"เติมความหนา+เหล็กเสริมจาก AI vision อ่านหน้า {pno + 1} ({drawing_no}): {', '.join(filled)}")
    return items, notes


def extract_pier_footing_pairs(spans):
    piers, footings = [], []
    for s in spans:
        text = s["text"].strip()
        x, y = grid_utils.center(s["bbox"])
        if PIER_CODE_RE.match(text):
            piers.append((text, x, y))
        elif FOOTING_CODE_RE.match(text):
            footings.append((text, x, y))

    pairs = []
    used = set()
    for pier_text, px, py in piers:
        best_idx, best_dist = None, None
        for idx, (f_text, fx, fy) in enumerate(footings):
            if idx in used:
                continue
            dist = (fx - px) ** 2 + (fy - py) ** 2
            if best_dist is None or dist < best_dist:
                best_idx, best_dist = idx, dist
        footing_text = None
        if best_idx is not None:
            used.add(best_idx)
            footing_text = footings[best_idx][0]
        pairs.append({"pier_code": pier_text, "footing_code": footing_text, "x": px, "y": py})
    return pairs


def extract_footing_takeoff(pdf_path, drawing_no="S-05", page_index=None, spec_drawing_no="S-09",
                             use_vision_fallback=True):
    doc = fitz.open(pdf_path)
    if page_index is None:
        pno = grid_utils.find_drawing_page(doc, drawing_no, marker_re=PIER_CODE_RE)
        if pno is None:
            return {
                "status": "not_found",
                "notes": [f"ไม่พบหน้าแบบ {drawing_no} ที่มีป้ายรหัสตอม่ออยู่จริง"],
                "items": [], "positions": [], "totals": {},
            }
    else:
        pno = page_index - 1

    page = doc[pno]
    spans = extract_fixed_spans(page)
    columns, rowlabels = grid_utils.extract_grid(spans)
    if not columns or not rowlabels:
        return {
            "status": "grid_not_found",
            "notes": [f"หาป้ายกริดไม่ครบในหน้า {pno + 1} (columns={len(columns)}, rows={len(rowlabels)})"],
            "items": [], "positions": [], "totals": {},
        }

    pairs = extract_pier_footing_pairs(spans)
    for p in pairs:
        p["grid"] = f"{grid_utils.nearest_label(p['x'], columns)}{grid_utils.nearest_label(p['y'], rowlabels)}"

    scale_denom = grid_utils.find_scale_denominator(spans)
    pts_per_m = grid_utils.points_per_meter(scale_denom) if scale_denom else None
    filled_rects = grid_utils.filled_rects_on_page(page) if pts_per_m else []

    notes = []
    if pts_per_m is None:
        notes.append("ไม่พบค่า SCALE ในหัวกระดาษ -- ข้ามการวัดขนาดจากรูปวาด")

    for p in pairs:
        if pts_per_m and filled_rects:
            w, h = grid_utils.measure_rect_near_point(p["x"], p["y"], filled_rects, pts_per_m)
            p["size_m"] = [round(w, 2), round(h, 2)] if w else None
        else:
            p["size_m"] = None

    # จัดกลุ่มตามรหัสฐานราก -- ยึดขนาดที่พบบ่อยสุดต่อรหัสเป็นขนาดมาตรฐาน (เผื่อวัดคลาดเคลื่อนเล็กน้อย
    # จุดใดจุดหนึ่ง) แล้วนับจำนวน
    by_code = {}
    for p in pairs:
        code = p["footing_code"]
        if not code:
            continue
        by_code.setdefault(code, []).append(p)

    items = []
    total_concrete_net = 0.0
    for code, plist in sorted(by_code.items()):
        sizes = [tuple(p["size_m"]) for p in plist if p["size_m"]]
        size = max(set(sizes), key=sizes.count) if sizes else None
        count = len(plist)
        item = {
            "code": code, "count": count,
            "size_m": list(size) if size else None,
            "thickness_m": None,  # ต้องใช้ Phase B (AI vision) อ่านตารางสเปคที่ flatten
            "rebar": None,
            "concrete_m3_each": None,
            "concrete_m3_total": None,
            "source": "vector_geometry" if size else "unmeasured",
            "status": "needs_vision_for_spec",
        }
        if size:
            area = size[0] * size[1]
            item["area_m2_each"] = round(area, 4)
        items.append(item)

    unmatched = [p["pier_code"] for p in pairs if not p["footing_code"]]
    if unmatched:
        notes.append(f"จับคู่รหัสฐานรากไม่ได้ {len(unmatched)} จุด: {', '.join(unmatched)}")

    if use_vision_fallback and any(i["thickness_m"] is None for i in items):
        items, vision_notes = _apply_vision_footing_specs(pdf_path, items, drawing_no=spec_drawing_no)
        notes.extend(vision_notes)

    if any(i["thickness_m"] is None for i in items):
        notes.append("ยังไม่มีความหนา (T) และเหล็กเสริมสำหรับบางรายการ -- ตารางสเปคฐานรากมักถูก flatten "
                      "เป็น vector อ่านด้วย text ไม่ได้ และ AI vision fallback อ่านไม่สำเร็จ/ไม่ได้เปิดใช้")

    return {
        "status": "positions_and_sizes_confirmed" if items and all(i["size_m"] for i in items) else "partial",
        "drawing_page": pno + 1,
        "scale_denominator": scale_denom,
        "notes": notes,
        "items": items,
        "positions": [
            {"grid": p["grid"], "pier_code": p["pier_code"], "footing_code": p["footing_code"], "size_m": p["size_m"]}
            for p in pairs
        ],
        "total_count": len(pairs),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf_path")
    ap.add_argument("--drawing-no", default="S-05")
    ap.add_argument("--page", type=int, default=None)
    args = ap.parse_args()
    result = extract_footing_takeoff(args.pdf_path, drawing_no=args.drawing_no, page_index=args.page)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
