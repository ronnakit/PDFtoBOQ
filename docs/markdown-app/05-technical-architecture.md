# สถาปัตยกรรมเทคนิค (Web App + Server-side Core)

> เอกสารนี้บันทึกทิศทางที่ตัดสินใจแล้วเรื่องรูปแบบระบบ ส่วนรายละเอียดการเลือกเทคโนโลยี/hosting ยังเป็น open question — ดู §4

## 1. ทิศทางที่ตัดสินใจแล้ว

- **หน้าบ้านเป็น Web Application** (ไม่ใช่ desktop app หรือ mobile app) — ลูกค้าอัปโหลดไฟล์ DWG/DXF ผ่านเบราว์เซอร์
- **Core engine (ตัวถอดแบบ/คำนวณ BOQ ของ "ไพน้อย") อยู่บน server เท่านั้น** ไม่ส่ง logic การคำนวณ/กฎ net deduction/pricing rule ไปให้ client — เหตุผลหลักคือป้องกันการ reverse engineer สูตร/กฎที่เป็นทรัพย์สินทางปัญญาหลักของโครงการ
- **เฟสนี้ (prototype)**: รันทุกอย่างบนเครื่อง dev ของผู้ก่อตั้งก่อน ยังไม่ deploy ขึ้น production server จริง

## 2. ข้อควรระวัง — "server-side core" ป้องกัน reverse engineering ได้แค่ระดับหนึ่ง ไม่ใช่ทั้งหมด

การเก็บ core logic ไว้บน server ป้องกันไม่ให้คนเห็น **source code/สูตรตรงๆ** ได้จริง แต่ **ไม่ได้ป้องกันการเดา/สร้างระบบเลียนแบบจากการดู input/output**:

- ถ้าคู่แข่งส่งไฟล์ DWG หลายร้อยไฟล์เข้าระบบแล้วเทียบผลลัพธ์ BOQ ที่ได้ ก็สามารถ "reverse engineer" กฎ business logic ได้ระดับหนึ่ง (เหมือนที่เกิดขึ้นกับ API สาธารณะทั่วไป)
- สิ่งที่ป้องกันได้จริงคือ **การขโมย codebase ตรงๆ** ไม่ใช่การเดา logic จาก behavior
- คำแนะนำ: ใช้ rate limiting + ต้องสมัครสมาชิก/จ่ายเงินก่อนใช้ (ไม่เปิด API สาธารณะแบบไม่จำกัด) เพื่อทำให้การ "scrape" input/output จำนวนมากมีต้นทุนสูงพอที่จะไม่คุ้มสำหรับคู่แข่งรายเล็ก — ไม่ใช่การป้องกันแบบเบ็ดเสร็จ

## 3. ภาพรวม pipeline (ระดับแนวคิด)

```
[Client: Web App]
   → อัปโหลดไฟล์ DWG/DXF
   → (ถ้าเป็น DWG) แปลงเป็น DXF ด้วย ODA File Converter
[Server: Core Engine "ไพน้อย"]
   → Parser (ezdxf) แกะ entity/layer/block
   → จับคู่กับ Master Category Schema (04-category-schema.md)
   → คำนวณปริมาณสุทธิ (net deduction, waste factor) ตาม SOP (03-ai-boq-procedure.md)
   → ผูกราคาจาก price list (ราคากลาง + ⚠️ ต้องยืนยันสิทธิ์การใช้)
   → Generate Excel BOQ (มีสูตรคำนวณ)
[Client: Web App]
   → ดาวน์โหลดผลลัพธ์ / ตรวจสอบเครดิตคงเหลือ
```

## 4. Open questions ที่ต้องตัดสินใจก่อนเริ่มเขียนโค้ดจริง

- [ ] เลือก stack ฝั่ง server (Python/FastAPI เป็นตัวเลือกธรรมชาติเพราะ ezdxf เป็น Python) และฝั่ง web frontend
- [ ] เลือก hosting provider (ต้องรองรับไฟล์อัปโหลดขนาดใหญ่ + ประมวลผล CAD ที่ใช้ CPU/memory สูงกว่าเว็บทั่วไป)
- [ ] ระบบ auth + credit/billing (ต้องผูกกับ PromptPay/บัตร — ดูแนวทาง Payment Gateway ที่รักบ้านใช้เป็นตัวอย่างใน `07-technical-requirements.md` ของรักบ้าน)
- [ ] นโยบายความปลอดภัยไฟล์อัปโหลด (validate นามสกุล/ขนาด/สแกนไวรัส ก่อนประมวลผลไฟล์ CAD ที่มาจากภายนอก)
- [ ] แนวทาง rate limiting/ป้องกันการ scrape ตาม §2
- [ ] เก็บไฟล์ CAD ของลูกค้านานแค่ไหน/นโยบายความเป็นส่วนตัวของแบบบ้านลูกค้า (แบบบ้านอาจมีข้อมูลที่ตั้ง/เจ้าของ)
