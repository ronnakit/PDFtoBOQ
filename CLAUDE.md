# CLAUDE.md

คำแนะนำสำหรับ Claude Code เมื่อทำงานในรีโพนี้

## โครงการนี้คืออะไร

**PDFtoBOQ** — เว็บแอปจริงที่ถอดแบบก่อสร้าง (PDF) เป็น BOQ (Bill of Quantities) อัตโนมัติ ใช้ AI agent ชื่อ "ไพน้อย" ทำงาน*ภายใน*แอป — repo: `github.com/ronnakit/PDFtoBOQ.git` (private, branch `main`)

**นี่คือรีโพโค้ดที่ deploy จริง** ไม่ใช่รีโพเอกสารพิมพ์เขียว — เอกสารขั้นตอนถอดแบบ/มาตรฐาน/ประวัติการตัดสินใจเชิงธุรกิจอยู่ที่ [`docs/markdown-app/`](./docs/markdown-app/) (ย้ายมารวมที่นี่ 2569-09-02 จากรีโพแยกต่างหากที่เคยใช้คู่ขนาน — ดู `LOG.md` §02 กันยายน 2569 รอบดึก สำหรับเหตุผล)

## สถาปัตยกรรม

```
frontend/index.html         -- SPA เดียว, drag/drop PDF -> POST /api/takeoff -> แสดงผล
app_server.py                -- http.server ธรรมดา (ไม่มีเฟรมเวิร์ก), route ทั้งหมด
python/pipeline_orchestrator.py  -- เรียกทุกหมวดที่มี, ประกอบผล, เขียน confirm_boq.json
python/extract_footing_boq.py    -- ฐานราก (โค้ดล้วน + AI vision fallback อ่านตารางสเปคที่ flatten)
python/extract_pier_column_boq.py -- ตอม่อ-เสา (โค้ดล้วน)
python/extract_beam_boq.py       -- คาน (สเปคโค้ดล้วน, เรขาคณิต AI vision จำกัดขอบเขต) -- status "partial_coverage" เสมอ
python/extract_roof_boq.py       -- หลังคาเหล็ก (AI vision เป็นวิธีหลัก อ่านตารางที่ผู้ออกแบบสรุปไว้เอง)
python/extract_floor_boq.py      -- ยังไม่ implement (ลองแล้วไม่ผ่าน ดู pipeline_orchestrator.py หมวด floor)
python/grid_utils.py             -- โมดูลกลาง: หาแผ่นแบบจากชื่อ, หาเส้นกริด+สเกล, วัดขนาดจาก vector fill
python/thai_font_fix.py          -- แก้ฟอนต์ไทยเพี้ยนจาก AutoCAD print-to-PDF
python/ai_vision_fallback.py     -- wrapper เรียก Anthropic API (ดู "AI vision" ด้านล่าง)
```

สคริปต์อื่นใน `python/` (`clean_dxf.py`, `classify_layers.py`, `pynoi.py`, `extract_foundation_data.py` ฯลฯ) เป็นโค้ดทดลอง/อ้างอิงจากช่วงพัฒนาก่อนหน้า **ไม่ได้ต่อเข้า pipeline ปัจจุบัน** — อย่าสมมติว่าทำงานได้จนกว่าจะตรวจสอบ

## AI vision (สำคัญ — อ่านก่อนแก้โค้ดที่เรียก AI)

- **เป้าหมายผลิตภัณฑ์จริง: รันได้ 100% อัตโนมัติด้วย free-tier AI เท่านั้น ไม่มีต้นทุนต่อครั้ง** (ตัดสินใจแล้ว ดู `BACKLOG.md` §ตัดสินใจธุรกิจ)
- **สถานะปัจจุบัน (ชั่วคราว):** ใช้ Anthropic API key แบบ paid ที่เจ้าของโปรเจกต์ให้มาทดสอบ จนกว่าเครดิตจะหมดแล้วจะเปลี่ยน provider — key อยู่ใน `.env` (`ANTHROPIC_API_KEY=...`, gitignore แล้ว **ห้าม commit เด็ดขาด**) ตรวจสอบก่อน commit ทุกครั้งด้วย `git diff --cached | grep -i "sk-ant-api"`
- โค้ดที่ผูกกับ Anthropic SDK จำกัดอยู่แค่ 2 ฟังก์ชันใน `ai_vision_fallback.py` (`call_vision_json`/`_get_client`) เพื่อสลับ provider ได้ง่ายเมื่อถึงเวลา — ถ้าเห็นเครดิตหมด/ผู้ใช้บอกว่าจะเปลี่ยน key ให้เช็คกับเจ้าของโปรเจกต์ก่อนสมมติว่า key เดิมยังใช้ได้
- **AI vision เป็น fallback สำหรับจุดที่โค้ดอ่านไม่ได้จริงๆ เท่านั้น** (ตรวจก่อนด้วย `page.get_text()` ว่างในโซนที่ควรมีตาราง = สัญญาณว่าถูก flatten เป็น vector หรือเป็นภาพ raster ฝัง) ไม่ใช่ยิงทุกหน้าเข้า AI
- โมเดล default คือ Haiku (คุ้มต้นทุน) — บางงาน (เช่น แยกสีเส้นคานในคานเรขาคณิต) พิสูจน์แล้วว่าต้องใช้ Sonnet ถึงจะแม่นพอ ดู `extract_beam_boq.py`

## ข้อตกลงในการทำงาน (เหมือนรีโพเอกสารพิมพ์เขียว)

- **ภาษาที่ใช้สื่อสาร:** ตอบกลับผู้ใช้เป็นภาษาไทยเสมอ โค้ด/path/ศัพท์เทคนิคเป็นภาษาอังกฤษได้ตามปกติ
- **การ commit/push:** สร้าง commit หรือ push ให้เฉพาะเมื่อผู้ใช้ขอเท่านั้น
- **LOG.md:** บันทึกการตัดสินใจ/งานสำคัญที่กระทบหลายไฟล์ (เรียงเก่า→ใหม่ ต่อท้ายไฟล์ — **ต่างจากธรรมเนียมของรีโพเอกสารพิมพ์เขียวที่เรียงใหม่→เก่า** ดูรูปแบบเดิมในไฟล์ก่อนเขียนเพิ่ม)
- **BACKLOG.md:** รายการคำถาม/งานค้าง
- **ห้ามฝังค่าที่ยืนยันเฉพาะโปรเจกต์เป็นค่าคงที่ในสคริปต์** — สูตรคำนวณ/ค่าคงที่ทางฟิสิกส์ของวัสดุ (น้ำหนักเหล็ก กก./เมตร, ความหนาแน่นเหล็ก ฯลฯ) อยู่ในโค้ดได้ปกติ แต่ข้อมูลยืนยันเฉพาะโปรเจกต์ต้องอยู่ใน `project/<ชื่อโปรเจกต์>/` เท่านั้น
- **ทุกค่าที่คำนวณต้องมีสถานะ/แหล่งที่มากำกับเสมอ** (`computed`/`partial`/`not_implemented` ฯลฯ) — ห้ามคืนตัวเลขเปล่าๆ หรืออ้างว่า "สำเร็จ 100%" ถ้าไม่ใช่ทุกหมวดคำนวณได้จริง (ดู `app_server.py`'s `build_takeoff_summary()` เป็นตัวอย่าง)
- **ทดสอบผ่าน HTTP จริงก่อนถือว่าเสร็จ** — อัปโหลดไฟล์จริงผ่าน `/api/takeoff`, เช็ค response, เช็ค render หน้าเว็บใน browser ไม่ใช่แค่รัน `extract_*.py` แบบ standalone แล้วจบ

## โครงสร้างโฟลเดอร์ต่อโปรเจกต์

`project/<ชื่อโปรเจกต์>/` — สร้างอัตโนมัติตอนอัปโหลดไฟล์ผ่าน `/api/takeoff` (ดู `app_server.py`'s `handle_takeoff_process()`):
- `PDF/` — ไฟล์ต้นฉบับที่อัปโหลด
- `markdown/confirm_boq.json` — ผลลัพธ์จาก pipeline (structured, มี status ต่อค่า)
- `boq/` — รายงานฉบับสมบูรณ์ (ถ้ามีการสร้าง)
