# ข้อมูลพื้น (Floor) — new house

> ข้อมูลนี้ยืนยันกับเจ้าของโปรเจกต์แล้ว (2569-08-30) — ห้องมาจากการอ่าน A-04 (แบบสถาปัตย์จริง)
> ไม่ใช่จากกริดโครงสร้าง S-02 (ดู `extract_floor_boq.py` และ `03-ai-boq-procedure.md` หมวด 1
> "ห้ามใช้กริดโครงสร้างสมมติรูปทรง/ขนาดห้องสถาปัตย์")
>
> กริดอ้างอิง (ม., จากคอลัมน์1/แถวA): คอลัมน์ 1=0, 2=4.50, 4=9.00, 5=14.00, 6=19.00;
> แถว A=0, B=4.50, C=6.50, D=11.00, E=15.50, โซน offset เหนือแถว A = -1.90 ถึง 0
> (เฉพาะคอลัมน์1-2 และ 5-6)

## พารามิเตอร์พื้น

ยืนยันจาก S-09 (แบบขยายพื้น) 2569-08-30 — ดูที่มา/เหตุผลเต็มใน `03-ai-boq-procedure.md` หมวด 1 "กฎเหล็กเสริมพื้น S1"

- topping_thickness_m: 0.05
- s1_thickness_m: 0.10
- s1_cover_m: 0.035
- main_mesh_spacing_m: 0.15
- main_mesh_rebar_size: RB9
- chair_spacing_m: 0.125
- chair_length_m: 0.25
- chair_rebar_size: RB6

## รายการห้อง

| name | system | floor_code | width_m | length_m | area_override_m2 | note |
|---|---|---|---|---|---|---|
| ห้องครัว | HC | F1 | 4.50 | 4.50 | | col1-2, row A-B |
| ห้องโถง (zone1: col4-5, row A-B) | HC | F1 | 5.00 | 4.50 | | |
| ห้องโถง (zone2: col2-4, row A-B) | HC | F1 | 4.50 | 4.50 | | |
| ห้องโถง (zone3: col2-4, row B-C) | HC | F1 | 4.50 | 2.00 | | |
| ห้องโถง (zone4: col2-4, row C-D top 1.6m) | HC | F1 | 4.50 | 1.60 | | |
| ห้องนอน 3 | HC | F1 | 5.00 | 4.50 | | col5-6, row A-B |
| ห้องนอน 2 (col1-2 portion, full row C-D) | HC | F1 | 4.50 | 4.50 | | |
| ห้องนอน 2 (col2-4 portion, row C-D minus zone4 overlap) | HC | F1 | 4.50 | 2.90 | | 4.50-1.60 |
| ห้องนอน 1 (9.00x4.50 row D-E, minus WC1) | HC | F1 | | | 34.41 | col1-4, row D-E, net of WC1 cutout (9.00x4.50 - 2.10x2.90) |
| WC1 | S1 | F2 | 2.10 | 2.90 | | row D-E corner, col1 |
| WC2 | S1 | F2 | 3.40 | 2.00 | | inset in kitchen footprint, row B-C |
| WC3 | S1 | F2 | 2.90 | 1.90 | | offset zone above row A, col5-6 |
| ระเบียงหน้าบ้าน | S1 | F3 | 3.40 | 1.90 | | offset zone above row A, col1-2; exterior anti-slip tile on S1 |
| ระเบียงไม้กลางบ้าน | S1 | F4 | 10.00 | 2.00 | | row B-C, col4-6; wood decking laid over S1 for strength, confirmed by owner |
