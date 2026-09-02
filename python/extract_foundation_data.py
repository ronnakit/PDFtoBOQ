"""ไพน้อย — Stage 0: Foundation Data Extraction

Reads the reference pages of a construction-drawing PDF ONCE (cover, site plan,
sheet index, spec/legend) plus the title-block "DWG. NO." of every page, and
saves the result as <pdf_dir>/foundation_data.md next to the PDF.

foundation_data.md is a SINGLE file, human-readable Thai prose at the top for
review, with the actual structured data embedded as one fenced ```json block
lower down -- same pattern as 04-category-schema.md + schema_loader.py. There
is no separate .json file: editing the embedded JSON block in the .md IS
editing ไพน้อย's data, nothing else needs to stay in sync.

On every later run, if foundation_data.md already exists, its embedded JSON is
loaded directly and the PDF is NOT re-read — per the Journey
(03-ai-boq-procedure.md): never repeat Stage 0 once done for a project.

Usage:
    python extract_foundation_data.py <pdf_path> --cover-page N --site-page N
        --index-page N --spec-page N [--force]

Page numbers are 1-indexed. All four are REQUIRED, no defaults — page order is
specific to each project's own drawing set (e.g. one project: 1=cover, 2=site
plan, 3=index, 4=spec; another project may order these completely differently
or split them across more pages). Identify each page by its actual content
(open the PDF, read the sheet titles) before running — never assume any fixed
page numbers apply to a new project.
"""
import argparse
import base64
import io
import json
import os
import re
import time

import anthropic
import fitz
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from PIL import Image, ImageDraw

MODEL = "claude-haiku-4-5"
# Stage 0's 4 single-page reads (cover/site/index/spec) run ONCE per project ever, and
# proved unreliable on Haiku even at full resolution (dense multi-section Thai tables,
# not simple isolated codes) - verified by eye against the actual PDF pages. Accuracy
# matters far more than cost here, so use a stronger model; the 29-page title-block
# batch is a simple "read one short code" task and stays on Haiku (0 mismatches).
STRONG_MODEL = "claude-sonnet-5"

COVER_PROMPT = """This is the cover page of a Thai construction-permit PDF, with an official
municipal stamp and signatures. Extract:
- project name / house type
- owner name
- site address
- permit number (เลขที่ใบอนุญาต)
- permit book/volume reference if shown (เล่มที่)
- permit date (วันที่)
Respond with ONLY JSON: {"project_name":"...","owner":"...","address":"...","permit_no":"...","book_no":"...","permit_date":"...","notes":"..."}"""

SITE_PROMPT = """This is a site plan page (ผังบริเวณ) from a Thai construction-permit PDF.
Extract whatever of these is legible:
- title deed number (โฉนดที่ดินเลขที่) and any land parcel reference numbers
- overall site/plot dimensions if labeled
- notable site elements mentioned (โรงจอดรถ, แนวรั้ว, แนวท่อระบายน้ำ, etc.) - just list which of these appear, don't measure them
Respond with ONLY JSON: {"title_deed_no":"...","land_parcel_ref":"...","site_elements_present":["..."],"notes":"..."}"""

INDEX_PROMPT = """This is the drawing sheet index page (สารบัญแบบ) from a Thai construction PDF.
It has TWO separate sections - extract both.

SECTION 1 - the sheet index tables: sheet codes (e.g. A-01, A-02, S-01, E-01) with their
titles, usually grouped by discipline (สถาปัตยกรรม/Architecture, วิศวกรรม/Structural,
ไฟฟ้า/Electrical, สุขาภิบาล/Sanitary). Read every row of every table.

SECTION 2 - the drawing notation legend (รายการสัญลักษณ์แบบสถาปัตยกรรม), usually a separate
column on the page - this defines symbols used THROUGHOUT the whole drawing set (not specific
to this page), needed to correctly read later plan/section/detail pages. Extract, if present:
- the dimension-reference symbols (circle/X marks for center-to-center, center-to-edge,
  edge-to-edge distances along column/grid lines) - describe what each shape means
- the door tag symbol and window tag symbol (e.g. a shield/pentagon shape used to mark door
  and window reference numbers on plans) - describe the shape and what it marks
- the elevation-view marker (labeled something like "ชื่อรูปด้าน" / "elevation") and the
  section-cut marker (labeled something like "ชื่อรูปตัดอาคาร" / "section") - these are TWO
  DIFFERENT symbols; read each symbol's OWN caption text on the page to decide which is which,
  do NOT assume by shape or by which one you saw first. State which caption you read for each.
- the north-direction symbol
- the material hatch patterns (e.g. brick/concrete/steel/soil/finished-wood/glass) - for EACH
  one, look at its OWN box individually and describe ONLY what you see in that specific box
  (dots vs diagonal lines vs crossed/woven lines vs solid fill vs wavy grain) - do not reuse the
  same description across two different materials; if two hatch boxes look genuinely identical,
  say so explicitly instead of inventing a difference
- any other general drawing symbols shown (e.g. slope direction arrows)
If this page has no such symbol-legend section, say so explicitly rather than guessing.

Respond with ONLY JSON: {"sheets": [{"code": "A-01", "title": "ผังบริเวณ - แผนที่สังเขป", "discipline": "Architecture"}, ...],
"drawing_notation": {"dimension_symbols": "...", "door_tag_symbol": "...", "window_tag_symbol": "...",
"section_marker": "...", "elevation_marker": "...", "north_symbol": "...",
"material_hatches": {"concrete": "...", "steel": "...", "soil": "...", "wood": "...", "brick": "...", "glass": "..."},
"other_symbols": ["..."]}, "notes": "..."}"""

SPEC_PROMPT = """This is the specification/legend page (ข้อกำหนดและรายการประกอบแบบ) from a Thai
construction PDF - the single most important reference page for takeoff. Extract:
- the masonry/brick rule (e.g. default wall type, when it differs)
- every wall type code and its description (e.g. ผ1, ผ2, ผ3)
- every floor type code and its description (e.g. F1, F2, F3, F4)
- every door category code and window category code shown (general D/W legend, not the detailed door-by-door schedule)
- where eave/fascia (ฝ้าชายคา/เชิงชาย) detail is said to be found (e.g. "see section A-A, B-B")
- any other numbered general notes that look important for quantity takeoff
Respond with ONLY JSON: {"brick_rule":"...","wall_types":{"ผ1":"..."},"floor_types":{"F1":"..."},"door_categories":{"...":"..."},"window_categories":{"...":"..."},"eave_detail_location":"...","other_notes":["..."]}"""

TITLEBLOCK_PROMPT = """This is a tight crop of the bottom-right corner of one sheet from a Thai
construction PDF, containing ONLY the "DWG. NO." cell (plus DATE/TOTAL nearby). Read the
DWG. NO. value exactly as printed (e.g. "A-04", "S-02", "E-01") - it is short, a letter
prefix plus a number, NOT a long license-number-style code. If illegible, say "illegible".
Respond with ONLY JSON: {"dwg_no": "A-04"}"""

# Every one of these keys is also a field (or material_hatches/other_symbols sub-entry) in
# the drawing_notation dict produced by INDEX_PROMPT - keep the two lists in sync.
SYMBOL_BBOX_KEYS = [
    "dimension_symbols", "door_tag_symbol", "window_tag_symbol", "section_marker",
    "elevation_marker", "north_symbol", "hatch_concrete", "hatch_steel", "hatch_soil",
    "hatch_wood", "hatch_brick_wall_plan", "hatch_glass_wall_plan", "hatch_glass_section",
    "slope_arrow",
]

BBOX_PROMPT = """This is the drawing-notation symbol-legend page (รายการสัญลักษณ์แบบสถาปัตยกรรม)
from a Thai construction PDF. For EACH of the keys below, if its symbol/icon is present on
this page, give the bounding box of JUST that symbol's graphic (not its caption text, not the
whole table row - a tight-ish box around the drawn icon itself, with a little margin since a
human will fine-tune the numbers afterward) as a fraction of the FULL PAGE width/height
(0.0 to 1.0, x0<x1, y0<y1), plus a short 2-4 word Thai label for display.

Keys:
- dimension_symbols: the circle/X-mark distance-reference icons together (one box covering
  all three example lines: center-to-center, center-to-edge, edge-to-edge)
- door_tag_symbol: the circle containing 'ป' + a number
- window_tag_symbol: the hexagon containing 'น' + a number
- section_marker: the single triangle+A-NO flag captioned "ชื่อรูปตัดอาคาร"
- elevation_marker: the X-cross 4-arrow symbol captioned "ชื่อรูปด้าน"
- north_symbol: the compass rose
- hatch_concrete, hatch_steel, hatch_soil, hatch_wood, hatch_brick_wall_plan,
  hatch_glass_wall_plan, hatch_glass_section: each is ONE small hatch-pattern box only
  (not the material name text next to it) - read each box's OWN pattern individually,
  do not assume two boxes match
- slope_arrow: the SLOPE 1:200 arrow

Omit a key entirely if its symbol is not present on this page - never guess a box for
something you don't see.

Respond with ONLY JSON: {"boxes": [{"key": "door_tag_symbol", "label_th": "เลขอ้างอิงประตู", "bbox_pct": [0.62, 0.24, 0.68, 0.30]}, ...]}"""


API_BASE64_LIMIT = 10_485_760  # the API's actual limit is on the base64-ENCODED size, not raw bytes
MAX_PNG_BYTES = int(API_BASE64_LIMIT * 3 / 4 * 0.9)  # base64 inflates by 4/3 - back that out, plus margin


def detect_symbol_boxes(client, doc, page_index):
    """Ask the model to propose a bounding box for each known symbol on the notation-legend
    page. Boxes are approximate by design - a human fine-tunes bbox_pct numbers directly in
    the saved JSON afterward (see --recrop-only), no drag-and-drop UI needed."""
    png = render_page(doc, page_index)
    data, usage = call_single(client, png, BBOX_PROMPT, max_tokens=2000)
    return data.get("boxes", []), usage


def render_symbol_boxes_overlay(doc, page_index, boxes, out_path, dpi=350):
    """Draw every proposed box + a number label on one copy of the page, so a human can see
    every position at a glance before deciding which ones need nudging. Saved as one PNG."""
    img = Image.open(io.BytesIO(doc[page_index].get_pixmap(dpi=dpi).tobytes("png"))).convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)
    for i, b in enumerate(boxes, 1):
        x0, y0, x1, y1 = b["bbox_pct"]
        px0, py0, px1, py1 = int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)
        draw.rectangle([px0, py0, px1, py1], outline="red", width=4)
        draw.text((px0, max(0, py0 - 28)), f"{i}. {b.get('label_th', b['key'])}", fill="red")
    img.save(out_path)


def crop_symbol_boxes(doc, page_index, boxes, out_dir, dpi=350):
    """Crop each box (as currently written in bbox_pct - possibly hand-edited) into its own
    small PNG under out_dir/symbols/<key>.png. Returns {key: relative_path}."""
    symbols_dir = os.path.join(out_dir, "symbols")
    os.makedirs(symbols_dir, exist_ok=True)
    img = Image.open(io.BytesIO(doc[page_index].get_pixmap(dpi=dpi).tobytes("png")))
    w, h = img.size
    paths = {}
    for b in boxes:
        x0, y0, x1, y1 = b["bbox_pct"]
        crop = img.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))
        rel_path = os.path.join("symbols", f"{b['key']}.png")
        crop.save(os.path.join(out_dir, rel_path))
        paths[b["key"]] = rel_path.replace("\\", "/")
    return paths


def get_symbol_description(dn, key):
    """Look up the existing AI text description for a SYMBOL_BBOX_KEYS entry from the
    drawing_notation dict already produced by INDEX_PROMPT."""
    if key.startswith("hatch_"):
        return dn.get("material_hatches", {}).get(key[len("hatch_"):], "-")
    if key == "slope_arrow":
        for note in dn.get("other_symbols", []):
            if "slope" in note.lower() or "ลาด" in note:
                return note
        return "-"
    return dn.get(key, "-")


def render_page(doc, index, dpi=250):
    """Render at high DPI for legibility; only shrink if the PNG would exceed the
    API's size limit (e.g. a site-plan page with a huge embedded photo) — never
    blanket-lower DPI for every page just to fix one oversized page.

    NOTE: the API checks the size of the base64-ENCODED string (4/3 larger than
    raw bytes), not the raw PNG size — a raw-byte-only check silently lets an
    oversized image through. MAX_PNG_BYTES already accounts for this inflation."""
    png = doc[index].get_pixmap(dpi=dpi).tobytes("png")
    while len(png) > MAX_PNG_BYTES and dpi > 72:
        dpi = int(dpi * 0.8)
        png = doc[index].get_pixmap(dpi=dpi).tobytes("png")
    return png


def render_titleblock_strip(doc, index, dpi=250):
    """Crop ONLY the DWG. NO. cell — verified by eye at (right 25% width, bottom
    10% height) of the page, e.g. shows exactly "A - 04" with nothing else
    ambiguous nearby (the architect/engineer license numbers sit elsewhere in
    the title block, not in this corner) — do not widen this crop blindly."""
    page = doc[index]
    img = Image.open(io.BytesIO(page.get_pixmap(dpi=dpi).tobytes("png")))
    w, h = img.size
    strip = img.crop((int(w * 0.75), int(h * 0.90), w, h))
    buf = io.BytesIO()
    strip.save(buf, format="PNG")
    return buf.getvalue()


def b64_image_block(png_bytes):
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                          "data": base64.standard_b64encode(png_bytes).decode("ascii")}}


def _parse_json(text):
    cleaned = text.strip().removeprefix("```json").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"_raw": text}


def call_single(client, png_bytes, prompt, max_tokens=6000, model=STRONG_MODEL):
    # streaming avoids the SDK's "operation may take >10min" error on large max_tokens
    # (adaptive thinking can burn the whole budget before any output text appears)
    with client.messages.stream(
        model=model, max_tokens=max_tokens,
        messages=[{"role": "user", "content": [b64_image_block(png_bytes), {"type": "text", "text": prompt}]}],
    ) as stream:
        resp = stream.get_final_message()
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    return _parse_json(text), resp.usage


def extract_titleblocks_batch(client, doc):
    reqs = []
    for i in range(len(doc)):
        png = render_titleblock_strip(doc, i)
        reqs.append(Request(custom_id=f"page-{i+1}", params=MessageCreateParamsNonStreaming(
            model=MODEL, max_tokens=100,
            messages=[{"role": "user", "content": [b64_image_block(png), {"type": "text", "text": TITLEBLOCK_PROMPT}]}],
        )))
    batch = client.messages.batches.create(requests=reqs)
    print(f"  titleblock batch: {batch.id} ({len(reqs)} pages)")
    while True:
        batch = client.messages.batches.retrieve(batch.id)
        if batch.processing_status == "ended":
            break
        time.sleep(10)

    result, in_tok, out_tok = {}, 0, 0
    for r in client.messages.batches.results(batch.id):
        if r.result.type != "succeeded":
            continue
        msg = r.result.message
        in_tok += msg.usage.input_tokens
        out_tok += msg.usage.output_tokens
        text = next((b.text for b in msg.content if b.type == "text"), "{}")
        page_num = int(r.custom_id.split("-")[1])
        result[page_num] = _parse_json(text).get("dwg_no", "illegible")
    return result, in_tok, out_tok


def load_foundation_data(md_path):
    """Extract the embedded ```json block from foundation_data.md — same pattern as schema_loader.py."""
    text = open(md_path, encoding="utf-8").read()
    match = re.search(r"```json\n(.*?)\n```", text, re.S)
    if not match:
        raise ValueError(f"no ```json fenced block found in {md_path}")
    return json.loads(match.group(1))


def render_markdown(data, project_label):
    pi = data["project_info"]
    si = data["site_info"]
    ls = data["legend_and_specs"]
    mismatches = data["sheet_index_mismatches"]

    lines = [f"# ข้อมูลพื้นฐานโครงการ: {project_label}", ""]
    lines.append(f"> อ่านจากไฟล์ `{data['source_pdf']}` โดยไพน้อย (Claude Haiku 4.5) — "
                  "**ยังไม่มีคนตรวจสอบ** แก้ไขก้อน JSON ด้านล่างได้โดยตรงถ้าพบข้อผิดพลาด")
    lines.append("")

    lines.append("## สรุปสำหรับอ่าน (คนอ่านส่วนนี้)")
    lines.append("")
    lines.append("### ข้อมูลโครงการ")
    for key, label in [("project_name", "ชื่อโครงการ"), ("owner", "เจ้าของ"), ("address", "ที่อยู่"),
                        ("permit_no", "ใบอนุญาตเลขที่"), ("book_no", "เล่มที่"), ("permit_date", "วันที่")]:
        lines.append(f"- {label}: {pi.get(key, '-')}")
    lines.append("")

    lines.append("### ข้อมูลที่ดิน/ผังบริเวณ")
    lines.append(f"- โฉนดเลขที่: {si.get('title_deed_no', '-')}")
    lines.append(f"- เลขที่ดินอ้างอิง: {si.get('land_parcel_ref', '-')}")
    lines.append(f"- องค์ประกอบที่พบในผัง: {', '.join(si.get('site_elements_present', [])) or '-'}")
    lines.append("")

    lines.append("### สารบัญแบบ (ตรวจสอบกับ title block จริงของแต่ละหน้าแล้ว)")
    lines.append("| รหัส | ชื่อแผ่น | หมวด |")
    lines.append("|---|---|---|")
    for s in data["sheet_index_declared"]:
        lines.append(f"| {s.get('code', '-')} | {s.get('title', '-')} | {s.get('discipline', '-')} |")
    lines.append("")
    if mismatches:
        lines.append(f"⚠️ **พบ {len(mismatches)} จุดที่ title block จริงไม่ตรงกับสารบัญที่ประกาศไว้ — ต้องตรวจสอบ:**")
        for m in mismatches:
            lines.append(f"- หน้า {m['page']}: title block บอกว่า \"{m['title_block_says']}\" ({m['note']})")
    else:
        lines.append("✅ title block ทุกหน้าตรงกับสารบัญที่ประกาศไว้ ไม่พบจุดขัดแย้ง")
    lines.append("")

    dn = data.get("drawing_notation", {})
    boxes = data.get("notation_symbol_boxes", [])
    overview_img = data.get("notation_symbol_overview_image")
    lines.append("### สัญลักษณ์แบบ (ใช้ตีความหน้าอื่นๆ ในชุดแบบนี้ทั้งหมด)")
    if dn:
        lines.append("> ⚠️ **AI อ่านรูปทรง/ลาย hatch ผิดพลาดซ้ำๆในหลายรอบที่ผ่านมา (สลับคู่กัน, อ่านรูปทรงผิด) "
                      "— ดูรูปจริงเทียบกับคำอธิบายเสมอ ก่อนติ๊กยืนยัน**")
        lines.append("")
        if overview_img:
            lines.append("**ภาพรวมตำแหน่งกรอบที่ไพน้อยเสนอ (เลขกำกับตรงกับหัวข้อด้านล่าง):**  ")
            lines.append(f"![overview]({overview_img})")
            lines.append("")
            lines.append("> ถ้ากรอบไหนเพี้ยน แก้ตัวเลข `bbox_pct` ของสัญลักษณ์นั้นในก้อน JSON ด้านล่างโดยตรง "
                          "(`[x0, y0, x1, y1]` เป็นสัดส่วนของหน้าเต็ม 0.0-1.0) แล้วรัน "
                          "`python extract_foundation_data.py <pdf> --index-page N --out-path <ไฟล์นี้> --recrop-only` "
                          "เพื่อครอปภาพใหม่โดยไม่ต้องเรียก API ซ้ำ")
            lines.append("")

        box_by_key = {b["key"]: b for b in boxes}
        for i, key in enumerate(SYMBOL_BBOX_KEYS, 1):
            b = box_by_key.get(key)
            if not b:
                continue
            desc = get_symbol_description(dn, key).replace("\n", " ")
            lines.append(f"#### {i}. {b.get('label_th', key)}")
            if b.get("image_path"):
                lines.append(f"![{key}]({b['image_path']})")
            lines.append(f"- AI อ่านว่า: {desc}")
            lines.append("- [ ] ถูกต้อง")
            lines.append("- [ ] แก้ไข: _____ (พิมพ์ \"ตัดออก\" = ไม่ต้องใช้สัญลักษณ์นี้เลย)")
            lines.append("")

        if dn.get("other_symbols"):
            leftover = [s for s in dn["other_symbols"] if "slope" not in s.lower() and "ลาด" not in s]
            if leftover:
                lines.append("- สัญลักษณ์อื่น (ไม่มีกรอบเสนอ):")
                for sym in leftover:
                    lines.append(f"  - {sym}")
                lines.append("")
    else:
        lines.append("- ไม่พบส่วนสัญลักษณ์แบบบนหน้าสารบัญของโปรเจกต์นี้")
    lines.append("")

    lines.append("### ข้อกำหนดสำคัญ (จากหน้าสเปค)")
    lines.append(f"- กฎก่ออิฐ: {ls.get('brick_rule', '-')}")
    lines.append("- ประเภทผนัง: " + "; ".join(f"{k}={v}" for k, v in ls.get("wall_types", {}).items()))
    lines.append("- ประเภทพื้น: " + "; ".join(f"{k}={v}" for k, v in ls.get("floor_types", {}).items()))
    lines.append(f"- ตำแหน่งรายละเอียดฝ้าชายคา/เชิงชาย: {ls.get('eave_detail_location', '-')}")
    if ls.get("other_notes"):
        lines.append("- หมายเหตุอื่น:")
        for note in ls["other_notes"]:
            lines.append(f"  - {note}")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## ข้อมูลดิบ (ไพน้อยอ่านส่วนนี้ — แก้ไขตรงนี้ถ้าต้องแก้ ไม่มีไฟล์ .json แยกอีก)")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(data, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf_path")
    ap.add_argument("--project-label", default=None, help="human-readable project name for the .md title")
    # ไม่มี default -- เลขหน้าปก/ผังบริเวณ/สารบัญ/สัญลักษณ์ เป็นเลย์เอาต์เฉพาะของแต่ละโปรเจกต์ ไม่มี
    # ความหมายร่วมข้ามโปรเจกต์ (เคยมี default=1/2/3/4 ตรงกับ newhouse พอดี ทำให้รันกับ PDF อื่นแล้วอ่าน
    # หน้าผิดแบบเงียบๆ โดยไม่ error) -- ต้องระบุทุกครั้งหลังไล่ดูสารบัญ/หน้าจริงของโปรเจกต์นั้นก่อน
    # (บังคับเฉพาะโหมดปกติ -- --recrop-only ใช้แค่ --index-page เดียว เช็คแยกด้านล่าง)
    ap.add_argument("--cover-page", type=int, default=None)
    ap.add_argument("--site-page", type=int, default=None)
    ap.add_argument("--index-page", type=int, default=None)
    ap.add_argument("--spec-page", type=int, default=None)
    ap.add_argument("--force", action="store_true", help="re-extract even if foundation_data.md exists")
    ap.add_argument("--out-path", default=None,
                     help="override the output .md path (e.g. for a side-by-side test run) "
                          "instead of the default <project_root>/foundation_data.md")
    ap.add_argument("--recrop-only", action="store_true",
                     help="reload an existing foundation_data.md, re-crop the notation symbol "
                          "images from its (possibly hand-edited) bbox_pct numbers, and rewrite "
                          "the file - no API calls, use this after nudging a box's coordinates")
    args = ap.parse_args()

    if args.recrop_only:
        if args.index_page is None:
            ap.error("--recrop-only ต้องระบุ --index-page ด้วย (เลขหน้าสารบัญ/สัญลักษณ์ของโปรเจกต์นี้)")
    elif None in (args.cover_page, args.site_page, args.index_page, args.spec_page):
        ap.error("ต้องระบุ --cover-page --site-page --index-page --spec-page ครบทั้ง 4 ค่า "
                  "(ไล่ดูหน้าจริงของโปรเจกต์นี้ก่อน ไม่มี default เพราะแต่ละโปรเจกต์เรียงหน้าไม่เหมือนกัน)")

    # project root = the folder that CONTAINS the "PDF" subfolder the file sits in
    # (project/new house/PDF/xxx.pdf -> project/new house/foundation_data.md),
    # never the PDF's own subfolder.
    pdf_dir = os.path.dirname(os.path.abspath(args.pdf_path))
    project_root = os.path.dirname(pdf_dir) if os.path.basename(pdf_dir).upper() == "PDF" else pdf_dir
    out_path = args.out_path or os.path.join(project_root, "foundation_data.md")

    if args.recrop_only:
        data = load_foundation_data(out_path)
        doc = fitz.open(args.pdf_path)
        out_dir = os.path.dirname(os.path.abspath(out_path))
        boxes = data.get("notation_symbol_boxes", [])
        paths = crop_symbol_boxes(doc, args.index_page - 1, boxes, out_dir)
        for b in boxes:
            b["image_path"] = paths.get(b["key"])
        overview_rel = os.path.join("symbols", "_proposal_overview.png")
        render_symbol_boxes_overlay(doc, args.index_page - 1, boxes, os.path.join(out_dir, overview_rel))
        data["notation_symbol_overview_image"] = overview_rel.replace("\\", "/")
        project_label = args.project_label or data["project_info"].get("project_name", "ไม่ทราบชื่อโครงการ")
        markdown = render_markdown(data, project_label)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        print(f"Recropped {len(boxes)} symbol(s) from edited bbox_pct values: {out_path}")
        return

    if os.path.exists(out_path) and not args.force:
        print(f"foundation_data.md already exists at {out_path} — loading it, NOT re-reading the PDF.")
        data = load_foundation_data(out_path)
        print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
        return

    client = anthropic.Anthropic()
    doc = fitz.open(args.pdf_path)
    strong_in = strong_out = 0
    haiku_in = haiku_out = 0

    print("Stage 0: extracting cover / site / index / spec pages...")
    cover, u1 = call_single(client, render_page(doc, args.cover_page - 1), COVER_PROMPT)
    strong_in += u1.input_tokens; strong_out += u1.output_tokens
    site, u2 = call_single(client, render_page(doc, args.site_page - 1), SITE_PROMPT)
    strong_in += u2.input_tokens; strong_out += u2.output_tokens
    index_declared, u3 = call_single(client, render_page(doc, args.index_page - 1), INDEX_PROMPT)
    strong_in += u3.input_tokens; strong_out += u3.output_tokens
    spec, u4 = call_single(client, render_page(doc, args.spec_page - 1), SPEC_PROMPT)
    strong_in += u4.input_tokens; strong_out += u4.output_tokens

    print("Stage 0: detecting notation symbol positions...")
    boxes, u5 = detect_symbol_boxes(client, doc, args.index_page - 1)
    strong_in += u5.input_tokens; strong_out += u5.output_tokens

    print("Stage 0: reading every page's own title block (cross-check)...")
    titleblocks, haiku_in, haiku_out = extract_titleblocks_batch(client, doc)

    declared_codes = [s.get("code") for s in index_declared.get("sheets", [])]
    mismatches = [
        {"page": page_num, "title_block_says": dwg_no, "note": "not found in declared index list"}
        for page_num, dwg_no in sorted(titleblocks.items())
        if dwg_no not in declared_codes and dwg_no != "illegible"
    ]

    out_dir = os.path.dirname(os.path.abspath(out_path))
    symbol_paths = crop_symbol_boxes(doc, args.index_page - 1, boxes, out_dir)
    for b in boxes:
        b["image_path"] = symbol_paths.get(b["key"])
    overview_rel = os.path.join("symbols", "_proposal_overview.png")
    render_symbol_boxes_overlay(doc, args.index_page - 1, boxes, os.path.join(out_dir, overview_rel))

    foundation_data = {
        "source_pdf": os.path.basename(args.pdf_path),
        "project_info": cover,
        "site_info": site,
        "sheet_index_declared": index_declared.get("sheets", []),
        "sheet_index_verified": {str(k): v for k, v in sorted(titleblocks.items())},
        "sheet_index_mismatches": mismatches,
        "drawing_notation": index_declared.get("drawing_notation", {}),
        "notation_symbol_boxes": boxes,
        "notation_symbol_overview_image": overview_rel.replace("\\", "/"),
        "legend_and_specs": spec,
    }

    project_label = args.project_label or cover.get("project_name") or "ไม่ทราบชื่อโครงการ"
    markdown = render_markdown(foundation_data, project_label)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    # strong-model calls (Sonnet 5) are live, not batched; the title-block batch (Haiku) gets the 50% discount
    cost = (strong_in * 2.00 + strong_out * 10.00) / 1_000_000 + (haiku_in * 1.00 + haiku_out * 5.00) / 1_000_000 * 0.5
    print(f"\nSaved: {out_path}")
    print(f"Mismatches between declared index and actual title blocks: {len(mismatches)}")
    print("(see foundation_data.md for details - Thai text here can crash Windows console encoding)")
    print(f"cost: ${cost:.5f} (~{cost*36.5:.2f} THB)")


if __name__ == "__main__":
    main()
