"""PDFtoBOQ -- งานโครงสร้าง: ถอดปริมาณคอนกรีต+เหล็กคาน (Beam Takeoff)

เขียนใหม่ทั้งหมด (2569-09-02) แทนเวอร์ชันเดิมที่ผูกกับโปรเจกต์ newhouse โดยเฉพาะ (สเปคคาน/หน้าตัด/
รหัส B1-B6 hardcode ในโค้ด อ่านจากแผ่น S-02 ที่ไม่มีในโปรเจกต์อื่น) -- ดู LOG.md ฝั่งเอกสารพิมพ์เขียว

วิธีทำงาน (สเปคใช้โค้ดล้วน, เรขาคณิตใช้ AI vision -- เพราะพิสูจน์แล้วว่าตำแหน่ง/ความยาวคานอ่านจาก
เรขาคณิต vector ไม่ได้ สีระบุชนิดคานเป็นภาพ raster ฝังในหน้า ไม่ใช่ vector fill):

1. สเปคคาน (หน้าตารางขยายคาน เช่น S-10): โค้ดล้วน 100% -- หา TYPE cell (B1/B2/.../CB) แต่ละอันเป็นจุด
   ยึด แล้วมอบ span อื่นในหน้าให้ block ที่ TYPE cell ใกล้ที่สุด (nearest-label clustering แบบเดียวกับ
   ที่ใช้จับคู่รหัสฐานราก-ตอม่อ) อ่านหน้าตัด+เหล็กบน/ล่าง/ปลอกจากทั้ง 3 ตำแหน่ง (Continuous/Mid/End)
   แล้วยึดค่า**มากสุด**ของเหล็กบน/ล่าง และ**ระยะห่างปลอกน้อยสุด**เป็นค่าใช้ตลอดความยาว (safe-side --
   ไม่ตีความกฎยืด/ตัดเหล็กละเอียดตาม location เหมือนที่วิศวกรออกแบบจริงทำ ได้ปริมาณสูงกว่าจริงเล็กน้อย
   ไม่ใช่ต่ำกว่า)
2. เรขาคณิตคาน (ตำแหน่ง/ความยาว): ใช้ตำแหน่งเสา (pier) ที่ยืนยันแล้วจาก extract_pier_column_boq.py
   เป็น "จุดต่อ" ที่เป็นไปได้ของคาน (คานวิ่งระหว่างจุดรองรับสองจุดที่ติดกันบนกริดเดียวกัน) -- คำนวณ
   ความยาวแต่ละช่วงจากตำแหน่งกริดจริง (ไม่ต้องให้ AI อ่าน/บวกเลขเอง) แล้วถาม AI vision แค่คำถามแคบๆ
   ต่อช่วง (มีคานทาบช่วงนี้ไหม รหัสอะไร ดูจากสี) แทนการให้ไล่ตามเส้นสีในภาพทั้งหมดเอง (ทดสอบแล้วพบว่า
   วิธีให้ AI ไล่เส้น+บวกความยาวเองมีอัตราผิดพลาดสูงกว่าการถามแบบมีจุดยึดพิกัดพิกเซลให้ชัดเจน)
   ใช้โมเดลที่แม่นกว่า (ไม่ใช่ default ที่เบากว่า) สำหรับงานแยกสีนี้โดยเฉพาะเพราะพิสูจน์แล้วว่าจำเป็น

**ข้อจำกัดที่ทราบ:** ครอบคลุมเฉพาะคานที่วิ่งระหว่างจุดเสา (pier) ที่ยืนยันแล้วเท่านั้น -- คานช่วงสั้นที่
รองรับด้วยจุดอื่นที่ไม่ใช่เสาหลัก (เช่น คานทางเข้า/กันสาดที่รองรับด้วยผนัง) จะไม่ถูกนับ ทำให้ความยาวรวม
ต่ำกว่าความเป็นจริงได้บ้าง -- ระบุสถานะ "partial_coverage" ไว้เสมอ ไม่อ้างว่าครบ 100%

Usage:
    python extract_beam_boq.py <pdf_path>
"""
import argparse
import json
import re
import sys

import fitz

import grid_utils
from extract_footing_boq import extract_footing_takeoff
from thai_font_fix import extract_fixed_spans

BEAM_CODE_RE = re.compile(r"^(B[0-9]+|CB)$")
REBAR_COUNT_RE = re.compile(r"^(\d+)-DB\s*(\d+)\s*mm\.?$", re.IGNORECASE)
STIRRUP_RE = re.compile(r"^RB\s*(\d+)\s*mm\.?\s*@=?\s*([\d.]+)\s*mm\.?$", re.IGNORECASE)
SIZE_MM_RE = re.compile(r"^(\d+)\s*[xX]\s*(\d+)\s*mm\.?$")

STRUCTURAL_CONCRETE_WASTE = 0.03
REBAR_WEIGHT_WASTE = 0.05
DB12_KG_PER_M = 0.888
RB6_KG_PER_M = 0.222
STIRRUP_HOOK_ALLOWANCE_M = 0.10

GEOMETRY_VISION_MODEL = "claude-sonnet-5"
CROP_MARGIN_PT = 150


def parse_beam_schedule(doc):
    """หาแผ่นตารางขยายคาน (มี TOP BAR + STIRRUP ปรากฏ) แล้วดึงสเปคทุกรหัสด้วย nearest-type-header
    clustering -- ไม่ hardcode ตำแหน่งหน้า/พิกัด ใช้ได้กับ layout ตารางหลายบล็อกต่อหน้าทั่วไป."""
    for pno in range(len(doc)):
        spans = extract_fixed_spans(doc[pno])
        texts = [s["text"].strip() for s in spans]
        if "TOP BAR" not in texts or "STIRRUP" not in texts:
            continue

        type_cells = [(t, *grid_utils.center(s["bbox"])) for s, t in zip(spans, texts) if BEAM_CODE_RE.match(t)]
        if not type_cells:
            continue

        blocks = {code: {"db": [], "rb": [], "size": []} for code, _, _ in type_cells}
        for s, t in zip(spans, texts):
            x, y = grid_utils.center(s["bbox"])
            candidates = [(code, cx, cy) for code, cx, cy in type_cells if cy <= y + 5]
            if not candidates:
                continue
            code = min(candidates, key=lambda c: (x - c[1]) ** 2 + (y - c[2]) ** 2)[0]

            m = REBAR_COUNT_RE.match(t)
            if m:
                blocks[code]["db"].append((int(m.group(1)), m.group(2), y))
                continue
            m = STIRRUP_RE.match(t)
            if m:
                blocks[code]["rb"].append((m.group(1), float(m.group(2)) / 1000))
                continue
            m = SIZE_MM_RE.match(t)
            if m:
                blocks[code]["size"].append((int(m.group(1)), int(m.group(2))))

        schedule = {}
        for code, d in blocks.items():
            if not d["db"]:
                continue
            ys = sorted({y for _, _, y in d["db"]})
            mid = (ys[0] + ys[-1]) / 2 if len(ys) > 1 else ys[0]
            top = [n for n, _, y in d["db"] if y <= mid]
            bottom = [n for n, _, y in d["db"] if y > mid]
            db_size = d["db"][0][1]
            max_top = max(top) if top else max(n for n, _, _ in d["db"])
            max_bottom = max(bottom) if bottom else max_top
            min_spacing = min((sp for _, sp in d["rb"]), default=None)
            stirrup_size = d["rb"][0][0] if d["rb"] else None
            size_mm = d["size"][0] if d["size"] else None
            schedule[code] = {
                "size_m": [size_mm[0] / 1000, size_mm[1] / 1000] if size_mm else None,
                "top_bar_count": max_top, "bottom_bar_count": max_bottom, "db_size": db_size,
                "stirrup_size": stirrup_size, "stirrup_spacing_m": min_spacing,
            }
        if schedule:
            return {"page": pno + 1, "schedule": schedule}
    return None


def build_candidate_segments(doc, pier_positions, drawing_no="S-06"):
    """สร้างรายการช่วงกริดที่ *อาจ* มีคานทาบ จากตำแหน่งเสาที่ยืนยันแล้ว (จุดต่อเนื่องกันบนแถว/คอลัมน์
    เดียวกัน) -- คำนวณความยาวจริงจากตำแหน่งกริด ไม่ต้องให้ AI อ่าน/บวกเลข."""
    pno = grid_utils.find_drawing_page(doc, drawing_no)
    if pno is None:
        return None, None, None
    page = doc[pno]
    spans = extract_fixed_spans(page)
    columns, rows = grid_utils.extract_grid(spans)
    col_x = dict(columns)
    row_y = dict(rows)
    scale_denom = grid_utils.find_scale_denominator(spans)
    pts_per_m = grid_utils.points_per_meter(scale_denom) if scale_denom else None
    if not pts_per_m:
        return None, None, None

    by_row, by_col = {}, {}
    for g in pier_positions:
        col, row = g[0], g[1:]
        if col not in col_x or row not in row_y:
            continue
        by_row.setdefault(row, []).append(g)
        by_col.setdefault(col, []).append(g)

    segments = []
    for row, pts in by_row.items():
        pts.sort(key=lambda g: col_x[g[0]])
        for a, b in zip(pts, pts[1:]):
            segments.append({
                "from": a, "to": b, "orientation": "horizontal",
                "length_m": round(abs(col_x[b[0]] - col_x[a[0]]) / pts_per_m, 3),
                "from_pt": (col_x[a[0]], row_y[row]), "to_pt": (col_x[b[0]], row_y[row]),
            })
    for col, pts in by_col.items():
        pts.sort(key=lambda g: row_y[g[1:]])
        for a, b in zip(pts, pts[1:]):
            segments.append({
                "from": a, "to": b, "orientation": "vertical",
                "length_m": round(abs(row_y[b[1:]] - row_y[a[1:]]) / pts_per_m, 3),
                "from_pt": (col_x[col], row_y[a[1:]]), "to_pt": (col_x[col], row_y[b[1:]]),
            })

    if not segments:
        return None, None, None

    xs = [p for s in segments for p in (s["from_pt"][0], s["to_pt"][0])]
    ys = [p for s in segments for p in (s["from_pt"][1], s["to_pt"][1])]
    clip = fitz.Rect(min(xs) - CROP_MARGIN_PT, min(ys) - CROP_MARGIN_PT,
                      max(xs) + CROP_MARGIN_PT, max(ys) + CROP_MARGIN_PT)
    clip = clip.intersect(page.rect)
    return pno, segments, clip


def classify_segments_via_vision(page, segments, clip, valid_codes, dpi=200):
    import ai_vision_fallback
    scale = dpi / 72.0
    to_px = lambda pt: (round((pt[0] - clip.x0) * scale), round((pt[1] - clip.y0) * scale))
    seg_list = [{"id": i, "from": s["from"], "to": s["to"],
                 "from_px": to_px(s["from_pt"]), "to_px": to_px(s["to_pt"])}
                for i, s in enumerate(segments)]
    codes_str = ", ".join(sorted(valid_codes))

    prompt = f"""ภาพนี้คือแปลนคาน (beam plan) พิกัดพิกเซล (x,y) นับจากมุมบนซ้ายของภาพนี้เป็น (0,0)
เส้นคานแต่ละเส้นมีสีต่างกันตามรหัส จับกลุ่มสีที่ต่างกันชัดเจนแล้วจับคู่กับรหัสตามป้ายชื่อที่อยู่ใกล้เส้น
นั้นที่สุด **รหัสคานที่มีจริงในโปรเจกต์นี้มีแค่: {codes_str} เท่านั้น -- ห้ามตอบรหัสอื่นนอกจากรายการนี้
เด็ดขาด แม้จะเห็นตัวเลขในภาพไม่ชัดก็ให้เลือกรหัสที่ใกล้เคียงที่สุดจากรายการนี้ ไม่ใช่สร้างรหัสใหม่**

นี่คือรายการ "เส้นกริดที่มีเสารองรับสองข้าง" (candidate segment) ที่ต้องการให้ตรวจสอบว่ามีคานทาบเส้นตรง
ระหว่างจุดสองจุดนั้นหรือไม่ (พิกัดพิกเซลของแต่ละจุด):
{json.dumps(seg_list, ensure_ascii=False)}

สำหรับแต่ละ id ในรายการ ให้ดูตำแหน่งพิกเซลนั้นในภาพว่ามีเส้นคาน (เส้นหนาระบายสี มีป้ายชื่อกำกับ) ทาบเส้น
ตรงระหว่างสองจุดนั้นจริงหรือไม่ ถ้ามีให้อ่านรหัสคาน (ต้องเป็นหนึ่งใน {codes_str} เท่านั้น) จากป้ายชื่อที่
ใกล้ที่สุด ถ้าไม่มีเส้นคานทาบเลย (เช่นเป็นช่องว่างหรือผนังเฉยๆ) ให้ตอบ code เป็น null ตอบสั้นกระชับ

ตอบเป็น JSON ล้วนๆ เท่านั้น ไม่มีข้อความอื่น ต้องมีผลลัพธ์ครบทุก id ({len(segments)} รายการ):
{{"results": [{{"id": 0, "code": "B4"}}, {{"id": 1, "code": null}}, ...]}}"""

    pix = page.get_pixmap(dpi=dpi, clip=clip)
    result = ai_vision_fallback.call_vision_json(pix.tobytes("png"), prompt,
                                                  model=GEOMETRY_VISION_MODEL, max_tokens=4096)
    return result


def extract_beam_takeoff(pdf_path):
    doc = fitz.open(pdf_path)
    notes = []

    schedule_result = parse_beam_schedule(doc)
    if schedule_result is None:
        return {"status": "spec_not_found", "notes": ["ไม่พบตารางขยายคาน (ต้องมี TOP BAR + STIRRUP)"],
                "items": []}
    schedule = schedule_result["schedule"]

    footing = extract_footing_takeoff(pdf_path, use_vision_fallback=False)
    pier_positions = [p["grid"] for p in footing.get("positions", []) if p.get("pier_code")]
    if not pier_positions:
        return {"status": "no_pier_positions", "notes": ["ต้องมีตำแหน่งเสาก่อน (extract_footing_boq)"],
                "items": []}

    pno, segments, clip = build_candidate_segments(doc, pier_positions)
    if segments is None:
        return {"status": "geometry_not_found", "notes": ["หากริด/สเกลสำหรับวางตำแหน่งคานไม่เจอ"],
                "items": []}

    try:
        import ai_vision_fallback  # noqa: F401
        vision_result = classify_segments_via_vision(doc[pno], segments, clip, valid_codes=set(schedule.keys()))
    except Exception as e:
        return {"status": "vision_call_failed", "notes": [f"AI vision เรียกไม่สำเร็จ (หน้า {pno + 1}): {e}"],
                "items": []}

    if vision_result.get("_parse_error"):
        return {"status": "vision_parse_failed",
                "notes": [f"AI vision อ่านผลไม่สำเร็จ (หน้า {pno + 1})", str(vision_result.get("_raw"))[:300]],
                "items": []}

    code_by_id = {r["id"]: r.get("code") for r in vision_result.get("results", [])}
    valid_codes = set(schedule.keys())
    invalid_codes_seen = set()
    totals = {}
    matched_segments = []
    for i, seg in enumerate(segments):
        code = code_by_id.get(i)
        if code and code not in valid_codes:
            invalid_codes_seen.add(code)
            code = None
        if not code:
            continue
        totals.setdefault(code, 0.0)
        totals[code] += seg["length_m"]
        matched_segments.append({**seg, "code": code})

    unmatched_count = len(segments) - len(matched_segments)
    notes.append(f"ครอบคลุมเฉพาะคานระหว่างจุดเสาที่ยืนยันแล้ว ({len(segments)} ช่วง, จับคู่ได้ {len(matched_segments)}) "
                 f"-- คานช่วงสั้นที่รองรับด้วยจุดอื่น (เช่นทางเข้า/กันสาด) ยังไม่ถูกนับ")
    if unmatched_count:
        notes.append(f"{unmatched_count} ช่วงที่ตรวจสอบแล้วไม่พบคานทาบ (อาจเป็นผนังเฉยๆ หรือ AI อ่านพลาด)")
    if invalid_codes_seen:
        notes.append(f"AI ตอบรหัสที่ไม่มีในตารางสเปคจริง {sorted(invalid_codes_seen)} -- ตัดทิ้ง (ถือเป็น null)")

    items = []
    for code, total_length in sorted(totals.items()):
        spec = schedule.get(code)
        item = {"code": code, "total_length_m": round(total_length, 2)}
        if spec and spec["size_m"]:
            w, h = spec["size_m"]
            item["size_m"] = [w, h]
            vol = w * h * total_length
            item["concrete_m3_net"] = round(vol, 4)
            item["concrete_m3_with_waste"] = round(vol * (1 + STRUCTURAL_CONCRETE_WASTE), 4)
            n_bars = spec["top_bar_count"] + spec["bottom_bar_count"]
            main_kg = total_length * n_bars * DB12_KG_PER_M
            item["main_bar_spec"] = f"{spec['top_bar_count']}+{spec['bottom_bar_count']}-DB{spec['db_size']}"
            item["main_bar_kg_net"] = round(main_kg, 2)
            item["main_bar_kg_with_waste"] = round(main_kg * (1 + REBAR_WEIGHT_WASTE), 2)
            if spec["stirrup_spacing_m"]:
                n_ties = int(total_length / spec["stirrup_spacing_m"]) + 1
                tie_perimeter = 2 * (w + h) + STIRRUP_HOOK_ALLOWANCE_M
                stirrup_kg = n_ties * tie_perimeter * RB6_KG_PER_M
                item["stirrup_spec"] = f"1-RB{spec['stirrup_size']}@{spec['stirrup_spacing_m']:.3f}m"
                item["stirrup_kg_net"] = round(stirrup_kg, 2)
                item["stirrup_kg_with_waste"] = round(stirrup_kg * (1 + REBAR_WEIGHT_WASTE), 2)
            item["status"] = "computed"
        else:
            item["status"] = "spec_missing"
            notes.append(f"ไม่มีสเปคหน้าตัด/เหล็กของรหัส {code} ในตารางขยายคาน -- ข้ามการคำนวณ")
        items.append(item)

    return {
        "status": "partial_coverage",
        "geometry_page": pno + 1,
        "schedule_page": schedule_result["page"],
        "items": items,
        "notes": notes,
        "candidate_segment_count": len(segments),
        "matched_segment_count": len(matched_segments),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf_path")
    args = ap.parse_args()
    result = extract_beam_takeoff(args.pdf_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
