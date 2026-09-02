"""
new_project.py -- ตั้งโปรเจกต์ใหม่ให้ไพน้อย (สร้างโฟลเดอร์มาตรฐาน + ก็อปปี้ไฟล์เข้าที่)

ทำสิ่งนี้ให้:
  1. สร้างโฟลเดอร์ project/<ชื่อโปรเจกต์>/ พร้อมโฟลเดอร์ย่อยมาตรฐาน (PDF, boq, cad, symbols, MD)
     ตามแบบเดียวกับที่ใช้ในโปรเจกต์ "new house" -- กันชนกับโปรเจกต์อื่น เพราะแยกคนละโฟลเดอร์เต็มๆ
  2. ถามหาไฟล์จริง (แบบก่อสร้าง PDF, BOQ เปรียบเทียบ .xls/.xlsx, ไฟล์ CAD .dxf ถ้ามี)
     แล้วก็อปปี้เข้าโฟลเดอร์ย่อยที่ถูกต้องให้อัตโนมัติ -- ไม่ต้องสร้าง/วางเองทีละที
  3. สร้างไฟล์ claude_boq.md เปล่า (แม่แบบ) ให้พร้อมเริ่มบันทึกผลลัพธ์ที่ยืนยันแล้ว

ใช้งาน (รันจาก command line แล้วตอบคำถามที่ถามไปเรื่อยๆ ได้เลย ไม่ต้องจำ syntax):
    python new_project.py

หมายเหตุสำคัญ: เครื่องมือนี้แค่ "จัดที่เก็บไฟล์" ให้เป็นระเบียบเดียวกันทุกโปรเจกต์เท่านั้น
สคริปต์คำนวณ (extract_footing_boq.py, extract_beam_boq.py, extract_floor_boq.py,
extract_roof_boq.py ฯลฯ) เป็นโค้ดกลางที่ใช้ซ้ำได้ทุกโปรเจกต์แล้ว (ไม่มีข้อมูลเฉพาะโปรเจกต์ใดฝังอยู่
ในตัวโค้ดอีกต่อไป) -- แต่ **ข้อมูลที่ต้องยืนยันเฉพาะบ้านหลังนั้น** (ตำแหน่งห้องพื้น, รูปทรง/ตำแหน่งกริด
หลังคา ฯลฯ) ต้องเขียนเป็นไฟล์ markdown ใหม่ไว้ใน project/<ชื่อโปรเจกต์>/MD/ ก่อน (ดูตัวอย่างรูปแบบที่
project/new house/MD/floor_data.md และ roof_geometry.md) สคริปต์จะอ่านจากตรงนั้นแทนของ new house
ทันทีที่ path โปรเจกต์เปลี่ยน
"""

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = PROJECT_ROOT / "project"

STANDARD_SUBFOLDERS = ["PDF", "boq", "cad", "symbols", "markdown"]

CLAUDE_BOQ_TEMPLATE = """# claude_boq.md — BOQ ที่ไพน้อยถอดแล้ว (ยืนยันแล้ว) — {project_name}

> **ไฟล์นี้คือแหล่งอ้างอิงเดียว (single source of truth) ของปริมาณงานทุกหมวดที่ถอดและยืนยันแล้ว**
> ถ้าจะทำงานต่อ **อ่านไฟล์นี้ก่อน ไม่ต้องถอดซ้ำรายการที่มีเครื่องหมาย ✅ ด้านล่าง**
> กฎ/สูตรที่ใช้คำนวณอยู่ใน [03-ai-boq-procedure.md](../../03-ai-boq-procedure.md)

## สถานะการยืนยัน

| รายการ | สถานะ | ยืนยันโดย | วันที่ |
|---|---|---|---|
| (ยังไม่มีรายการ) | - | - | - |

---

# หมวด 1: งานโครงสร้าง

(ยังไม่เริ่มถอด)
"""


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def copy_into(src_str: str, dest_dir: Path) -> None:
    if not src_str:
        return
    src = Path(src_str.strip('"'))
    if not src.exists():
        print(f"  ⚠️ ไม่พบไฟล์ {src} -- ข้ามไป (เช็ค path แล้วรันใหม่ทีหลังได้)")
        return
    dest = dest_dir / src.name
    shutil.copy2(src, dest)
    print(f"  ✅ ก็อปปี้ {src.name} -> {dest.relative_to(PROJECT_ROOT)}")


def main() -> None:
    print("=== ตั้งโปรเจกต์ใหม่ให้ไพน้อย ===\n")

    name = ask("ชื่อโปรเจกต์ใหม่ (เช่น kadfarang, welcome maerem): ")
    if not name:
        print("ไม่ได้ใส่ชื่อโปรเจกต์ ยกเลิกครับ")
        return

    project_dir = PROJECTS_DIR / name
    if project_dir.exists():
        print(f"\n⚠️ โฟลเดอร์ project/{name}/ มีอยู่แล้ว -- ไม่สร้างทับ (กันข้อมูลเก่าหาย)")
        print("   ถ้าต้องการเติมไฟล์เข้าโฟลเดอร์เดิม ให้ก็อปปี้ไฟล์เข้าไปเองที่ path นี้:")
        print(f"   {project_dir}")
        return

    for sub in STANDARD_SUBFOLDERS:
        (project_dir / sub).mkdir(parents=True, exist_ok=True)
    print(f"\n✅ สร้างโฟลเดอร์ project/{name}/ พร้อมโฟลเดอร์ย่อย: {', '.join(STANDARD_SUBFOLDERS)}\n")

    print("ใส่ path ไฟล์จริงที่จะเอาเข้าโปรเจกต์นี้ (ถ้าไม่มี/ยังไม่พร้อม กด Enter ข้ามได้เลย)\n")

    pdf_path = ask("path ไฟล์แบบก่อสร้าง PDF: ")
    copy_into(pdf_path, project_dir / "PDF")

    boq_path = ask("path ไฟล์ BOQ เปรียบเทียบ (.xls/.xlsx, ถ้ามี): ")
    copy_into(boq_path, project_dir / "boq")

    cad_path = ask("path ไฟล์ CAD (.dxf, ถ้ามี): ")
    copy_into(cad_path, project_dir / "cad")

    boq_md = project_dir / "markdown" / "claude_boq.md"
    boq_md.write_text(CLAUDE_BOQ_TEMPLATE.format(project_name=name), encoding="utf-8")
    print(f"\n✅ สร้างไฟล์ผลลัพธ์เปล่า project/{name}/markdown/claude_boq.md ให้แล้ว\n")

    print("=== เสร็จแล้ว ===")
    print(f"โปรเจกต์ '{name}' พร้อมใช้งานที่ project/{name}/")
    print("ขั้นตอนถัดไป (Stage 0 -- อ่านข้อมูลพื้นฐานจาก PDF):")
    print(f'  python extract_foundation_data.py "{project_dir / "PDF"}\\<ชื่อไฟล์.pdf>"')
    print("\n⚠️ หมายเหตุ: หมวดพื้น/หลังคา ต้องเขียนไฟล์ MD ของโปรเจกต์นี้ก่อนถึงจะรันได้")
    print(f'   ดูตัวอย่างรูปแบบที่ project/116-69 - แบบบ้านชั้นเดียว/markdown/floor_data.md และ roof_geometry.md')
    print(f'   แล้วสร้างไฟล์แบบเดียวกันไว้ที่ project/{name}/markdown/ ตามข้อมูลที่ยืนยันกับเจ้าของโปรเจกต์นี้')


if __name__ == "__main__":
    main()
