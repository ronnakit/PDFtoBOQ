# 05 — สถาปัตยกรรมระบบและโครงสร้างทางเทคนิค (Technical Architecture)

---

## 1. โครงสร้างระบบ (System Architecture)
- Web Frontend: Vanilla HTML5 / CSS3 / JavaScript (Drag & Drop UI)
- Backend Engine: Python 3.11+ (ThreadingHTTPServer / app_server.py)
- Modules:
  1. PDF Inspector: แยก Vector Text และ Scanned Bitmap
  2. Project Sandbox: แยกโฟลเดอร์โครงการอิสระ 100%
  3. Quality Gate: ตรวจสอบความสมบูรณ์แบบก่อนคำนวณ
  4. Deterministic Engine: คิดปริมาณงานโครงสร้างด้วยสูตรวิศวกรรม
  5. Report Exporter: ReportLab PDF และ openpyxl Excel Workbook

---

## 2. การแยกพื้นที่โครงการ (Project Isolation Standard)
ทุกโครงการจะถูกแยกโฟลเดอร์อิสระใน D:\webapp\pdftoboq\project\<ชื่อโครงการ>\
ประกอบด้วย 5 โฟลเดอร์มาตรฐาน:
- PDF/ : ไฟล์แบบแปลนต้นฉบับ
- boq/ : ไฟล์รายงาน PDF และ Excel BOQ
- cad/ : ไฟล์แบบ 2D/3D CAD (.dwg, .dxf, .skp)
- markdown/ : เก็บไฟล์ฐานข้อมูล MD (confirm_boq.md, foundation_data.md, floor_data.md, roof_geometry.md)
- symbols/ : รูปภาพสัญลักษณ์และ Marker ที่สกัดจากแบบ
