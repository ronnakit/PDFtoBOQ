"""ไพน้อย — เปรียบเทียบผลคำนวณ (ฐานราก+ตอม่อ+เสา+คาน) กับ BOQ จริง (ground truth)
และคำนวณไม้แบบ (formwork) เพิ่ม — ทั้งหมดเป็นโค้ด Python ล้วน ใช้ตัวเลขที่ยืนยันแล้ว
จาก claude_boq.md เท่านั้น ไม่เรียก AI/API เพิ่ม

Formwork formula (มาตรฐานทั่วไป):
- ฐานราก/ตอม่อ (สี่เหลี่ยมจัตุรัส หล่อในหลุมขุด): ไม้แบบ 4 ด้าน = เส้นรอบรูป x ความลึก/ความสูง
- เสา (ยืนอิสระ เหนือพื้น): ไม้แบบ 4 ด้าน = เส้นรอบรูป x ความสูง
- คาน (ท้องคาน+ข้าง 2 ด้าน, ด้านบนไม่ต้องเพราะเทพร้อมพื้น): ไม้แบบ 3 ด้าน = (กว้าง + 2xลึก) x ความยาว
"""

# --- ground truth (BOQ - new house.xls, sheet "Struc") ---
GT = {
    "2.0_ฐานรากเสาตอม่อ": {"lean_concrete_m3": 4.0, "concrete_m3": 7.0, "db12_kg": 478.0, "rb6_kg": 40.0, "formwork_m2": 50.0},
    "3.0_เสาคาน": {"concrete_m3": 14.0, "db12_kg": 1259.0, "rb6_kg": 366.0, "steel_box_kg": 228.0, "formwork_m2": 206.0},
    "4.0_พื้น": {"concrete_m3": 13.0, "formwork_m2": 14.0},
}

# --- ไพน้อย: ฐานราก (from claude_boq.md, extract_footing_boq.py) ---
FOOTING = {
    # T values back-solved from the confirmed pad volumes in claude_boq.md
    # (0.45/2.75/4.056 m3) - NOT all 0.20m, that was a display bug fixed 2569-08-30
    "F1": {"count": 4, "A": 0.75, "B": 0.75, "T": 0.20},
    "F2": {"count": 11, "A": 1.00, "B": 1.00, "T": 0.25},
    "F3": {"count": 8, "A": 1.30, "B": 1.30, "T": 0.30},
}
footing_concrete = sum(f["A"] * f["B"] * f["T"] * f["count"] for f in FOOTING.values())
footing_formwork = sum(2 * (f["A"] + f["B"]) * f["T"] * f["count"] for f in FOOTING.values())

# --- ไพน้อย: ตอม่อ (below floor, 0.20x0.20, height 1.2m, 23 ต้นรวม C1+Cx) ---
PIER_CROSS = (0.20, 0.20)
PIER_HEIGHT = 1.2
N_PIERS_TOTAL = 11 + 8 + 4  # C1/F2 + C1/F3 + Cx/F1
pier_concrete = PIER_CROSS[0] * PIER_CROSS[1] * PIER_HEIGHT * N_PIERS_TOTAL
pier_formwork = 2 * sum(PIER_CROSS) * PIER_HEIGHT * N_PIERS_TOTAL

# --- ไพน้อย: เสา (above floor, C1 only, 0.20x0.20, height 3.2m, 19 ต้น) ---
COLUMN_CROSS = (0.20, 0.20)
COLUMN_HEIGHT = 3.2
N_COLUMNS_C1 = 11 + 8
column_concrete = COLUMN_CROSS[0] * COLUMN_CROSS[1] * COLUMN_HEIGHT * N_COLUMNS_C1
column_formwork = 2 * sum(COLUMN_CROSS) * COLUMN_HEIGHT * N_COLUMNS_C1

# --- ไพน้อย: คาน (38 segment, ยืนยันแล้ว, จาก extract_beam_boq.py รอบล่าสุด) ---
BEAM_CROSS = (0.20, 0.40)  # width, depth
BEAM_SEGMENTS_M = [
    4.5, 1.9, 1.9, 4.5, 4.5, 5.0, 5.0, 0.7, 0.7, 4.5, 4.5, 3.5, 3.5,
    4.5, 4.5, 5.0, 5.0, 2.0, 2.0, 4.5, 2.0, 2.5, 1.9, 1.6, 1.0,
    4.5, 4.5, 5.0, 5.0, 4.5, 4.5, 4.5, 4.5, 4.5, 4.5, 4.5, 4.5, 2.0,
]
beam_total_length = sum(BEAM_SEGMENTS_M)
beam_concrete = BEAM_CROSS[0] * BEAM_CROSS[1] * beam_total_length
# 3-side formwork: bottom (width) + 2 sides (depth) - top open, cast with slab
beam_formwork = (BEAM_CROSS[0] + 2 * BEAM_CROSS[1]) * beam_total_length

WASTE = 1.03

print("=== หมวด 2.0 ฐานราก+ตอม่อ (below floor) ===")
print(f"ไพน้อย: คอนกรีตฐานราก {footing_concrete:.3f} m3 (+3%={footing_concrete*WASTE:.3f}) + ตอม่อ {pier_concrete:.3f} m3 (+3%={pier_concrete*WASTE:.3f}) = รวม {(footing_concrete+pier_concrete)*WASTE:.3f} m3")
print(f"BOQ จริง (2.5): {GT['2.0_ฐานรากเสาตอม่อ']['concrete_m3']} m3")
print(f"ไพน้อย: ไม้แบบฐานราก {footing_formwork:.2f} m2 + ตอม่อ {pier_formwork:.2f} m2 = รวม {footing_formwork+pier_formwork:.2f} m2")
print(f"BOQ จริง (2.9): {GT['2.0_ฐานรากเสาตอม่อ']['formwork_m2']} m2")

print("\n=== หมวด 3.0 เสา+คาน (above floor) ===")
combined_concrete = (column_concrete + beam_concrete) * WASTE
print(f"ไพน้อย: คอนกรีตเสา {column_concrete:.3f} m3 + คาน {beam_concrete:.3f} m3 = รวมสุทธิ {column_concrete+beam_concrete:.3f} m3, +3%={combined_concrete:.3f} m3")
print(f"BOQ จริง (3.1): {GT['3.0_เสาคาน']['concrete_m3']} m3")
combined_formwork = column_formwork + beam_formwork
print(f"ไพน้อย: ไม้แบบเสา {column_formwork:.2f} m2 + คาน {beam_formwork:.2f} m2 = รวม {combined_formwork:.2f} m2")
print(f"BOQ จริง (3.6): {GT['3.0_เสาคาน']['formwork_m2']} m2")

print(f"\nรวมไม้แบบทั้งหมด (ฐานราก+ตอม่อ+เสา+คาน) ไพน้อย: {footing_formwork+pier_formwork+combined_formwork:.2f} m2")
print(f"รวม BOQ จริง (2.9+3.6): {GT['2.0_ฐานรากเสาตอม่อ']['formwork_m2']+GT['3.0_เสาคาน']['formwork_m2']} m2")
