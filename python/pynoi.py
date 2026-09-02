"""
pynoi.py -- ประตูเดียวของไพน้อย (single entry point, หลาย module ข้างใน)

ไม่ต้องจำชื่อไฟล์สคริปต์ทีละไฟล์อีกต่อไป -- เรียกผ่านคำสั่งเดียวนี้แทน:

    python pynoi.py <คำสั่ง> [เงื่อนไขของคำสั่งนั้น...]

ดูรายการคำสั่งทั้งหมด:
    python pynoi.py --help

ดูวิธีใช้ของคำสั่งใดคำสั่งหนึ่ง (ส่งต่อ --help ให้ module นั้นโดยตรง):
    python pynoi.py floor --help

เบื้องหลัง: แต่ละคำสั่งแค่เรียกไฟล์ .py เดิม (module) ที่มีอยู่แล้วให้ทำงาน -- ไม่ได้เขียนโค้ด
คำนวณซ้ำใหม่ที่นี่ ผลลัพธ์เหมือนรันไฟล์นั้นตรงๆ ทุกประการ
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# คำสั่ง -> (ไฟล์ module, คำอธิบายสั้นๆ)
COMMANDS = {
    "new-project": ("new_project.py", "ตั้งโปรเจกต์ใหม่ (สร้างโฟลเดอร์มาตรฐาน + ก็อปปี้ไฟล์เข้าที่)"),
    "stage0": ("extract_foundation_data.py", "Stage 0 -- อ่านข้อมูลพื้นฐานโครงการจาก PDF (หน้าปก/ผังบริเวณ/สารบัญแบบ/สัญลักษณ์)"),
    "footing": ("extract_footing_boq.py", "ถอดปริมาณฐานราก (คอนกรีต+เหล็ก)"),
    "pier-column": ("extract_pier_column_boq.py", "ถอดปริมาณตอม่อ-เสา (คอนกรีต+เหล็ก)"),
    "beam": ("extract_beam_boq.py", "ถอดปริมาณคาน (คอนกรีต+เหล็ก)"),
    "floor": ("extract_floor_boq.py", "ถอดปริมาณพื้น (อ่านจาก MD/floor_data.md ของโปรเจกต์)"),
    "roof": ("extract_roof_boq.py", "ถอดปริมาณหลังคา (อ่านจาก MD/roof_geometry.md ของโปรเจกต์)"),
    "cutting-list": ("combine_cutting_list.py", "รวม cutting list เหล็กข้ามหมวด (ลดของเสียจากการตัดแยกทีละหมวด)"),
    "ground-truth": ("read_ground_truth_boq.py", "อ่านไฟล์ BOQ จริง (.xls) ของลูกค้ามาดูเปรียบเทียบ"),
}


def print_help() -> None:
    print(__doc__)
    print("คำสั่งที่มีตอนนี้:\n")
    width = max(len(c) for c in COMMANDS)
    for cmd, (_, desc) in COMMANDS.items():
        print(f"  {cmd:<{width}}  {desc}")
    print("\nตัวอย่าง:")
    print('  python pynoi.py new-project')
    print('  python pynoi.py floor "../../new house"')
    print('  python pynoi.py roof "../../new house"')
    print('  python pynoi.py footing "../../new house/PDF/xxx.pdf" --s01-page 5 --s05-page 9')


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print_help()
        return

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"⚠️ ไม่รู้จักคำสั่ง '{cmd}'\n")
        print_help()
        sys.exit(1)

    script_name, _ = COMMANDS[cmd]
    script_path = HERE / script_name
    forwarded_args = sys.argv[2:]

    result = subprocess.run([sys.executable, str(script_path), *forwarded_args])
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
