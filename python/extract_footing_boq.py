"""PDFtoBOQ -- งานโครงสร้าง: ถอดปริมาณคอนกรีต+เหล็กฐานราก (Footing Takeoff)

**แก้ 2569-09-02 (รอบ 2):** เดิมค้นหาแผ่นแบบด้วย**เลขแผ่น** (`drawing_no="S-05"` ค่าเริ่มต้น, สเปค
`spec_drawing_no="S-09"`) ซึ่งเป็นค่าที่จำมาจากไฟล์ 116-69 ตัวเดียว -- ทดสอบกับไฟล์โปรเจกต์อื่นแล้วพัง
ทันที เพราะ **เลขแผ่นเป็นธรรมเนียมเฉพาะสำนักงานออกแบบแต่ละที่ ไม่สื่อความหมายเดียวกันข้ามโปรเจกต์เลย**
(ไฟล์หนึ่ง S-05=ผังตำแหน่งฐานราก แต่อีกไฟล์ S-05=ตารางสเปคละเอียดคนละเรื่อง) -- เปลี่ยนมาค้นจาก
**หัวข้อภาษาไทยบนแผ่นเอง** ("แปลนฐานราก" / "แบบขยายฐานราก") ด้วย grid_utils.find_page_by_content()
แทนทั้งหมด ไม่ผูกกับเลขแผ่นอีกต่อไป (ยัง fallback ไปใช้ heuristic นับ marker เดิมได้ถ้าหาหัวข้อไม่เจอ)

วิธีทำงาน (โค้ดล้วน 100%, ไม่มีต้นทุน AI สำหรับตำแหน่ง/ขนาด):
1. หาแผ่นผังตำแหน่งฐานราก จากหัวข้อ "แปลนฐานราก" (หรือ fallback: แผ่นที่มีป้ายรหัสตอม่อ Cx เยอะ)
2. หาเส้นกริด + อ่านสเกลจากหัวกระดาษ ด้วย grid_utils
3. จับคู่รหัสตอม่อ (Cx) กับรหัสฐานราก (Fx) ที่ใกล้ที่สุด -- รองรับทั้งป้ายแยก 2 ป้าย ("C1" กับ "F1" คนละ
   ตำแหน่ง) และป้ายรวมเดียว ("F1/C1" หรือ "C1/F1" ในข้อความเดียว, พบจริงในบางโปรเจกต์)
4. วัดขนาดจริงของแต่ละฐานรากจากรูปสี่เหลี่ยมทึบสี (vector fill) ที่วาดไว้บนแบบ

**ข้อจำกัดที่ทราบอยู่แล้ว:** ความหนา (T) และเหล็กเสริม บางไฟล์อยู่ในตาราง "แบบขยายฐานราก" ที่ถูก
flatten เป็นเส้น vector ล้วน อ่านด้วย page.get_text() ไม่ได้ (พบใน 116-69) -- กรณีนี้ใช้ AI vision
fallback อ่านแทน แต่บางไฟล์ตารางนี้เป็น text จริงอ่านได้ตรงๆ (พบในโปรเจกต์อื่น) -- โค้ดนี้ลองอ่านด้วย
text ก่อนเสมอ ค่อย fallback ไป AI vision เฉพาะเมื่อจำเป็นจริงๆ

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

PIER_CODE_RE = re.compile(r"^C[0-9]+[A-Za-z]?$")
FOOTING_CODE_RE = re.compile(r"^F[0-9]+$")
COMBINED_LABEL_RE = re.compile(r"^(F[0-9]+)/(C[0-9A-Za-z]+)$|^(C[0-9A-Za-z]+)/(F[0-9]+)$")
# ใช้หา "แผ่นที่มีป้ายรหัสตอม่อ/ฐานรากเยอะที่สุด" ตอน fallback -- ต้องจับได้ทั้งป้ายแยก ("C1") และ
# ป้ายรวม ("F1/C1") เพราะบางไฟล์ใช้แต่ป้ายรวมล้วนๆ ไม่มีป้ายแยกเลยสักจุด (ถ้าใช้แค่ PIER_CODE_RE
# แผ่นจริงจะนับได้ 0 จุดเพราะไม่มีป้ายแยก ทำให้ fallback เลือกแผ่นผิดไปเจอที่อื่นที่บังเอิญมีคำว่า
# "C1" 3-4 จุด เช่นชื่อวิศวกรในกรอบข้อมูลแบบ)
PIER_OR_COMBINED_RE = re.compile(
    r"^C[0-9]+[A-Za-z]?$|^F[0-9]+/C[0-9A-Za-z]+$|^C[0-9A-Za-z]+/F[0-9]+$"
)

FOOTING_PLAN_TITLE_KEYWORDS = ["แปลนฐานราก"]
FOOTING_SPEC_TITLE_KEYWORDS = ["แบบขยายฐานราก"]

STRUCTURAL_CONCRETE_WASTE = 0.03

FOOTING_SPEC_TEXT_RE = re.compile(r"^F[0-9]+$")
FOOTING_SPEC_THICKNESS_RE = re.compile(r"^([\d.]+)$")
FOOTING_SPEC_SIZE_RE = re.compile(r"^([\d.]+)\s*[xX]\s*([\d.]+)$")
FOOTING_SPEC_REBAR_RE = re.compile(r"^\d+\+\d+-DB\d+\s*mm\.?#?$", re.IGNORECASE)

FOOTING_SPEC_VISION_PROMPT = """หน้านี้เป็นแบบก่อสร้างวิศวกรรมโครงสร้าง (แบบขยาย) มีหลายตารางในหน้าเดียว
หาตารางที่ชื่อ "แบบขยายฐานราก" (footing detail schedule) ซึ่งมีคอลัมน์หัวตาราง F, T, A x B, N# และแถว
ข้อมูลรหัส F1, F2, F3 (หรือรหัส Fx อื่นๆ ที่มี) อ่านค่าทุกแถวแล้วตอบเป็น JSON ล้วนๆ เท่านั้น ไม่มีข้อความ
อื่นใดๆ ในรูปแบบนี้:
{"items": [{"code": "F1", "thickness_m": 0.25, "size_m": [0.60, 0.60], "rebar": "5+5-DB12mm"}, ...]}
thickness_m และ size_m ต้องเป็นหน่วยเมตร (แปลงจากหน่วยอื่นถ้าตารางไม่ได้เขียนเป็นเมตร) ถ้าหาตารางนี้
ไม่เจอในภาพเลย ให้ตอบ {"items": [], "error": "not_found"}"""


def find_footing_spec_by_text(doc):
    """ลองอ่านตาราง "แบบขยายฐานราก" ด้วย text ตรงๆ ก่อนเสมอ (บางไฟล์ตารางนี้ไม่ได้ flatten เหมือน
    116-69) -- หาแผ่นจากหัวข้อ แล้วจับคู่ span ที่ตรงรูปแบบ F-code/thickness/size/rebar โดยดูแถวถัดจาก
    รหัส Fx ที่ใกล้กันในแนวนอน (ตาราง 1 แถวต่อ 1 รหัส) คืน None ถ้าหาแผ่นหรือรูปแบบที่คาดไว้ไม่เจอ."""
    pno = grid_utils.find_page_by_content(doc, FOOTING_SPEC_TITLE_KEYWORDS)
    if pno is None:
        return None, None
    spans = extract_fixed_spans(doc[pno])
    codes = [(s["text"].strip(), *grid_utils.center(s["bbox"])) for s in spans
             if FOOTING_SPEC_TEXT_RE.match(s["text"].strip())]
    if not codes:
        return None, pno

    others = []
    for s in spans:
        t = s["text"].strip()
        x, y = grid_utils.center(s["bbox"])
        if FOOTING_SPEC_SIZE_RE.match(t) or FOOTING_SPEC_REBAR_RE.match(t) or re.match(r"^[\d.]+$", t):
            others.append((t, x, y))

    results = {}
    for code, cx, cy in codes:
        row = [o for o in others if abs(o[2] - cy) < 5 and o[1] > cx]
        row.sort(key=lambda o: o[1])
        thickness, size, rebar = None, None, None
        for t, x, y in row:
            m = FOOTING_SPEC_SIZE_RE.match(t)
            if m:
                size = [float(m.group(1)), float(m.group(2))]
                continue
            if FOOTING_SPEC_REBAR_RE.match(t):
                rebar = t
                continue
            if thickness is None and re.match(r"^[\d.]+$", t) and not size:
                thickness = float(t)
        if size or rebar:
            results[code] = {"thickness_m": thickness, "size_m": size, "rebar": rebar}
    return (results or None), pno


def _apply_vision_footing_specs(pdf_path, items):
    """เติม thickness_m/rebar ให้ items ที่ยังเป็น None ด้วย AI vision อ่านตารางสเปคที่ flatten เป็น
    vector (page.get_text() อ่านไม่ได้จริง) -- หาแผ่นจาก**หัวข้อ**"แบบขยายฐานราก" ไม่ใช่เลขแผ่น -- เรียก
    AI แค่ครั้งเดียวต่อไฟล์ ไม่ใช่ครั้งละรายการ. คืน (items, notes) -- ถ้าเรียก AI ไม่สำเร็จ items จะไม่
    ถูกแก้ไข แค่เติม note อธิบายไว้ ไม่ทำให้ pipeline ทั้งหมดล้ม."""
    notes = []
    try:
        import ai_vision_fallback
    except ImportError as e:
        notes.append(f"ข้าม AI vision fallback: import ไม่สำเร็จ ({e})")
        return items, notes

    doc = fitz.open(pdf_path)
    pno = grid_utils.find_page_by_content(doc, FOOTING_SPEC_TITLE_KEYWORDS)
    if pno is None:
        # fallback: บางไฟล์ตารางฐานรากถูก flatten ทั้งหมดรวมหัวข้อด้วย (ไม่เหลือ text ให้ค้นเจอเลย
        # แม้แต่ชื่อหัวข้อเอง, พบจริงกับ 116-69) แต่ตารางสเปคเสา/ตอม่อ (MAIN REBAR/STIRRUP) มักอยู่
        # หน้าเดียวกับตารางฐานราก (แผ่น "แบบขยายโครงสร้าง" รวมทุกหมวดไว้ที่เดียว) ลองหาจากตรงนั้นแทน
        for candidate in range(len(doc)):
            texts_lower = [s["text"].strip().lower() for s in extract_fixed_spans(doc[candidate])]
            if any("rebar" in t for t in texts_lower) and any("stirrup" in t for t in texts_lower):
                pno = candidate
                break
    if pno is None:
        notes.append("ข้าม AI vision fallback: ไม่พบแผ่น 'แบบขยายฐานราก' และไม่พบแผ่นสเปคเสาที่อาจอยู่ร่วมกัน")
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
        notes.append(f"เติมความหนา+เหล็กเสริมจาก AI vision อ่านหน้า {pno + 1}: {', '.join(filled)}")
    return items, notes


def extract_pier_footing_pairs(spans):
    """จับคู่รหัสตอม่อ (Cx) กับรหัสฐานราก (Fx) ที่ใกล้ที่สุด -- รองรับทั้งป้ายแยก 2 ป้ายคนละตำแหน่ง
    (116-69: "C1" กับ "F1" วางใกล้กัน) และป้ายรวมเดียวกัน ("F1/C1" ข้อความเดียว, พบในบางโปรเจกต์) ถ้า
    เป็นป้ายรวม ถือว่าทั้งสองรหัสอยู่ตำแหน่งเดียวกันเป๊ะ จับคู่กันเองโดยไม่ต้องหาระยะใกล้สุด"""
    piers, footings = [], []
    for s in spans:
        text = s["text"].strip()
        x, y = grid_utils.center(s["bbox"])

        m = COMBINED_LABEL_RE.match(text)
        if m:
            f_code = m.group(1) or m.group(4)
            c_code = m.group(2) or m.group(3)
            piers.append((c_code, x, y))
            footings.append((f_code, x, y))
            continue

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


def extract_footing_takeoff(pdf_path, drawing_no=None, page_index=None, use_vision_fallback=True):
    """drawing_no: ระบุเลขแผ่นเองได้ (override) ถ้าไม่ระบุ (ค่าเริ่มต้น None) จะค้นจากหัวข้อ
    "แปลนฐานราก" อัตโนมัติก่อนเสมอ ค่อย fallback ไปใช้ heuristic นับป้ายรหัสตอม่อถ้าหาหัวข้อไม่เจอ"""
    doc = fitz.open(pdf_path)
    if page_index is not None:
        pno = page_index - 1
    elif drawing_no:
        pno = grid_utils.find_drawing_page(doc, drawing_no, marker_re=PIER_CODE_RE)
        if pno is None:
            return {
                "status": "not_found",
                "notes": [f"ไม่พบหน้าแบบ {drawing_no} ที่มีป้ายรหัสตอม่ออยู่จริง"],
                "items": [], "positions": [], "totals": {},
            }
    else:
        pno = grid_utils.find_page_by_content(doc, FOOTING_PLAN_TITLE_KEYWORDS, require_grid=True)
        if pno is None:
            # fallback: หาแผ่นที่มีป้ายรหัสตอม่อ (Cx) เยอะที่สุดในเอกสาร (ไม่ใช่แค่แผ่นแรกที่เจอ >=3
            # จุด -- กันกรณีบังเอิญตรงที่อื่น เช่น ชื่อวิศวกรในกรอบข้อมูลแบบ)
            pno = grid_utils.find_page_with_most_markers(doc, PIER_OR_COMBINED_RE, min_count=3)
        if pno is None:
            return {
                "status": "not_found",
                "notes": ["ไม่พบแผ่น 'แปลนฐานราก' และไม่พบแผ่นที่มีป้ายรหัสตอม่อหนาแน่นพอ"],
                "items": [], "positions": [], "totals": {},
            }

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
    for code, plist in sorted(by_code.items()):
        sizes = [tuple(p["size_m"]) for p in plist if p["size_m"]]
        size = max(set(sizes), key=sizes.count) if sizes else None
        count = len(plist)
        item = {
            "code": code, "count": count,
            "size_m": list(size) if size else None,
            "thickness_m": None,
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

    # 1. ลองอ่านตารางสเปคด้วย text ตรงๆ ก่อนเสมอ (ถูกกว่า แม่นกว่า ไม่ต้องพึ่ง AI)
    text_specs, spec_page = find_footing_spec_by_text(doc)
    if text_specs:
        filled = []
        for item in items:
            spec = text_specs.get(item["code"])
            if spec and item["thickness_m"] is None:
                item["thickness_m"] = spec.get("thickness_m")
                item["size_m"] = item["size_m"] or spec.get("size_m")
                item["rebar"] = spec.get("rebar")
                item["status"] = "confirmed_via_text"
                filled.append(item["code"])
        if filled:
            notes.append(f"เติมความหนา+เหล็กเสริมจากตาราง text จริงหน้า {spec_page + 1}: {', '.join(filled)}")

    # 2. เหลือรายการไหนที่ยังไม่มีความหนา ค่อย fallback ไป AI vision (เฉพาะกรณีตารางถูก flatten)
    if use_vision_fallback and any(i["thickness_m"] is None for i in items):
        items, vision_notes = _apply_vision_footing_specs(pdf_path, items)
        notes.extend(vision_notes)

    if any(i["thickness_m"] is None for i in items):
        notes.append("ยังไม่มีความหนา (T) และเหล็กเสริมสำหรับบางรายการ -- ตารางสเปคฐานรากอาจถูก flatten "
                      "เป็น vector และ AI vision fallback อ่านไม่สำเร็จ/ไม่ได้เปิดใช้")

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
    ap.add_argument("--drawing-no", default=None, help="ระบุเลขแผ่นเอง (override) ปกติไม่ต้องใส่")
    ap.add_argument("--page", type=int, default=None)
    args = ap.parse_args()
    result = extract_footing_takeoff(args.pdf_path, drawing_no=args.drawing_no, page_index=args.page)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
