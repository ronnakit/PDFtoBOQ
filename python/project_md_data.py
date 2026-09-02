"""
project_md_data.py -- อ่านข้อมูลเฉพาะโปรเจกต์จากไฟล์ markdown ใต้ project/<ชื่อ>/MD/

หลักการ (ยืนยันกับเจ้าของโปรเจกต์ 2569-09-01): ข้อมูลบางอย่างใช้ร่วมกันได้ทุกโปรเจกต์
(สูตรคำนวณ, ค่าคงที่ทางฟิสิกส์ของวัสดุ เช่น น้ำหนักเหล็ก กก./เมตร) -- อันนี้อยู่ในโค้ด
(ตัวแปร/ฟังก์ชันใน extract_*.py) ได้ตามปกติ แต่ **ข้อมูลที่ยืนยันเฉพาะบ้านหลังนั้น
(ขนาดห้อง, ตำแหน่งกริด, ระยะเสริมเหล็กที่อ่านจากแบบขยายของโปรเจกต์นั้น ฯลฯ) ต้องอยู่ใน
ไฟล์ MD ของโปรเจกต์นั้นเท่านั้น** ห้ามฝังเป็นค่าคงที่ในตัวสคริปต์ -- เพื่อให้สคริปต์คำนวณ
(extract_floor_boq.py, extract_roof_boq.py) ใช้ซ้ำข้ามโปรเจกต์ได้จริง แค่เปลี่ยนไฟล์ MD
ไม่ต้องแก้โค้ด

รูปแบบไฟล์ MD ที่อ่านได้ (เขียนด้วยมือหรือแก้ด้วยมือได้ง่าย ไม่ใช่ format พิเศษ):

    ## หัวข้อ Key-Value
    - key_name: 0.15
    - another_key: RB9

    ## หัวข้อตาราง
    | col_a | col_b | col_c |
    |---|---|---|
    | 4.50  | 4.50  | note text |

ใช้:
    from project_md_data import load_keyvalue_section, load_table_section
"""
import re
from pathlib import Path


def _find_section(md_text: str, header: str) -> str:
    """Return the text block under a `## header` line, up to the next `##` or EOF."""
    pattern = rf"^##\s*{re.escape(header)}\s*$"
    lines = md_text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(pattern, line.strip()):
            start = i + 1
            break
    if start is None:
        raise ValueError(f'ไม่พบหัวข้อ "## {header}" ในไฟล์ MD นี้')
    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].strip().startswith("## "):
            end = i
            break
    return "\n".join(lines[start:end])


def _coerce(value: str):
    value = value.strip()
    if value == "":
        return None
    try:
        if "." in value or "e" in value.lower():
            return float(value)
        return int(value)
    except ValueError:
        return value  # leave as string (e.g. "RB9", "col2")


def load_keyvalue_section(md_path, header: str) -> dict:
    """Parse a `## header` block of `- key: value` lines into {key: value}."""
    text = Path(md_path).read_text(encoding="utf-8")
    block = _find_section(text, header)
    result = {}
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        line = line.lstrip("-").strip()
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        result[key.strip()] = _coerce(value)
    return result


def load_table_section(md_path, header: str) -> list[dict]:
    """Parse a `## header` markdown table into a list of row-dicts keyed by column header.
    Empty cells become None. Numeric-looking cells are converted to int/float."""
    text = Path(md_path).read_text(encoding="utf-8")
    block = _find_section(text, header)
    rows = [line.strip() for line in block.splitlines() if line.strip().startswith("|")]
    if len(rows) < 2:
        raise ValueError(f'หัวข้อ "## {header}" ไม่มีตาราง markdown ที่อ่านได้')
    headers = [c.strip() for c in rows[0].strip("|").split("|")]
    data_rows = rows[2:]  # skip header + separator ("|---|---|")
    out = []
    for row in data_rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        record = {headers[i]: _coerce(cells[i]) if i < len(cells) else None for i in range(len(headers))}
        out.append(record)
    return out
