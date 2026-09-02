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

BEAM_CODE_RE = re.compile(r"^(B[0-9]+|CB|GB)$")
REBAR_COUNT_RE = re.compile(r"^(\d+)-DB\s*(\d+)\s*mm\.?$", re.IGNORECASE)
# ตัวอักษรนำหน้า "-RB" ต่างกันได้ต่อสำนักงานออกแบบ (เหมือนที่พบในตารางสเปคเสา) และหน่วยระยะห่างก็
# รองรับทั้ง มม./ม.
STIRRUP_RE = re.compile(r"^.?-?RB\s*(\d+)\s*mm\.?\s*@=?\s*([\d.]+)\s*(mm\.?|m\.?)?$", re.IGNORECASE)
SIZE_MM_RE = re.compile(r"^(\d+)\s*[xX]\s*(\d+)\s*mm\.?$")
BARE_DECIMAL_RE = re.compile(r"^(\d+\.\d+)$")

STRUCTURAL_CONCRETE_WASTE = 0.03
REBAR_WEIGHT_WASTE = 0.05
DB12_KG_PER_M = 0.888
RB6_KG_PER_M = 0.222
STIRRUP_HOOK_ALLOWANCE_M = 0.10

GEOMETRY_VISION_MODEL = "claude-sonnet-5"
CROP_MARGIN_PT = 150


def _cluster_by_axis(values, gap):
    """จัดกลุ่มค่าตัวเลข (x หรือ y) ที่ใกล้กันเป็นแถว/คอลัมน์เดียวกัน -- คั่นกลุ่มเมื่อช่องว่างระหว่าง
    ค่าที่เรียงแล้วเกิน gap"""
    ordered = sorted(values)
    groups = [[ordered[0]]]
    for v in ordered[1:]:
        if v - groups[-1][-1] > gap:
            groups.append([v])
        else:
            groups[-1].append(v)
    return groups


def _assign_type_code(x, y, type_cells, row_reps, style, row_gap=80):
    """หา TYPE cell ที่ span (x, y) เป็นของ โดยแบ่งเป็นแถวก่อน (ตามตำแหน่ง y ของ TYPE cell เอง)
    แล้วค่อยแบ่งคอลัมน์ภายในแถวนั้นด้วย x -- ใช้เส้นแบ่งกึ่งกลางระหว่าง TYPE cell ที่ติดกัน

    การแบ่งแถว **ไม่ใช้ระยะ 2D/มิดพอยต์ระหว่างป้าย** เพราะบล็อกข้อมูลของคานหนึ่งตัวมักกินพื้นที่แนวตั้ง
    มากกว่าครึ่งระยะห่างระหว่างแถว ทำให้ข้อมูลปลายบล็อกถูกดึงไปเป็นของแถวถัดไปผิดๆ ถ้าใช้มิดพอยต์ -- ใช้
    กฎ floor/ceiling ตาม style ที่ตรวจพบแทน (label_top: ข้อมูลอยู่หลังป้ายเสมอ -> แถวของ span คือป้าย
    ล่าสุดที่ y <= span y, label_bottom: ข้อมูลอยู่ก่อนป้ายเสมอ -> แถวของ span คือป้ายถัดไปที่ y >= span y)"""
    if style == "label_top":
        row_idx = 0
        for i, r in enumerate(row_reps):
            if r <= y:
                row_idx = i
    else:
        row_idx = len(row_reps) - 1
        for i in range(len(row_reps) - 1, -1, -1):
            if row_reps[i] >= y:
                row_idx = i
    cell_row = {i: min(range(len(row_reps)), key=lambda ri: abs(c[2] - row_reps[ri])) for i, c in enumerate(type_cells)}
    row_cells = [c for i, c in enumerate(type_cells) if cell_row[i] == row_idx]
    row_cells.sort(key=lambda c: c[1])
    col_bounds = [(row_cells[i][1] + row_cells[i + 1][1]) / 2 for i in range(len(row_cells) - 1)]
    col_idx = 0
    for b in col_bounds:
        if x >= b:
            col_idx += 1
        else:
            break
    return row_cells[col_idx][0]


def _build_schedule_for_style(candidates, type_cells, row_reps, style):
    """สร้างตารางสเปคคานจาก candidate spans ทั้งหมด โดยกำหนดรหัสคานของแต่ละ span ด้วย style
    (label_top/label_bottom) ที่ระบุ -- คืน dict {code: spec} เฉพาะรหัสที่มีข้อมูลเหล็กจริง (db)"""
    blocks = {code: {"db": [], "rb": [], "size_mm": [], "size_bare": []} for code, _, _ in type_cells}
    for s, t, x, y in candidates:
        code = _assign_type_code(x, y, type_cells, row_reps, style)

        m = REBAR_COUNT_RE.match(t)
        if m:
            blocks[code]["db"].append((int(m.group(1)), m.group(2), y))
            continue
        m = STIRRUP_RE.match(t)
        if m:
            spacing_raw = float(m.group(2))
            spacing_m = spacing_raw / 1000.0 if spacing_raw > 10 else spacing_raw
            blocks[code]["rb"].append((m.group(1), spacing_m, y))
            continue
        m = SIZE_MM_RE.match(t)
        if m:
            blocks[code]["size_mm"].append((int(m.group(1)), int(m.group(2))))
            continue
        m = BARE_DECIMAL_RE.match(t)
        if m:
            blocks[code]["size_bare"].append(float(m.group(1)))

    schedule = {}
    for code, d in blocks.items():
        if not d["db"]:
            continue
        # เส้นแบ่งบน/ล่าง: ใช้ตำแหน่ง y ของป้ายปลอก (RB) เป็นตัวแบ่งถ้ามี (แม่นกว่า เพราะแต่ละ
        # section คู่มีปลอกอยู่ตรงกลางเหล็กบน/ล่างเป๊ะ) ถ้าไม่มีปลอกเลย fallback เป็นค่ากลางของช่วง y
        if d["rb"]:
            divider = sum(y for _, _, y in d["rb"]) / len(d["rb"])
        else:
            ys = sorted({y for _, _, y in d["db"]})
            divider = (ys[0] + ys[-1]) / 2 if len(ys) > 1 else ys[0]
        top = [n for n, _, y in d["db"] if y <= divider]
        bottom = [n for n, _, y in d["db"] if y > divider]
        db_size = d["db"][0][1]
        max_top = max(top) if top else max(n for n, _, _ in d["db"])
        max_bottom = max(bottom) if bottom else max_top
        min_spacing = min((sp for _, sp, _ in d["rb"]), default=None)
        stirrup_size = d["rb"][0][0] if d["rb"] else None

        if d["size_mm"]:
            w, h = d["size_mm"][0]
            size_m = [w / 1000, h / 1000]
        elif d["size_bare"]:
            size_m = [round(min(d["size_bare"]), 3), round(max(d["size_bare"]), 3)]
        else:
            size_m = None

        schedule[code] = {
            "size_m": size_m,
            "top_bar_count": max_top, "bottom_bar_count": max_bottom, "db_size": db_size,
            "stirrup_size": stirrup_size, "stirrup_spacing_m": min_spacing,
        }
    return schedule


def parse_beam_schedule(doc):
    """หาแผ่นตารางขยายคาน แล้วดึงสเปคทุกรหัสด้วย grid-based clustering (แบ่งแถวตาม y ของ TYPE cell
    ก่อน แล้วแบ่งคอลัมน์ตาม x ภายในแถวนั้น ใช้เส้นแบ่งกึ่งกลางระหว่าง cell ที่ติดกัน) -- ไม่ hardcode
    ตำแหน่งหน้า/พิกัด/ป้ายหัวตาราง ("TOP BAR"/"STIRRUP") เพราะบางไฟล์ไม่มีป้ายหัวตารางเลย มีแต่ตัวเลข
    วางตำแหน่งสัมพัทธ์กับรูปตัด (เหล็กบน วาดเหนือเส้นปลอก, เหล็กล่าง วาดใต้เส้นปลอก) -- ใช้ตำแหน่งของ
    span ปลอก (RB) ที่ใกล้สุดในแต่ละ block เป็นเส้นแบ่งบน/ล่างแทน

    ไม่เดา label_top/label_bottom จากตำแหน่งเดียว (เจอ false positive จากข้อความอื่นในหน้าที่บังเอิญ
    match regex เดียวกัน เช่น scale/เลขแผ่นใกล้ขอบบน) -- ลองสร้างตารางทั้งสอง style แล้วเลือก style ที่
    ทำให้รหัสคานมีข้อมูลเหล็ก (db) ครบมากกว่า (style ที่ผิดมักทำให้บาง TYPE cell ทั้งแถวไม่มีข้อมูลเลย
    เพราะข้อมูลของแถวนั้นถูกดึงไปแถวข้างเคียงหมด)"""
    for pno in range(len(doc)):
        spans = extract_fixed_spans(doc[pno])
        texts = [s["text"].strip() for s in spans]

        type_cells = [(t, *grid_utils.center(s["bbox"])) for s, t in zip(spans, texts) if BEAM_CODE_RE.match(t)]
        if len(type_cells) < 2:
            # หน้าที่มีป้ายรหัสคานแค่จุดเดียวมักเป็นการพูดถึงเฉยๆ (เช่นหน้าอธิบายคำย่อ "GB = Ground
            # Beam") ไม่ใช่ตารางสเปคจริง -- ตารางสเปคจริงต้องมีหลายรหัสคานอยู่ด้วยกันเสมอ
            continue

        # จำกัดขอบเขตการค้นด้วย bounding box ของ TYPE cell ทั้งหมด (ขยายออกด้วย margin แนวนอน+แนวตั้ง
        # กว้าง เพราะบล็อกข้อมูลคานหนึ่งตัวอาจกินพื้นที่ทั้งแนวนอน/แนวตั้งเป็นร้อยจุด ไกลจากป้ายของตัวเอง
        # เช่น 116-69 ที่แต่ละ TYPE cell มี 3 sub-column ห่างจากป้ายได้ถึง 100 จุด) -- กันไม่ให้ตารางอื่น
        # บนหน้าเดียวกัน (เช่นตารางสเปคเสาที่ไม่มี TYPE cell เป็นของตัวเอง) ถูกดูดเข้ามาเป็นของคานทั้งที่
        # ไม่เกี่ยวกัน โดยไม่ต้องใช้ระยะตัดขาดคงที่ตายตัว
        margin_x, margin_y = 120, 250
        cell_xs = [cx for _, cx, _ in type_cells]
        cell_ys = [cy for _, _, cy in type_cells]
        box = (min(cell_xs) - margin_x, min(cell_ys) - margin_y, max(cell_xs) + margin_x, max(cell_ys) + margin_y)

        candidates = [(s, t, *grid_utils.center(s["bbox"])) for s, t in zip(spans, texts)
                      if box[0] <= grid_utils.center(s["bbox"])[0] <= box[2]
                      and box[1] <= grid_utils.center(s["bbox"])[1] <= box[3]]
        if not candidates:
            continue
        row_reps = sorted(sum(g) / len(g) for g in _cluster_by_axis([cy for _, _, cy in type_cells], 80))
        if len(row_reps) < 2:
            schedule = _build_schedule_for_style(candidates, type_cells, row_reps, "label_top")
        else:
            sched_top = _build_schedule_for_style(candidates, type_cells, row_reps, "label_top")
            sched_bottom = _build_schedule_for_style(candidates, type_cells, row_reps, "label_bottom")
            schedule = sched_top if len(sched_top) >= len(sched_bottom) else sched_bottom
        if schedule:
            return {"page": pno + 1, "schedule": schedule}
    return None


def build_candidate_segments(doc, pier_positions, plan_page=None):
    """สร้างรายการช่วงกริดที่ *อาจ* มีคานทาบ จากตำแหน่งเสาที่ยืนยันแล้ว (จุดต่อเนื่องกันบนแถว/คอลัมน์
    เดียวกัน) -- คำนวณความยาวจริงจากตำแหน่งกริด ไม่ต้องให้ AI อ่าน/บวกเลข.

    plan_page: เลขหน้า (0-indexed) ของแผ่นผังฐานราก/ตอม่อที่หาไว้แล้วจาก extract_footing_boq -- ใช้
    ซ้ำเป็นค่าเริ่มต้นเสมอ เพราะตำแหน่งเสาที่ใช้สร้างช่วงคานก็มาจากแผ่นเดียวกันนี้อยู่แล้ว และหลายไฟล์
    (ยืนยันจริง) มีทั้งแปลนฐานรากและแปลนคานพื้นรวมอยู่แผ่นเดียวกัน -- ถ้าไม่ระบุ (None) จะค้นหาแผ่นที่มี
    เส้นกริด+สเกลเอง (แผ่นแรกในเอกสารที่มี)."""
    if plan_page is not None:
        pno = plan_page
    else:
        pno = None
        for candidate in range(len(doc)):
            spans_c = extract_fixed_spans(doc[candidate])
            cols_c, rows_c = grid_utils.extract_grid(spans_c)
            if len(cols_c) >= 2 and len(rows_c) >= 2 and grid_utils.find_scale_denominator(spans_c):
                pno = candidate
                break
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
        return {"status": "spec_not_found", "notes": ["ไม่พบตารางขยายคาน (ไม่มีป้ายรหัสคาน B1/B2/.../CB/GB คู่กับสเปคเหล็กที่อ่านได้เลย)"],
                "items": []}
    schedule = schedule_result["schedule"]

    footing = extract_footing_takeoff(pdf_path, use_vision_fallback=False)
    pier_positions = [p["grid"] for p in footing.get("positions", []) if p.get("pier_code")]
    footing_plan_page = (footing["drawing_page"] - 1) if footing.get("drawing_page") else None
    if not pier_positions:
        return {"status": "no_pier_positions", "notes": ["ต้องมีตำแหน่งเสาก่อน (extract_footing_boq)"],
                "items": []}

    pno, segments, clip = build_candidate_segments(doc, pier_positions, plan_page=footing_plan_page)
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
