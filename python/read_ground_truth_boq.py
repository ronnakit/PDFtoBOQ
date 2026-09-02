"""
read_ground_truth_boq -- dump the human-made ground-truth BOQ (.xls) into a
structured form, for comparing pynoi's parsed-from-CAD quantities against
what a real QS actually measured and priced.

This is NOT a general-purpose BOQ-Excel parser -- it is written against the
specific sheet layout of ../../new house/boq/BOQ - new house.xls (sheets:
total, Struc, Arch, San, EE, ACC). A second ground-truth project
("welcome maerem" / Kadfarang) exists with its own BOQ file and likely a
different layout -- this script will need adapting, not blind reuse, when
that file is tackled (see ../../../BACKLOG.md).

Requires the legacy `xlrd` (1.2.0) -- modern xlrd dropped .xls support,
and openpyxl only reads .xlsx. See ../../../CLAUDE.md if this needs
reinstalling: `pip install xlrd==1.2.0`.

Usage:
    python read_ground_truth_boq.py "../../new house/boq/BOQ - new house.xls"
"""

import argparse
import sys
from pathlib import Path

import xlrd

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# column layout shared by every non-"total" sheet in this workbook:
# code, description, qty, unit, unit_material, total_material, unit_labor, total_labor, total
COL_CODE, COL_DESC, COL_QTY, COL_UNIT, COL_UNIT_MAT, COL_TOTAL_MAT, COL_UNIT_LABOR, COL_TOTAL_LABOR, COL_TOTAL = range(9)


def load(file_path: Path):
    if not file_path.exists():
        raise FileNotFoundError(file_path)
    return xlrd.open_workbook(str(file_path))


def read_line_items(sheet) -> list[dict]:
    """แถวที่มี code (แปลงเป็นตัวเลข/สตริงได้) ในคอลัมน์แรก และมี description -- ถือเป็น line item"""
    items = []
    for r in range(sheet.nrows):
        code = sheet.cell_value(r, COL_CODE) if sheet.ncols > COL_CODE else ""
        desc = sheet.cell_value(r, COL_DESC) if sheet.ncols > COL_DESC else ""
        if code == "" or not str(desc).strip():
            continue
        if str(desc).strip().startswith(("รวม", "แบบแสดง", "ชื่อโครงการ", "สถานที่", "เจ้าของ")):
            continue  # subtotal/header rows, not line items
        items.append(
            {
                "row": r,
                "code": code,
                "description": str(desc).strip(),
                "qty": sheet.cell_value(r, COL_QTY) if sheet.ncols > COL_QTY else "",
                "unit": sheet.cell_value(r, COL_UNIT) if sheet.ncols > COL_UNIT else "",
                "total_cost": sheet.cell_value(r, COL_TOTAL) if sheet.ncols > COL_TOTAL else "",
            }
        )
    return items


def report_sheet(wb, sheet_name: str) -> list[dict]:
    sheet = wb.sheet_by_name(sheet_name)
    items = read_line_items(sheet)
    print(f"\n=== {sheet_name} ({len(items)} line items) ===")
    for it in items:
        print(f"  [{it['code']}] {it['description']} -- {it['qty']} {it['unit']} = {it['total_cost']}")
    return items


def check_duplicate_codes(all_items: dict[str, list[dict]]) -> None:
    """คู่มือ BOQ นี้เขียนโดยคนจริงเร่งรีบเช่นกัน -- เจอ code ซ้ำ (เช่น '2.1' ปรากฏ 2 ครั้งในชีตเดียว)
    ระหว่างสำรวจไฟล์นี้ ไม่ต่างอะไรจาก "ขยะ" ที่เจอใน CAD (07-drawing-signal-vs-noise.md) แค่คนละสื่อ --
    ต้อง flag ไว้ ไม่ใช่ไว้ใจว่า code จะ unique เสมอ
    """
    for sheet_name, items in all_items.items():
        seen: dict[str, int] = {}
        for it in items:
            key = str(it["code"])
            seen[key] = seen.get(key, 0) + 1
        dupes = {k: n for k, n in seen.items() if n > 1}
        if dupes:
            print(f"\n⚠️ {sheet_name}: code ซ้ำกัน -- {dupes} (ตรวจสอบว่าเป็น typo ของผู้ทำ BOQ เอง)")


def main() -> None:
    ap = argparse.ArgumentParser(description="อ่าน ground-truth BOQ (.xls) แบบมีโครงสร้าง")
    ap.add_argument("file", type=Path, help="path to the ground-truth .xls BOQ")
    args = ap.parse_args()

    wb = load(args.file)
    sheet_names = [n for n in wb.sheet_names() if n != "total"]
    all_items = {name: report_sheet(wb, name) for name in sheet_names}
    check_duplicate_codes(all_items)


if __name__ == "__main__":
    main()
