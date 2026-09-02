# ข้อมูลพื้นฐานโครงการ: บ้านพักอาศัย (newhouse, ดอยสะเก็ด)

> อ่านจากไฟล์ `แบบก่อสร้างอาคารบ้านพักชั้นเดี่ยว.pdf` โดยไพน้อย (Claude Haiku 4.5) — **ยังไม่มีคนตรวจสอบ** แก้ไขก้อน JSON ด้านล่างได้โดยตรงถ้าพบข้อผิดพลาด

## สรุปสำหรับอ่าน (คนอ่านส่วนนี้)

### ข้อมูลโครงการ
- ชื่อโครงการ: แบบก่อสร้างอาคารบ้านพักอาศัยชั้นเดียว 3ห้องนอน 3ห้องน้ำ
- เจ้าของ: คุณ สิริกุล ฟุ้งกิตติกุล
- ที่อยู่: บ้านยางทอง หมู่ที่ 4 ต.สันปูเลย อ.ดอยสะเก็ด จ.เชียงใหม่
- ใบอนุญาตเลขที่: 503/2568
- เล่มที่: 
- วันที่: 12 มิ.ย. 2568

### ข้อมูลที่ดิน/ผังบริเวณ
- โฉนดเลขที่: 65978 (เล่มที่ 660 หน้า 78)
- เลขที่ดินอ้างอิง: ระวางที่ดิน 4846 IV 0880 เลขที่ดิน 2992 ตำบลสันปูเลย อำเภอดอยสะเก็ด จังหวัดเชียงใหม่
- องค์ประกอบที่พบในผัง: ที่จอดรถ (parking area with car symbols), ระบบระบายน้ำ (drainage system, per แบบสาธารณสุข), แนวต้นไม้/รั้วต้นไม้รอบพื้นที่ (tree line along boundary), อาคารหลัก/สิ่งปลูกสร้าง (main building outline with rooms), ทางเดิน/ลานอเนกประสงค์ (pathway/patio area)

### สารบัญแบบ (ตรวจสอบกับ title block จริงของแต่ละหน้าแล้ว)
| รหัส | ชื่อแผ่น | หมวด |
|---|---|---|
| A-01 | ผังบริเวณ - แผนที่สังเขป | Architecture |
| A-02 | สารบัญแบบ | Architecture |
| A-03 | รายการประกอบแบบ | Architecture |
| A-04 | แปลน พื้นอาคาร | Architecture |
| A-05 | แปลน หลังคา | Architecture |
| A-06 | รูปด้านที่ 1 - 2 | Architecture |
| A-07 | รูปด้านที่ 2 - 3 | Architecture |
| A-08 | รูปตัด A-A | Architecture |
| A-09 | รูปตัด B-B | Architecture |
| A-10 | แบบขยายประตู | Architecture |
| A-11 | แบบขยายหน้าต่าง | Architecture |
| A-12 | แบบขยายห้องน้ำ | Architecture |
| S-01 | แปลน ฐานราก , เสาตอม่อ | Structural |
| S-02 | แปลน เสา , คาน , และพื้น | Structural |
| S-03 | แปลน โครงสร้างหลังคา - อะเส | Structural |
| S-04 | ขยาย โครงสร้างหลังคา | Structural |
| S-05 | แบบขยายฐานราก | Structural |
| S-06 | แบบขยายเสา ฐานคลองราก | Structural |
| S-07 | แบบขยายงานเสริมเหล็กคานทั่วไป | Structural |
| S-08 | แบบขยายโครงสร้างคาน | Structural |
| S-09 | แบบขยายโครงสร้างพื้น | Structural |
| E-01 | แปลน ไฟฟ้า,สัญลักษณ์ | Electrical |
| E-02 | แปลน ไฟฟ้าส่องสว่าง | Electrical |
| E-03 | แปลน ไฟฟ้ากำลัง | Electrical |
| SN-01 | แบบสุขาภิบาลทั่วไป | Sanitary |
| SN-02 | แบบแปลนน้ำดี | Sanitary |
| SN-03 | แบบแปลนน้ำเสีย | Sanitary |
| SN-04 | แบบขยายบ่อซึมน้ำเสีย บ่อเกรอะ - บ่อซึม | Sanitary |

✅ title block ทุกหน้าตรงกับสารบัญที่ประกาศไว้ ไม่พบจุดขัดแย้ง

### สัญลักษณ์แบบ (ใช้ตีความหน้าอื่นๆ ในชุดแบบนี้ทั้งหมด)
> ⚠️ **AI อ่านรูปทรง/ลาย hatch ผิดพลาดซ้ำๆในหลายรอบที่ผ่านมา (สลับคู่กัน, อ่านรูปทรงผิด) — ดูรูปจริงเทียบกับคำอธิบายเสมอ ก่อนติ๊กยืนยัน**

**ภาพรวมตำแหน่งกรอบที่ไพน้อยเสนอ (เลขกำกับตรงกับหัวข้อด้านล่าง):**  
![overview](symbols/_proposal_overview.png)

> ถ้ากรอบไหนเพี้ยน แก้ตัวเลข `bbox_pct` ของสัญลักษณ์นั้นในก้อน JSON ด้านล่างโดยตรง (`[x0, y0, x1, y1]` เป็นสัดส่วนของหน้าเต็ม 0.0-1.0) แล้วรัน `python extract_foundation_data.py <pdf> --index-page N --out-path <ไฟล์นี้> --recrop-only` เพื่อครอปภาพใหม่โดยไม่ต้องเรียก API ซ้ำ

#### 1. ระยะ/แนวเสา
![dimension_symbols](symbols/dimension_symbols.png)
- AI อ่านว่า: Two independent grid-line label symbols: a circle enclosing a letter (e.g. 'A') for a lettered grid line, and a circle enclosing a number (e.g. '1') for a numbered grid line - both point to a crosshair marked 'แนวเสา' (column line). Along a dimension line between two grid marks: a plus-sign (+) crosshair at both ends = 'ระยะศูนย์กลางถึงศูนย์กลาง' (center-to-center); a plus-sign at one end + an X-mark at the other = 'ระยะศูนย์กลางถึงริม' (center-to-edge); an X-mark at both ends = 'ระยะริมถึงริม' (edge-to-edge).
- [ ] ถูกต้อง
- [ ] แก้ไข: _____ (พิมพ์ "ตัดออก" = ไม่ต้องใช้สัญลักษณ์นี้เลย)

#### 4. รูปตัด
![section_marker](symbols/section_marker.png)
- AI อ่านว่า: A single triangular flag containing a letter (e.g. 'A') above a small box labeled 'A-NO'. When captioned 'ชื่อรูปตัดอาคาร แผ่นที่ที่อ้างอิงไปถึง' this names a building SECTION and its sheet number. NOTE: the identical triangle+A-NO glyph is reused elsewhere on this page for 'แบบขยายทั่วไป' (general enlarged-detail callouts) - same shape, different meaning by context/caption, not by shape alone.
- [ ] ถูกต้อง
- [ ] แก้ไข: _____ (พิมพ์ "ตัดออก" = ไม่ต้องใช้สัญลักษณ์นี้เลย)

#### 5. รูปด้าน
![elevation_marker](symbols/elevation_marker.png)
- AI อ่านว่า: A cross/X-shaped marker of four triangular arrowheads pointing outward in 4 directions (positions 1,2,3,4), each triangle labeled 'A-NO' — '1,2,3,4 ชื่อรูปด้าน แสดงทิศทางตามแนวชี้บอก' (names the elevation view; arrow = viewing direction); 'A-NO' gives the sheet number where drawn.
- [ ] ถูกต้อง
- [ ] แก้ไข: _____ (พิมพ์ "ตัดออก" = ไม่ต้องใช้สัญลักษณ์นี้เลย)

#### 6. ทิศเหนือ
![north_symbol](symbols/north_symbol.png)
- AI อ่านว่า: A compass rose with N (top), S (bottom), E (right), W (left) and a bold arrow/needle pointing to N — สัญลักษณ์แสดงทิศเหนือ.
- [ ] ถูกต้อง
- [ ] แก้ไข: _____ (พิมพ์ "ตัดออก" = ไม่ต้องใช้สัญลักษณ์นี้เลย)

#### 7. ลายคอนกรีต
![hatch_concrete](symbols/hatch_concrete.png)
- AI อ่านว่า: Small irregular dot/speck stipple pattern inside a box, labeled 'คอนกรีต'.
- [ ] ถูกต้อง
- [ ] แก้ไข: _____ (พิมพ์ "ตัดออก" = ไม่ต้องใช้สัญลักษณ์นี้เลย)

#### 8. ลายเหล็ก
![hatch_steel](symbols/hatch_steel.png)
- AI อ่านว่า: Evenly-spaced parallel diagonal hatch lines (single direction) inside a box, labeled 'เหล็ก'.
- [ ] ถูกต้อง
- [ ] แก้ไข: _____ (พิมพ์ "ตัดออก" = ไม่ต้องใช้สัญลักษณ์นี้เลย)

#### 9. ลายดิน
![hatch_soil](symbols/hatch_soil.png)
- AI อ่านว่า: Cross-hatch / basket-weave pattern (diagonal lines crossing in two directions) inside a box, labeled 'ดิน'. Visually distinct from concrete's dotted stipple and steel's single-direction diagonal - do not confuse the three in section drawings.
- [ ] ถูกต้อง
- [ ] แก้ไข: _____ (พิมพ์ "ตัดออก" = ไม่ต้องใช้สัญลักษณ์นี้เลย)

#### 10. ลายไม้แต่งผิว
![hatch_wood](symbols/hatch_wood.png)
- AI อ่านว่า: Wavy horizontal wood-grain lines inside a box, labeled 'ไม้แต่งผิว'.
- [ ] ถูกต้อง
- [ ] แก้ไข: _____ (พิมพ์ "ตัดออก" = ไม่ต้องใช้สัญลักษณ์นี้เลย)

#### 12. ผนังกระจก
![hatch_glass_wall_plan](symbols/hatch_glass_wall_plan.png)
- AI อ่านว่า: A solid/filled black bar between two thin border lines (opaque, not hatched), labeled 'ผนังกระจก' — glass partition/wall in PLAN view.
- [ ] ถูกต้อง
- [ ] แก้ไข: _____ (พิมพ์ "ตัดออก" = ไม่ต้องใช้สัญลักษณ์นี้เลย)

#### 13. บานกระจก
![hatch_glass_section](symbols/hatch_glass_section.png)
- AI อ่านว่า: Evenly-spaced parallel diagonal hatch lines (single direction) inside a box, labeled 'บานกระจก' (แก้ไขโดยผู้ตรวจสอบ จากเดิม 'กระจก') — glass in SECTION view.
- [ ] ถูกต้อง
- [ ] แก้ไข: _____ (พิมพ์ "ตัดออก" = ไม่ต้องใช้สัญลักษณ์นี้เลย)

#### 14. ลูกศรความลาดเอียง
![slope_arrow](symbols/slope_arrow.png)
- AI อ่านว่า: A slope-direction arrow labeled 'แนวลาดเอียง SLOPE 1:200' with an arrowhead pointing in the downslope direction, used to indicate floor/roof slope direction and ratio.
- [ ] ถูกต้อง
- [ ] แก้ไข: _____ (พิมพ์ "ตัดออก" = ไม่ต้องใช้สัญลักษณ์นี้เลย)


### ข้อกำหนดสำคัญ (จากหน้าสเปค)
- กฎก่ออิฐ: ผนังทั่วไป เป็นผนังก่ออิฐมอญครึ่งแผ่น นอกเหนือจากนี้ให้ดูรายละเอียดในแบบแปลน; ทุกมุมผนัง ผนังจะต้องก่อหุ้มลอยๆ รอบวงกบประตู-หน้าต่าง ต้องมีเสาเอ็น คสล. โดยเสริมเหล็ก RB6 SR24 ในเสา/คาน ค.ส.ล. เสริมเหล็ก 2-RB9 SR24 เหล็กปลอก RB6 SR24 @0.20ม.
- ประเภทผนัง: ผ1=ผนังก่ออิฐบล็อก ฉาบปูนเรียบทาสี; ผ2=ผนังก่ออิฐบล็อก ผิวบุกระเบื้องเคลือบกรุผนัง ขนาด 8"x10" สูง 1.80 เมตร; ผ3=กรุผนังด้วย แผ่นผนังไม้สังเคราะห์ WPC (หรือกำหนดภายหลัง)
- ประเภทพื้น: F1=พื้นคอนกรีตเสริมเหล็ก ผิวปูกระเบื้องแกรนิตโต้ 24"x24"; F2=พื้นคอนกรีตเสริมเหล็ก ผิวปูกระเบื้องเคลือบกันลื่นห้องน้ำ 12"x12"; F3=พื้นคอนกรีตเสริมเหล็ก ผิวปูกระเบื้องเคลือบกันลื่นภายนอก 12"x12"; F4=พื้นระเบียง กรุไม้ปูระเบียง (รูปแบบกำหนดภายหลัง)
- ตำแหน่งรายละเอียดฝ้าชายคา/เชิงชาย: รายการฝ้าเพดาน-ฝ้าชายคา ให้ดูรายละเอียดในรูปตัด A-A, B-B
- หมายเหตุอื่น:
  - ระดับอาคาร: กำหนดให้ระดับผิวทางเท้าสาธารณบริเวณที่ก่อสร้างเป็น ±0.000; ระดับอื่นให้ถือตัวเลขระดับในแบบสถาปัตยกรรม
  - อัตราส่วนผสมปูนก่อฉาบทั่วไป ซีเมนต์:ปูนขาว:ทรายหยาบ = 1:1:2 โดยปริมาตร
  - ปูนฉาบทั่วไป ซีเมนต์:ปูนขาว:ทรายละเอียด = 1:1:5 โดยปริมาตร
  - ปูนผสมปูกระเบื้องเคลือบผนังและพื้น ซีเมนต์:ทรายละเอียด = 1:2 โดยปริมาตร
  - คอนกรีตโครงสร้างต้องมีกำลังอัด (Compressive Strength) ไม่น้อยกว่า 210 กก./ตร.ซม. (Cube)
  - อัตราส่วนผสมคอนกรีตโครงสร้าง ซีเมนต์:ทรายหยาบ:หินหรือกรวด = 1:2:4 โดยปริมาตร
  - อัตราส่วนผสมคอนกรีตหยาบ ซีเมนต์:ทรายหยาบ:หินหรือกรวด = 1:3:5 โดยปริมาตร
  - เหล็กเสริมต้องได้มาตรฐาน: เหล็กเส้นกลม SR24, เหล็กข้ออ้อย SD30
  - งานไฟฟ้าต้องเป็นไปตามมาตรฐานการไฟฟ้าส่วนภูมิภาค สำหรับอาคารพักอาศัย; สายไฟทองแดงหุ้มฉนวน PVC สีขาว ทนแรงดันไฟได้ถึง 600 VOLT
  - เต้ารับติดตั้งสูงจากพื้น 0.50 ม. (วัดจากพื้นถึงกึ่งกลางเต้ารับ); เต้ารับในห้องน้ำหรือเคาน์เตอร์ครัวสูง 1.00 ม.; สวิทช์สูง 1.30 ม.; Panel Board สูงถึงกึ่งกลางแป้นยึด 2.20 ม.
  - ทุกห้อง ทุกชั้น ต้องมี Circuit Breaker เป็นตัวตัดตอนเมื่อเกิดกระแสไฟฟ้าลัดวงจร
  - เครื่องสุขภัณฑ์และอุปกรณ์ประกอบให้ใช้ชนิดเคลือบขาว แบบมาตรฐาน
  - ท่อน้ำดีและอุปกรณ์ข้อต่อใช้ PVC สีฟ้า ชั้น 8.5 ตามมาตรฐาน มอก. 17/2532
  - ท่อน้ำเสีย-ท่อโสโครกใช้ PVC สีฟ้า ตามมาตรฐาน มอก. 17/2532
  - ขนาดท่อประปา-ท่อน้ำเสีย-ท่อโสโครก: ท่อประปาแยกจากท่อเมน เข้าอุปกรณ์ประปาในอาคาร ใช้ขนาด Ø 3/4"; ท่อน้ำเสียจากอ่างล้างหน้า/ซิงค์ใช้ Ø ตามรูปตัด; ท่อน้ำเสียจากอ่างล้างหน้า/ซิงค์และ Floor Drain ไปยังรางระบายน้ำและท่อโสโครกจากโถส้วมใช้ Ø 2"; ท่อโสโครกจากโถส้วมไปยังบ่อเกรอะและจากบ่อเกรอะไปยังบ่อซึมใช้ Ø 4"; ท่ออากาศ (Air Vent) ต่อจากท่อโสโครกระบายลมเหนือหลังคาใช้ Ø 1"

---

## ข้อมูลดิบ (ไพน้อยอ่านส่วนนี้ — แก้ไขตรงนี้ถ้าต้องแก้ ไม่มีไฟล์ .json แยกอีก)

```json
{
  "source_pdf": "แบบก่อสร้างอาคารบ้านพักชั้นเดี่ยว.pdf",
  "project_info": {
    "project_name": "แบบก่อสร้างอาคารบ้านพักอาศัยชั้นเดียว 3ห้องนอน 3ห้องน้ำ",
    "owner": "คุณ สิริกุล ฟุ้งกิตติกุล",
    "address": "บ้านยางทอง หมู่ที่ 4 ต.สันปูเลย อ.ดอยสะเก็ด จ.เชียงใหม่",
    "permit_no": "503/2568",
    "book_no": "",
    "permit_date": "12 มิ.ย. 2568",
    "notes": "เอกสารมีตราประทับเทศบาลตำบลสันปูเลยและลายเซ็นเจ้าหน้าที่หลายตำแหน่ง (ตรวจหลักฐาน, ตรวจสถานที่, ผู้อำนวยการกองช่าง, ปลัดเทศบาลตำบล, นายกเทศมนตรีตำบล) วันที่บนตราประทับไม่ชัดเจนบางส่วน อาจคลาดเคลื่อน"
  },
  "site_info": {
    "title_deed_no": "65978 (เล่มที่ 660 หน้า 78)",
    "land_parcel_ref": "ระวางที่ดิน 4846 IV 0880 เลขที่ดิน 2992 ตำบลสันปูเลย อำเภอดอยสะเก็ด จังหวัดเชียงใหม่",
    "site_elements_present": [
      "ที่จอดรถ (parking area with car symbols)",
      "ระบบระบายน้ำ (drainage system, per แบบสาธารณสุข)",
      "แนวต้นไม้/รั้วต้นไม้รอบพื้นที่ (tree line along boundary)",
      "อาคารหลัก/สิ่งปลูกสร้าง (main building outline with rooms)",
      "ทางเดิน/ลานอเนกประสงค์ (pathway/patio area)"
    ],
    "notes": "Site dimensions labeled around perimeter: 18.70, 4.78, 9.07, 44.16, 42.08, 25.58 m (units assumed meters). Adjacent plot/boundary reference numbers shown: 1844, 1999, 7053, 9368, 552, 2991. Scale 1:250. Permit stamp visible (ใบอนุญาต 503-2568, ลงวันที่ 12 พ.ย. 2568)."
  },
  "sheet_index_declared": [
    {
      "code": "A-01",
      "title": "ผังบริเวณ - แผนที่สังเขป",
      "discipline": "Architecture"
    },
    {
      "code": "A-02",
      "title": "สารบัญแบบ",
      "discipline": "Architecture"
    },
    {
      "code": "A-03",
      "title": "รายการประกอบแบบ",
      "discipline": "Architecture"
    },
    {
      "code": "A-04",
      "title": "แปลน พื้นอาคาร",
      "discipline": "Architecture"
    },
    {
      "code": "A-05",
      "title": "แปลน หลังคา",
      "discipline": "Architecture"
    },
    {
      "code": "A-06",
      "title": "รูปด้านที่ 1 - 2",
      "discipline": "Architecture"
    },
    {
      "code": "A-07",
      "title": "รูปด้านที่ 2 - 3",
      "discipline": "Architecture"
    },
    {
      "code": "A-08",
      "title": "รูปตัด A-A",
      "discipline": "Architecture"
    },
    {
      "code": "A-09",
      "title": "รูปตัด B-B",
      "discipline": "Architecture"
    },
    {
      "code": "A-10",
      "title": "แบบขยายประตู",
      "discipline": "Architecture"
    },
    {
      "code": "A-11",
      "title": "แบบขยายหน้าต่าง",
      "discipline": "Architecture"
    },
    {
      "code": "A-12",
      "title": "แบบขยายห้องน้ำ",
      "discipline": "Architecture"
    },
    {
      "code": "S-01",
      "title": "แปลน ฐานราก , เสาตอม่อ",
      "discipline": "Structural"
    },
    {
      "code": "S-02",
      "title": "แปลน เสา , คาน , และพื้น",
      "discipline": "Structural"
    },
    {
      "code": "S-03",
      "title": "แปลน โครงสร้างหลังคา - อะเส",
      "discipline": "Structural"
    },
    {
      "code": "S-04",
      "title": "ขยาย โครงสร้างหลังคา",
      "discipline": "Structural"
    },
    {
      "code": "S-05",
      "title": "แบบขยายฐานราก",
      "discipline": "Structural"
    },
    {
      "code": "S-06",
      "title": "แบบขยายเสา ฐานคลองราก",
      "discipline": "Structural"
    },
    {
      "code": "S-07",
      "title": "แบบขยายงานเสริมเหล็กคานทั่วไป",
      "discipline": "Structural"
    },
    {
      "code": "S-08",
      "title": "แบบขยายโครงสร้างคาน",
      "discipline": "Structural"
    },
    {
      "code": "S-09",
      "title": "แบบขยายโครงสร้างพื้น",
      "discipline": "Structural"
    },
    {
      "code": "E-01",
      "title": "แปลน ไฟฟ้า,สัญลักษณ์",
      "discipline": "Electrical"
    },
    {
      "code": "E-02",
      "title": "แปลน ไฟฟ้าส่องสว่าง",
      "discipline": "Electrical"
    },
    {
      "code": "E-03",
      "title": "แปลน ไฟฟ้ากำลัง",
      "discipline": "Electrical"
    },
    {
      "code": "SN-01",
      "title": "แบบสุขาภิบาลทั่วไป",
      "discipline": "Sanitary"
    },
    {
      "code": "SN-02",
      "title": "แบบแปลนน้ำดี",
      "discipline": "Sanitary"
    },
    {
      "code": "SN-03",
      "title": "แบบแปลนน้ำเสีย",
      "discipline": "Sanitary"
    },
    {
      "code": "SN-04",
      "title": "แบบขยายบ่อซึมน้ำเสีย บ่อเกรอะ - บ่อซึม",
      "discipline": "Sanitary"
    }
  ],
  "sheet_index_verified": {
    "1": "illegible",
    "2": "illegible",
    "3": "A-02",
    "4": "A-03",
    "5": "A-04",
    "6": "A-05",
    "7": "A-06",
    "8": "A-07",
    "9": "A-08",
    "10": "A-09",
    "11": "A-10",
    "12": "A-11",
    "13": "A-12",
    "14": "S-01",
    "15": "S-02",
    "16": "S-03",
    "17": "S-04",
    "18": "S-05",
    "19": "S-06",
    "20": "S-07",
    "21": "S-08",
    "22": "S-09",
    "23": "E-01",
    "24": "E-02",
    "25": "E-03",
    "26": "SN-01",
    "27": "SN-02",
    "28": "SN-03",
    "29": "illegible"
  },
  "sheet_index_mismatches": [],
  "legend_and_specs": {
    "brick_rule": "ผนังทั่วไป เป็นผนังก่ออิฐมอญครึ่งแผ่น นอกเหนือจากนี้ให้ดูรายละเอียดในแบบแปลน; ทุกมุมผนัง ผนังจะต้องก่อหุ้มลอยๆ รอบวงกบประตู-หน้าต่าง ต้องมีเสาเอ็น คสล. โดยเสริมเหล็ก RB6 SR24 ในเสา/คาน ค.ส.ล. เสริมเหล็ก 2-RB9 SR24 เหล็กปลอก RB6 SR24 @0.20ม.",
    "wall_types": {
      "ผ1": "ผนังก่ออิฐบล็อก ฉาบปูนเรียบทาสี",
      "ผ2": "ผนังก่ออิฐบล็อก ผิวบุกระเบื้องเคลือบกรุผนัง ขนาด 8\"x10\" สูง 1.80 เมตร",
      "ผ3": "กรุผนังด้วย แผ่นผนังไม้สังเคราะห์ WPC (หรือกำหนดภายหลัง)"
    },
    "floor_types": {
      "F1": "พื้นคอนกรีตเสริมเหล็ก ผิวปูกระเบื้องแกรนิตโต้ 24\"x24\"",
      "F2": "พื้นคอนกรีตเสริมเหล็ก ผิวปูกระเบื้องเคลือบกันลื่นห้องน้ำ 12\"x12\"",
      "F3": "พื้นคอนกรีตเสริมเหล็ก ผิวปูกระเบื้องเคลือบกันลื่นภายนอก 12\"x12\"",
      "F4": "พื้นระเบียง กรุไม้ปูระเบียง (รูปแบบกำหนดภายหลัง)"
    },
    "door_categories": {
      "D1": "ประตูบานเลื่อนเปิดอลูมิเนียม + บานติดตาย อุปกรณ์ครบชุด",
      "D2": "ประตูบานเปิดไม้ภายใน+ภายนอก พร้อมอุปกรณ์ครบชุด",
      "D3": "ประตูบานเปิด PVC พร้อมอุปกรณ์ครบชุด"
    },
    "window_categories": {
      "W1": "หน้าต่างบานเลื่อนสลับคู่",
      "W2": "หน้าต่างบานกระทุ้ง",
      "W3": "หน้าต่างบานกระทุ้ง ห้องน้ำ"
    },
    "eave_detail_location": "รายการฝ้าเพดาน-ฝ้าชายคา ให้ดูรายละเอียดในรูปตัด A-A, B-B",
    "other_notes": [
      "ระดับอาคาร: กำหนดให้ระดับผิวทางเท้าสาธารณบริเวณที่ก่อสร้างเป็น ±0.000; ระดับอื่นให้ถือตัวเลขระดับในแบบสถาปัตยกรรม",
      "อัตราส่วนผสมปูนก่อฉาบทั่วไป ซีเมนต์:ปูนขาว:ทรายหยาบ = 1:1:2 โดยปริมาตร",
      "ปูนฉาบทั่วไป ซีเมนต์:ปูนขาว:ทรายละเอียด = 1:1:5 โดยปริมาตร",
      "ปูนผสมปูกระเบื้องเคลือบผนังและพื้น ซีเมนต์:ทรายละเอียด = 1:2 โดยปริมาตร",
      "คอนกรีตโครงสร้างต้องมีกำลังอัด (Compressive Strength) ไม่น้อยกว่า 210 กก./ตร.ซม. (Cube)",
      "อัตราส่วนผสมคอนกรีตโครงสร้าง ซีเมนต์:ทรายหยาบ:หินหรือกรวด = 1:2:4 โดยปริมาตร",
      "อัตราส่วนผสมคอนกรีตหยาบ ซีเมนต์:ทรายหยาบ:หินหรือกรวด = 1:3:5 โดยปริมาตร",
      "เหล็กเสริมต้องได้มาตรฐาน: เหล็กเส้นกลม SR24, เหล็กข้ออ้อย SD30",
      "งานไฟฟ้าต้องเป็นไปตามมาตรฐานการไฟฟ้าส่วนภูมิภาค สำหรับอาคารพักอาศัย; สายไฟทองแดงหุ้มฉนวน PVC สีขาว ทนแรงดันไฟได้ถึง 600 VOLT",
      "เต้ารับติดตั้งสูงจากพื้น 0.50 ม. (วัดจากพื้นถึงกึ่งกลางเต้ารับ); เต้ารับในห้องน้ำหรือเคาน์เตอร์ครัวสูง 1.00 ม.; สวิทช์สูง 1.30 ม.; Panel Board สูงถึงกึ่งกลางแป้นยึด 2.20 ม.",
      "ทุกห้อง ทุกชั้น ต้องมี Circuit Breaker เป็นตัวตัดตอนเมื่อเกิดกระแสไฟฟ้าลัดวงจร",
      "เครื่องสุขภัณฑ์และอุปกรณ์ประกอบให้ใช้ชนิดเคลือบขาว แบบมาตรฐาน",
      "ท่อน้ำดีและอุปกรณ์ข้อต่อใช้ PVC สีฟ้า ชั้น 8.5 ตามมาตรฐาน มอก. 17/2532",
      "ท่อน้ำเสีย-ท่อโสโครกใช้ PVC สีฟ้า ตามมาตรฐาน มอก. 17/2532",
      "ขนาดท่อประปา-ท่อน้ำเสีย-ท่อโสโครก: ท่อประปาแยกจากท่อเมน เข้าอุปกรณ์ประปาในอาคาร ใช้ขนาด Ø 3/4\"; ท่อน้ำเสียจากอ่างล้างหน้า/ซิงค์ใช้ Ø ตามรูปตัด; ท่อน้ำเสียจากอ่างล้างหน้า/ซิงค์และ Floor Drain ไปยังรางระบายน้ำและท่อโสโครกจากโถส้วมใช้ Ø 2\"; ท่อโสโครกจากโถส้วมไปยังบ่อเกรอะและจากบ่อเกรอะไปยังบ่อซึมใช้ Ø 4\"; ท่ออากาศ (Air Vent) ต่อจากท่อโสโครกระบายลมเหนือหลังคาใช้ Ø 1\""
    ]
  },
  "drawing_notation": {
    "_verified_by_human_eye": "2026-08-29: section_marker/elevation_marker were swapped and 3 material_hatches entries (soil/glass_wall_plan/glass_section) were wrong in the original Sonnet read - corrected below by direct visual inspection of the source page at 400dpi.",
    "dimension_symbols": "Two independent grid-line label symbols: a circle enclosing a letter (e.g. 'A') for a lettered grid line, and a circle enclosing a number (e.g. '1') for a numbered grid line - both point to a crosshair marked 'แนวเสา' (column line). Along a dimension line between two grid marks: a plus-sign (+) crosshair at both ends = 'ระยะศูนย์กลางถึงศูนย์กลาง' (center-to-center); a plus-sign at one end + an X-mark at the other = 'ระยะศูนย์กลางถึงริม' (center-to-edge); an X-mark at both ends = 'ระยะริมถึงริม' (edge-to-edge).",
    "door_tag_symbol": "ตัดออกตามที่ผู้ตรวจสอบยืนยัน — ไม่ใช้สัญลักษณ์นี้เป็นข้อมูลอ้างอิง",
    "window_tag_symbol": "ตัดออกตามที่ผู้ตรวจสอบยืนยัน — ไม่ใช้สัญลักษณ์นี้เป็นข้อมูลอ้างอิง",
    "elevation_marker": "A cross/X-shaped marker of four triangular arrowheads pointing outward in 4 directions (positions 1,2,3,4), each triangle labeled 'A-NO' — '1,2,3,4 ชื่อรูปด้าน แสดงทิศทางตามแนวชี้บอก' (names the elevation view; arrow = viewing direction); 'A-NO' gives the sheet number where drawn.",
    "section_marker": "A single triangular flag containing a letter (e.g. 'A') above a small box labeled 'A-NO'. When captioned 'ชื่อรูปตัดอาคาร แผ่นที่ที่อ้างอิงไปถึง' this names a building SECTION and its sheet number. NOTE: the identical triangle+A-NO glyph is reused elsewhere on this page for 'แบบขยายทั่วไป' (general enlarged-detail callouts) - same shape, different meaning by context/caption, not by shape alone.",
    "north_symbol": "A compass rose with N (top), S (bottom), E (right), W (left) and a bold arrow/needle pointing to N — สัญลักษณ์แสดงทิศเหนือ.",
    "material_hatches": {
      "concrete": "Small irregular dot/speck stipple pattern inside a box, labeled 'คอนกรีต'.",
      "steel": "Evenly-spaced parallel diagonal hatch lines (single direction) inside a box, labeled 'เหล็ก'.",
      "soil": "Cross-hatch / basket-weave pattern (diagonal lines crossing in two directions) inside a box, labeled 'ดิน'. Visually distinct from concrete's dotted stipple and steel's single-direction diagonal - do not confuse the three in section drawings.",
      "wood": "Wavy horizontal wood-grain lines inside a box, labeled 'ไม้แต่งผิว'.",
      "brick_wall_plan": "Two horizontal lines with short vertical tick marks between them (brick-coursing symbol), labeled 'ผนังก่ออิฐมอญ' — brick masonry wall in PLAN view.",
      "glass_wall_plan": "A solid/filled black bar between two thin border lines (opaque, not hatched), labeled 'ผนังกระจก' — glass partition/wall in PLAN view.",
      "glass_section": "Evenly-spaced parallel diagonal hatch lines (single direction) inside a box, labeled 'บานกระจก' (แก้ไขโดยผู้ตรวจสอบ จากเดิม 'กระจก') — glass in SECTION view."
    },
    "other_symbols": [
      "A slope-direction arrow labeled 'แนวลาดเอียง SLOPE 1:200' with an arrowhead pointing in the downslope direction, used to indicate floor/roof slope direction and ratio."
    ]
  },
  "notation_symbol_boxes": [
    {
      "key": "dimension_symbols",
      "label_th": "ระยะ/แนวเสา",
      "bbox_pct": [
        0.605,
        0.118,
        0.845,
        0.212
      ],
      "image_path": "symbols/dimension_symbols.png"
    },
    {
      "key": "north_symbol",
      "label_th": "ทิศเหนือ",
      "bbox_pct": [
        0.615,
        0.393,
        0.682,
        0.482
      ],
      "image_path": "symbols/north_symbol.png"
    },
    {
      "key": "elevation_marker",
      "label_th": "รูปด้าน",
      "bbox_pct": [
        0.598,
        0.483,
        0.672,
        0.567
      ],
      "image_path": "symbols/elevation_marker.png"
    },
    {
      "key": "section_marker",
      "label_th": "รูปตัด",
      "bbox_pct": [
        0.614,
        0.57,
        0.758,
        0.626
      ],
      "image_path": "symbols/section_marker.png"
    },
    {
      "key": "hatch_glass_wall_plan",
      "label_th": "ผนังกระจก",
      "bbox_pct": [
        0.72,
        0.636,
        0.792,
        0.654
      ],
      "image_path": "symbols/hatch_glass_wall_plan.png"
    },
    {
      "key": "hatch_concrete",
      "label_th": "ลายคอนกรีต",
      "bbox_pct": [
        0.618,
        0.671,
        0.667,
        0.706
      ],
      "image_path": "symbols/hatch_concrete.png"
    },
    {
      "key": "hatch_glass_section",
      "label_th": "บานกระจก",
      "bbox_pct": [
        0.743,
        0.671,
        0.787,
        0.706
      ],
      "image_path": "symbols/hatch_glass_section.png"
    },
    {
      "key": "hatch_steel",
      "label_th": "ลายเหล็ก",
      "bbox_pct": [
        0.618,
        0.726,
        0.667,
        0.76
      ],
      "image_path": "symbols/hatch_steel.png"
    },
    {
      "key": "hatch_soil",
      "label_th": "ลายดิน",
      "bbox_pct": [
        0.743,
        0.726,
        0.787,
        0.76
      ],
      "image_path": "symbols/hatch_soil.png"
    },
    {
      "key": "hatch_wood",
      "label_th": "ลายไม้แต่งผิว",
      "bbox_pct": [
        0.618,
        0.777,
        0.667,
        0.806
      ],
      "image_path": "symbols/hatch_wood.png"
    },
    {
      "key": "slope_arrow",
      "label_th": "ลูกศรความลาดเอียง",
      "bbox_pct": [
        0.778,
        0.784,
        0.802,
        0.802
      ],
      "image_path": "symbols/slope_arrow.png"
    }
  ],
  "notation_symbol_overview_image": "symbols/_proposal_overview.png"
}
```
