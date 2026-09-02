# PDFtoBOQ

ถอดแบบก่อสร้าง (PDF) เป็น BOQ (Bill of Quantities) อัตโนมัติ ด้วย AI agent "ไพน้อย"

## รันเว็บแอป

```bash
pip install -r python/requirements.txt
python app_server.py
```

เปิด `http://localhost:8000` — ลากไฟล์ PDF แบบก่อสร้างวางได้เลย

ต้องมีไฟล์ `.env` ที่ root พร้อม `ANTHROPIC_API_KEY=...` (ดู "AI vision" ใน [CLAUDE.md](./CLAUDE.md) — ห้าม commit ไฟล์นี้เด็ดขาด อยู่ใน `.gitignore` แล้ว)

## สถานะปัจจุบัน (2569-09-02)

ถอดได้ 3/5 หมวดโครงสร้างแบบคำนวณเต็ม (ฐานราก, ตอม่อ-เสา, หลังคาเหล็ก) + 1 หมวดบางส่วน (คาน — ครอบคลุมเฉพาะช่วงระหว่างเสาที่ยืนยันแล้ว) — พื้นยังไม่ implement (ลองแล้วพบว่าวิธีที่มีคลาดเคลื่อนสูงเกินจะปล่อย ดู `LOG.md`)

ทุกค่าที่คำนวณมีสถานะกำกับเสมอ (`computed`/`partial`/`not_implemented`) แสดงในหน้าเว็บแยกรายหมวด — ไม่มีการอ้าง "สำเร็จ 100%" ถ้าไม่ได้ครบจริงทุกหมวด

## เอกสาร

- [CLAUDE.md](./CLAUDE.md) — สถาปัตยกรรม, ข้อตกลงการทำงาน, วิธีจัดการ AI vision/API key
- [docs/markdown-app/](./docs/markdown-app/) — ขั้นตอนการถอดแบบ, มาตรฐานงาน, สเปคผลิตภัณฑ์, แผนธุรกิจ (00-13)
- [BACKLOG.md](./BACKLOG.md) — รายการคำถาม/งานค้าง
- [LOG.md](./LOG.md) — บันทึกพัฒนาการของเว็บแอปนี้โดยตรง
- [docs/blueprint-history-log.md](./docs/blueprint-history-log.md) — บันทึกประวัติศาสตร์จากช่วงพัฒนาเอกสารพิมพ์เขียว/ทดสอบก่อนมีเว็บแอป (archive อ่านอย่างเดียว)

Repository: [github.com/ronnakit/PDFtoBOQ](https://github.com/ronnakit/PDFtoBOQ) (private)
