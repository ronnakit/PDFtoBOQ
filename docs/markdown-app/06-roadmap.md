# Roadmap

> ⚠️ **ปรับทิศทางใหญ่ (2569-08-24):** งานวิจัยตลาด ([01-market-competitors.md](./01-market-competitors.md)) พบว่า PDF คือรูปแบบไฟล์ที่ผู้รับเหมาได้รับจริงมากที่สุด (ไม่ใช่ DWG) และ pain point ที่ใหญ่ที่สุดคือ "หาสเกลที่เชื่อถือได้ไม่ได้จนต้อง print กระดาษ" — เปลี่ยนเส้นทางไปเปิดตัว **PDF Takeoff MVP** ([10-pdf-mvp-spec.md](./10-pdf-mvp-spec.md)) เป็นเส้นทางหารายได้เร็วที่สุดแทน งาน DWG/DXF (Phase 1 เดิม) ยังมีค่าและทำต่อ แต่ไม่ใช่เส้นทางแรกที่จะสร้างรายได้แล้ว

## Phase 0 — พิมพ์เขียว (เสร็จแล้วเป็นส่วนใหญ่)
- เขียนเอกสารชุดนี้ให้ครบ (มาร์เก็ต/การเงิน/สถาปัตยกรรม)
- ตัดสินใจชื่อโครงการ (ดู [BACKLOG.md](./BACKLOG.md))
- ยืนยันสิทธิ์การใช้ข้อมูลราคากลางภาครัฐเชิงพาณิชย์

## Phase 1 (เส้นทางใหม่ — เร็วที่สุด) — PDF Takeoff MVP + Founding Member 100 คนแรก
- สร้างเว็บแอปตาม [10-pdf-mvp-spec.md](./10-pdf-mvp-spec.md): upload PDF → calibrate scale → วัดเส้น/พื้นที่/นับจำนวน → export Excel — **ไม่มี AI ในเวอร์ชันแรก**
- เปิดขายราคา Founding Member ตามกลไกใน [11-founding-member-pricing.md](./11-founding-member-pricing.md)
- ช่องทาง: เครือข่าย RPS Group เอง + กลุ่ม Facebook/LINE ผู้รับเหมารายย่อย
- ใช้หมวดหมู่จาก [04-category-schema.md](./04-category-schema.md) ได้ทันที (format-agnostic ไม่ผูกกับ DWG)

## Phase 1b (ขนาน — ไม่หยุด) — DWG/DXF Prototype จาก Ground Truth
- งานที่ทำไปแล้วมาก: `pynoi_parser.py`, `classify_layers.py`, `clean_dxf.py` (Layer Exclusion, Duplicate Purge, font/style cleanup) ตาม [ground-truth-newhouse-2569.md](./ground-truth-newhouse-2569.md)
- ยังค้าง: Bounding Box Filter (แก้ปัญหา WALL layer), เกณฑ์ "หลักฐานสนับสนุน" เป็นโค้ดจริง ([07-drawing-signal-vs-noise.md §14](./07-drawing-signal-vs-noise.md))
- ยังมีค่าสำหรับลูกค้าที่มีไฟล์ CAD จริง (เช่น RPS เอง) แต่ไม่ใช่เส้นทางหารายได้แรกอีกต่อไป — ทำต่อแบบไม่เร่งรีบ

## Phase 2 — เพิ่ม AI เข้า PDF MVP (ให้ Founding Member ใช้ฟรีตามสัญญา)
- Auto-detect สเกลจากข้อความในแบบ
- Auto-recognize เส้นผนัง/ประตู/หน้าต่างจาก vector data ของ PDF (ต่อยอด logic "สัญญาณ vs ขยะ" จากงาน DWG ได้ ถ้า PDF มี vector จริงไม่ใช่ภาพสแกน)
- Auto-categorize + ราคาอัตโนมัติจาก price list
- ⚠️ **ไม่ตั้งกำหนดเวลาชัดเจนให้ Phase นี้ตอนขายรอบแรก** — ประสบการณ์จริงจากงาน DWG แสดงให้เห็นว่า AI feature ประเภทนี้ใช้เวลานานกว่าคาดมาก (ดู [11-founding-member-pricing.md §4](./11-founding-member-pricing.md#4-เชื่อมกับความยากง่ายของการสร้าง-ไพน้อย-ตามที่เจ้าของโปรเจกต์ตั้งข้อสังเกต))

## Phase 3 — ขยาย Distribution + Subscription
- เปิดราคาสำหรับลูกค้าหลัง 100 คนแรก (subscription หรือราคาครั้งเดียวที่สูงขึ้น)
- พิจารณา credit top-up (500/1,000/2,000 บาท) สำหรับงาน DWG concierge/self-serve ที่ยังมีอยู่ขนาน
- เริ่มพิจารณาการเชื่อมกลับเข้า Data Flywheel ของรักบ้าน

## Phase 4 (Stretch) — 3D Generation
- แปลง Vector 2D เป็น 3D component (SketchUp/Revit) — ยังไม่เริ่มก่อนมีรายได้จาก BOQ อย่างเดียวแล้ว เพื่อไม่ให้ scope creep ดึงรายได้ให้ช้าลง
