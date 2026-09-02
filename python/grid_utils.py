"""PDFtoBOQ -- โมดูลกลาง: หาเส้นกริด + สเกล + วัดขนาดจาก vector fill สำหรับ PDF vector ล้วน

แยกออกมาจาก extract_footing_pier_grid_vector.py (พิสูจน์ใช้ได้จริงกับไฟล์ 116-69 แล้ว --
วัดขนาดฐานราก 18 จุด ตรงกับตาราง spec จริง + Revit schedule 3 ทาง) เพื่อให้ทุกหมวด
(ฐานราก/ตอม่อ-เสา/คาน/พื้น/หลังคา) เรียกใช้ร่วมกันได้ ไม่ต้องเขียนกริด/สเกลแยกทุกหมวด

วิธีทำงานโดยสรุป:
1. หาป้ายกริด: ตัวอักษรเดี่ยว A-Z ที่เรียงกันเป็นแถวเดียวกัน (ค่า y ใกล้กัน) = เส้นกริดแนวตั้ง
   (คอลัมน์), ตัวเลข 1-2 หลักที่เรียงกันเป็นคอลัมน์เดียวกัน (ค่า x ใกล้กัน) = เส้นกริดแนวนอน (แถว)
2. อ่านค่าสเกลจากป้าย "SCALE 1:N" ในหัวกระดาษ แปลงเป็นจุด PDF ต่อเมตร
3. วัดขนาดชิ้นส่วนใดๆ ที่วาดเป็นรูปสี่เหลี่ยมทึบสี (vector fill) จับคู่กับตำแหน่งที่สนใจด้วย
   ระยะใกล้ที่สุด (ศูนย์กลางต่อศูนย์กลาง)

ต้องมี thai_font_fix.py อยู่ในโฟลเดอร์เดียวกัน (import extract_fixed_spans จากตรงนั้น)
"""
import re
from collections import Counter

from thai_font_fix import extract_fixed_spans

COLUMN_LETTER_RE = re.compile(r"^[A-Z]$")
ROW_NUMBER_RE = re.compile(r"^[0-9]{1,2}$")
SCALE_RATIO_RE = re.compile(r"^1\s*:\s*([\d.]+)$")

POINTS_PER_INCH = 72.0
MM_PER_INCH = 25.4


def center(bbox):
    x0, y0, x1, y1 = bbox
    return (x0 + x1) / 2.0, (y0 + y1) / 2.0


def find_page_by_content(doc, required_keywords, start=0, require_grid=False):
    """หาแผ่นแบบจาก **หัวข้อ/เนื้อหาภาษาไทยบนแผ่นเอง** (เช่น "แปลนฐานราก", "แบบขยายคาน") แทนการเดา
    จากเลขแผ่น (S-05, S-09 ฯลฯ) -- เลขแผ่นเป็นธรรมเนียมเฉพาะสำนักงานออกแบบแต่ละที่ ไม่สื่อความหมาย
    เดียวกันข้ามโปรเจกต์เลย (ยืนยันจริง: โปรเจกต์หนึ่ง S-05=ผังตำแหน่ง แต่อีกโปรเจกต์ S-05=ตารางสเปค)
    -- required_keywords คือ list ของคำที่ต้องเจอ**ทุกคำ**ในหน้าเดียวกัน (AND ไม่ใช่ OR) คืนเลขหน้า
    (0-indexed) ของหน้าแรกที่ตรง หรือ None ถ้าไม่เจอเลย ค้นจากหน้า start เป็นต้นไป

    require_grid=True: ปฏิเสธหน้าที่ตรงคำค้นแต่ไม่มีเส้นกริด (A-E/1-8) จริง -- กันกรณีหน้าสารบัญ/
    legend ที่แค่ "พูดถึง" ชื่อแผ่นในตาราง ไม่ใช่ตัวแผ่นจริง (พบจริง: หน้าสารบัญ A-01 มีคำว่า
    "แปลนฐานราก" อยู่ในรายการสารบัญ ทำให้ match ผิดหน้าถ้าไม่เช็คกริด)"""
    for pno in range(start, len(doc)):
        spans = extract_fixed_spans(doc[pno])
        joined = " ".join(s["text"] for s in spans)
        if not all(kw in joined for kw in required_keywords):
            continue
        if require_grid:
            columns, rows = extract_grid(spans)
            if len(columns) < 2 or len(rows) < 2:
                continue
        return pno
    return None


def find_page_with_most_markers(doc, marker_re, min_count=3):
    """หาแผ่นที่มีป้ายตรงกับ marker_re (เช่น รหัสตอม่อ Cx) **มากที่สุด** ในทั้งเอกสาร ไม่ใช่แค่แผ่น
    แรกที่เจอ >= min_count -- ใช้เป็น fallback สุดท้ายเมื่อหาหัวข้อภาษาไทยไม่เจอ (เช่นเพราะฟอนต์
    หัวข้อเพี้ยนคนละแบบกับฟอนต์เนื้อหา ยังไม่รองรับใน thai_font_fix.py) แผ่นจริง (ผังตำแหน่ง) จะมี
    ป้ายซ้ำเป็นสิบๆ จุด ต่างจากแผ่นอื่นที่อาจมีคำบังเอิญตรงแค่ 3-4 จุด (เช่น ชื่อวิศวกรในกรอบข้อมูล
    แบบ) -- คืน None ถ้าไม่มีแผ่นไหนถึง min_count เลย"""
    best_pno, best_count = None, 0
    for pno in range(len(doc)):
        spans = extract_fixed_spans(doc[pno])
        count = sum(1 for s in spans if marker_re.match(s["text"].strip()))
        if count > best_count:
            best_pno, best_count = pno, count
    return best_pno if best_count >= min_count else None


SHEET_CODE_RE = re.compile(r"^[A-Z]{1,3}-\d{1,3}$")


def find_sheet_code_by_description(doc, description_keywords, index_min_count=8):
    """หาแผ่นเป้าหมายผ่าน**สารบัญแบบ (สheet index)** ของเอกสารเอง แทนการเดาเลขแผ่นตรงๆ -- ธรรมเนียมที่
    เจอจริงข้ามหลายโปรเจกต์ (Thai technical drawing sets) คือเกือบทุกไฟล์มีหน้าสารบัญที่แจกแจง "รหัสแผ่น:
    คำอธิบาย" ครบทุกแผ่น แต่**รหัสแผ่นที่ตรงกับความหมายเดียวกัน (เช่น "แปลนพื้น") ไม่เหมือนกันข้ามโปรเจกต์
    เลย** (ยืนยันจริง: โปรเจกต์หนึ่งแปลนพื้น=A-05 อีกโปรเจกต์=A-03) -- จึงต้องอ่านสารบัญของไฟล์นั้นเองก่อน
    ทุกครั้ง ไม่ hardcode รหัสแผ่นใดๆ

    วิธีหา: หน้าสารบัญมีลักษณะเด่นชัด (นับได้ง่าย ไม่ต้องพึ่งหัวข้อภาษาไทยที่อาจเพี้ยน) คือมีข้อความรูป
    แบบ "X-NN" (เช่น A-01, S-05) เรียงกันเป็นสิบๆ รายการในหน้าเดียว -- มากกว่าแผ่นแบบอื่นใดๆ ที่ปกติมีแค่
    รหัสแผ่นตัวเอง 1 รหัส หรืออ้างอิงแผ่นอื่นผ่าน callout ไม่กี่จุด

    description_keywords: list ของคำที่ต้องเจอทุกคำในคำอธิบายของแถวเดียวกัน (AND) -- คืน (sheet_code,
    description) ของแถวแรกที่ตรง หรือ (None, None) ถ้าไม่เจอหน้าสารบัญ/ไม่เจอแถวที่ตรงเลย"""
    best_pno, best_count = None, 0
    for pno in range(len(doc)):
        spans = extract_fixed_spans(doc[pno])
        count = sum(1 for s in spans if SHEET_CODE_RE.match(s["text"].strip().upper()))
        if count > best_count:
            best_pno, best_count = pno, count
    if best_pno is None or best_count < index_min_count:
        return None, None

    spans = extract_fixed_spans(doc[best_pno])
    codes = [(s["text"].strip().upper(), *center(s["bbox"])) for s in spans if SHEET_CODE_RE.match(s["text"].strip().upper())]
    others = [(s["text"].strip(), *center(s["bbox"])) for s in spans
              if not SHEET_CODE_RE.match(s["text"].strip().upper()) and s["text"].strip()]
    for code, cx, cy in codes:
        # คำอธิบายอยู่แถวเดียวกัน (y ใกล้กัน) ทางขวาของรหัสแผ่นเสมอ (รูปแบบตารางสารบัญมาตรฐาน)
        cands = sorted((c for c in others if abs(c[2] - cy) < 6 and c[1] > cx), key=lambda c: c[1])
        if not cands:
            continue
        desc = cands[0][0]
        if all(k in desc for k in description_keywords):
            return code, desc
    return None, None


def find_drawing_page_by_title_block(doc, drawing_no, bottom_fraction=0.88):
    """หาหน้าที่มีป้าย "DRAWING NO." ตรงกับ drawing_no เป๊ะๆ โดยดูเฉพาะข้อความที่อยู่ค่อนไปทางล่างสุด
    ของหน้า (title block) เท่านั้น -- แม่นกว่า find_drawing_page เดิมเพราะไม่ต้องพึ่ง marker ของแต่ละ
    หมวด และไม่หลงไปจับหน้าสารบัญที่แค่ "พูดถึง" รหัสนี้ในตาราง (title block ของ AutoCAD template ส่วน
    ใหญ่วางไว้ท้ายหน้าเสมอ). คืน None ถ้าไม่เจอ -- ให้ผู้เรียก fallback ไปใช้ find_drawing_page แทน."""
    target = drawing_no.upper().strip()
    for pno in range(len(doc)):
        page = doc[pno]
        h = page.rect.height
        spans = extract_fixed_spans(page)
        for s in spans:
            text = s["text"].strip().upper()
            y = (s["bbox"][1] + s["bbox"][3]) / 2
            if text == target and y > h * bottom_fraction:
                return pno
    return None


def find_drawing_page(doc, drawing_no, min_marker_count=3, marker_re=None):
    """หาหน้าที่มีป้าย DRAWING NO. ตรงกับ drawing_no (เช่น 'S-05') จริง -- แยกจากหน้าสารบัญที่
    แค่ "พูดถึง" รหัสนี้ในตาราง ลองด้วย title block ก่อน (แม่นสุด, ดู find_drawing_page_by_title_block)
    แล้วค่อย fallback ไปเช็คว่าหน้านั้นมีป้ายที่ตรงกับ marker_re อยู่หลายจุด (เผื่อ template ไม่ได้วาง
    title block ไว้ตำแหน่งมาตรฐาน) (ค่าเริ่มต้น marker_re: รหัสตอม่อ Cx -- ปรับได้ตามหมวด)."""
    pno = find_drawing_page_by_title_block(doc, drawing_no)
    if pno is not None:
        return pno

    if marker_re is None:
        marker_re = re.compile(r"^C[0-9]+[A-Za-z]?$")
    target = drawing_no.upper()
    for pno in range(len(doc)):
        page = doc[pno]
        spans = extract_fixed_spans(page)
        texts = [s["text"] for s in spans]
        if target not in texts:
            continue
        marker_count = sum(1 for t in texts if marker_re.match(t))
        if marker_count >= min_marker_count:
            return pno
    return None


def _cluster_by_axis(candidates, axis, tolerance=3.0):
    """candidates: list of (text, x, y). axis: 0 for x, 1 for y. หากลุ่มพิกัดตามแกน axis ที่มี
    ความถี่มากที่สุด (ปัดเศษ tolerance) แล้วคืนเฉพาะ candidate ที่อยู่ในกลุ่มนั้น -- ตัดพวก
    stray text ที่บังเอิญ match regex ทิ้งไป."""
    if not candidates:
        return []
    buckets = Counter(round(c[1 + axis] / tolerance) * tolerance for c in candidates)
    best_bucket, _ = buckets.most_common(1)[0]
    return [c for c in candidates if abs(c[1 + axis] - best_bucket) <= tolerance * 1.5]


def extract_grid(spans):
    """คืน (columns, rows): list of (text, coord) แต่ละอัน -- columns เรียงตาม x (ซ้าย->ขวา),
    rows เรียงตาม y (บน->ล่าง)."""
    col_candidates = []
    row_candidates = []
    for s in spans:
        text = s["text"].strip()
        x, y = center(s["bbox"])
        if COLUMN_LETTER_RE.match(text):
            col_candidates.append((text, x, y))
        elif ROW_NUMBER_RE.match(text):
            row_candidates.append((text, x, y))

    cols = _cluster_by_axis(col_candidates, axis=1)  # กลุ่ม y เดียวกัน -> คอลัมน์
    rows = _cluster_by_axis(row_candidates, axis=0)  # กลุ่ม x เดียวกัน -> แถว

    columns = sorted({(text, x) for text, x, _y in cols}, key=lambda c: c[1])
    rowlabels = sorted({(text, y) for text, _x, y in rows}, key=lambda r: r[1])
    return columns, rowlabels


def nearest_label(coord, labels):
    text, _pos = min(labels, key=lambda lbl: abs(lbl[1] - coord))
    return text


def find_scale_denominator(spans):
    """หาตัวเลขสเกลจากป้าย "SCALE" ในหัวกระดาษ (เช่น "1 : 75" -> 75.0). คืน None ถ้าไม่เจอ
    หรือเป็นสเกลแบบ "As indicated" ที่ไม่มีตัวเลขเดียวใช้ได้ทั้งหน้า."""
    for s in spans:
        m = SCALE_RATIO_RE.match(s["text"].strip())
        if m:
            return float(m.group(1))
    return None


def points_per_meter(scale_denominator):
    """สเกล 1:N หมายถึง 1 เมตรจริง = 1000/N มม.บนกระดาษ -- แปลงเป็นจุด PDF (1/72 นิ้ว)."""
    mm_on_paper = 1000.0 / scale_denominator
    return POINTS_PER_INCH * mm_on_paper / MM_PER_INCH


def filled_rects_on_page(page):
    """คืนรายการ rect (fitz.Rect) ของทุกรูปที่ระบายสีทึบ (vector fill) บนหน้านั้น -- ใช้เป็น
    ตัวเลือกสำหรับ measure_rect_near_point()."""
    rects = []
    for d in page.get_drawings():
        if d.get("fill") is None:
            continue
        rect = d["rect"]
        if rect.width <= 0 or rect.height <= 0:
            continue
        rects.append(rect)
    return rects


def measure_rect_near_point(px, py, filled_rects, pts_per_m):
    """หารูปสี่เหลี่ยมทึบสีที่ใกล้จุด (px,py) ที่สุด (ศูนย์กลางต่อศูนย์กลาง) แล้วคืนขนาดจริง
    (width_m, height_m) -- คืน (None, None) ถ้าไม่มีรูปทึบสีเลยบนหน้านั้น. ใช้ได้กับชิ้นส่วนใดๆ
    ที่วาดเป็นรูปทึบสี (พิสูจน์แล้วกับฐานราก -- 18 จุด ตรงกับสเปคจริง 3 ทาง)."""
    if not filled_rects:
        return None, None
    nearest = min(
        filled_rects,
        key=lambda r: ((r.x0 + r.x1) / 2 - px) ** 2 + ((r.y0 + r.y1) / 2 - py) ** 2,
    )
    return nearest.width / pts_per_m, nearest.height / pts_per_m


def page_scale_and_grid(page):
    """ทางลัด: ให้หน้า fitz หนึ่งหน้า คืน (spans, columns, rows, scale_denominator, pts_per_m)
    ครบชุดในคำเรียกเดียว -- pts_per_m เป็น None ถ้าหาค่าสเกลไม่เจอ (ต้อง fallback เป็นค่าประมาณ
    เอง ห้ามหยุดรอผู้ใช้ ตามกฎที่ตัดสินใจไว้)."""
    spans = extract_fixed_spans(page)
    columns, rows = extract_grid(spans)
    scale_denom = find_scale_denominator(spans)
    pts_per_m = points_per_meter(scale_denom) if scale_denom is not None else None
    return spans, columns, rows, scale_denom, pts_per_m
