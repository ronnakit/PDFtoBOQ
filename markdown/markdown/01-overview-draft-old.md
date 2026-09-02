# BuildFlow AI: Construction Estimation & Modeling Platform

## 🎯 Mission
พัฒนาแพลตฟอร์มที่เปลี่ยนไฟล์แปลน CAD ให้เป็น BOQ และโมเดล 3D ได้โดยอัตโนมัติ เพื่อลดเวลาในการถอดแบบและประเมินราคาสำหรับผู้รับเหมาไทย (ตลาด < 10 ล้านบาท)

---

## 👤 Target Personas
### 1. ผู้รับเหมารุ่นใหม่ (คุณกร)
- **Goal:** ปิดการขายงานไว, แม่นยำเรื่องต้นทุน, ไม่เสียเวลาทำงานเอกสาร
- **Pain Point:** เบื่อการถอดแบบมือ/Excel, กลัวคำนวณพลาดจนเข้าเนื้อ

### 2. รูปแบบโครงการ (อาคารพาณิชย์/บ้าน)
- **Scope:** บ้านจัดสรร, ทาวน์โฮม, อาคารพาณิชย์ (พื้นที่ < 200 ตร.ม.)
- **Requirement:** ความแม่นยำ, ความโปร่งใสของราคา (อิงกรมบัญชีกลาง/สพฐ.)

---

## 🗺️ User Journey (The BuildFlow)

1. **Upload:** อัปโหลดไฟล์ .dwg/.dxf (รองรับไฟล์มี XREF โดยมีระบบแจ้งเตือนกรณีไฟล์หาย)
2. **Configure:** เลือกฟังก์ชันที่ต้องการ (A La Carte: BOQ, 3D SketchUp, 3D Revit)
3. **Process:** ระบบประมวลผล (Parser -> Calculation -> Rendering)
4. **Payment:** ตรวจสอบเครดิตคงเหลือ (แจ้งเตือน/เติมเงิน QR พร้อมเพย์หากไม่พอ)
5. **Output:** ดาวน์โหลดไฟล์ Excel BOQ (พร้อมสูตรคำนวณ) หรือโมเดล .skp

---

## ⚙️ Tech Stack & Roadmap
### Phase 1: MVP (Fast QTO & BOQ)
- **CAD Parsing:** ใช้ Python (ezdxf) แกะโครงสร้าง Entity ในไฟล์
- **Pricing Engine:** ดึงข้อมูลราคากลางกรมบัญชีกลาง/สพฐ. (JSON/Database)
- **Excel Export:** สร้างไฟล์ Excel พร้อมสูตรคำนวณ (`=Quantity * UnitPrice`)

### Phase 2: 3D Generation
- **Geometry:** แปลง Vector 2D เป็น 3D Component ใน SketchUp
- **Auto-Tagging:** ระบบจัดหมวดหมู่ Tag/Group อัตโนมัติ

---

## 💰 Business Model
- **Freemium:** ฟรีสำหรับอาคารพื้นที่ < 200 ตร.ม.
- **Pay-per-use:** ขายเครดิตแบบเติมเงิน (500 / 1,000 / 2,000 บาท)


