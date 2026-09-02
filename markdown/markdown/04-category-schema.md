# Master CAD-Parsing & Search Schema (v2.0)

> **มาแทนที่ schema v1 เดิม (flat list ไม่มี keyword)** — โครงสร้างนี้เสนอโดยเจ้าของโปรเจกต์หลังลองให้ AI อ่านไฟล์ BOQ หลายไฟล์แล้วพบ pattern คล้ายกัน ออกแบบให้ "ไพน้อย" ใช้เป็นเข็มทิศกวาดหา text/entity ในไฟล์ CAD **โดยไม่ผูกติดกับชื่อโครงการใดโครงการหนึ่ง** และรองรับ dynamic append เพิ่มหมวดหมู่ในอนาคต — v1 เดิมยังดูได้ผ่าน `git log -- 04-category-schema.md` ไม่ต้องเก็บสำเนาไว้ในไฟล์เอง (ใช้ git แทน filename versioning ตามที่ตกลงกันไว้)

## หลักการทำงานร่วมกับเอกสารอื่น (สำคัญ — อย่าสับสน)

Schema นี้ตอบคำถาม **"เจอ text/layer นี้แล้ว ควรจัดเข้าหมวดไหน" (สัญญาณ → จัดหมวด)** ส่วน [07-drawing-signal-vs-noise.md](./07-drawing-signal-vs-noise.md) ตอบคำถามคนละข้อ **"เจอ layer/block นี้แล้ว ควรตัดทิ้งเลยไหม" (ขยะ → คัดออก)** ลำดับการทำงานจริงคือ:

1. รัน Layer Exclusion (denylist, [07-drawing-signal-vs-noise.md §5.2](./07-drawing-signal-vs-noise.md#5-️-กลไกที่ต้องสร้าง-ระบบคัดกรองขยะ-cad-cad-noise-filtering-engine)) ก่อนเสมอ — ตัดขยะที่รู้จักแล้วทิ้ง
2. สิ่งที่เหลือ เอามาเทียบกับ `keywords`/`cad_search_layers` ใน schema นี้ — ถ้าตรงกับหมวดไหนก็จัดเข้าหมวดนั้น (**ใช้ substring match แบบไม่สนตัวพิมพ์เล็ก-ใหญ่เป็นค่าเริ่มต้นเสมอ** — เจอ layer จริงชื่อ `f1`/`f2` ตัวเล็กในไฟล์ newhouse ทั้งที่ schema เขียน `F1`/`F2` ตัวใหญ่)
3. ที่ไม่ตรงทั้ง denylist และ schema นี้เลย → เข้ากอง "ไม่แน่ใจ-ต้องตรวจสอบ" ของ Drawing Readiness Report ([03-ai-boq-procedure.md](./03-ai-boq-procedure.md) Step 1.5) ไม่ใช่ทิ้งเงียบๆ และไม่ใช่เดาใส่หมวดใดหมวดหนึ่งไปเอง

⚠️ **schema นี้คือ schema การ "ค้นหา/จัดหมวดจาก CAD" (ตามลักษณะทางกายภาพของงาน) ไม่ใช่ schema การ "รวมยอดขึ้นใบ BOQ" (ตามธรรมเนียมบัญชี/การจ้างช่าง) — สองอย่างนี้อนุญาตให้ไม่ตรงกันได้** ดู §ถังบำบัด/บ่อพัก ด้านล่างเป็นตัวอย่างจริงที่สองมุมมองนี้ขัดกัน

## ผลตรวจสอบกับไฟล์จริง (`newhouse 2569.dxf`, 155 เลเยอร์) — คงไว้เป็นหลักฐาน ก่อนจะ apply กับไฟล์ที่สอง

หมวดหมู่/keyword ด้านล่างผ่านการเทียบกับชื่อเลเยอร์จริงที่เจอในไฟล์ ([LOG.md](./LOG.md)) แล้วเพิ่ม/แก้ตามช่องว่างที่พบ:

| พบว่า... | แก้/เพิ่มอะไร |
|---|---|
| เลเยอร์จริงใช้ `COLM` (ย่อ) ไม่ใช่ `COLUMN` เต็ม | เพิ่ม `COLM` เข้า `cad_search_layers` ของหมวด 1 |
| เลเยอร์จริงมี `Truss-1`, `Truss$0$Truss`, `STELL` (พิมพ์/ย่อจาก "steel") | เพิ่ม `TRUSS`, `STEEL`/`STELL` |
| Layer จริงใช้ `Wind-1`/`wind` (ย่อจาก "window") ไม่ใช่ `WINDOW` เต็ม | เพิ่ม `WIND` เข้า `cad_search_layers` ของหมวด 2 (⚠️ เสี่ยง false positive มากกว่า `WINDOW` เพราะสั้น ต้องระวัง) |
| เลเยอร์จริงชื่อ **`ประตู-หน้างต่าง`** — สะกดผิดจาก "หน้าต่าง" (มี ง เกิน) | หลักฐานจริงว่า **keyword ตรงตัวอักษรเป๊ะไม่พอ** — งานต่อไปควรพิจารณา fuzzy/edit-distance matching ไม่ใช่แค่ substring (ดู backlog) |
| เลเยอร์จริงใช้ `WC-DET`/`WC-OUT`/`WC-OUTL` (ย่อ "water closet") ไม่ใช่คำเต็ม | เพิ่ม `WC` เข้า `cad_search_layers` ของหมวด 3 |
| เลเยอร์จริงชื่อ `f1`/`f2` ตัวเล็กล้วน ตรงกับรหัสพื้น F1/F2 ในตาราง Legend ของ BOQ จริง | ยืนยันว่าต้อง case-insensitive matching เสมอ (ระบุไว้ข้างบนแล้ว) |
| เลเยอร์จริงมี `LAMP` (ดวงไฟ) แต่ schema เดิมไม่มี keyword อังกฤษคำนี้ | เพิ่ม `LAMP`/`LIGHT` เข้าหมวด 4 |
| หมวด 4/5/6 ในร่างเดิมไม่มี key `cad_search_layers` เลย (มีแต่หมวด 1-3) | เพิ่มให้ครบทุกหมวดเพื่อความสม่ำเสมอของโครงสร้าง (สำคัญถ้าจะเขียนโค้ดอ่าน schema นี้แบบ programmatic) |

### รอบที่ 2 — เขียน [classify_layers.py](./project/code/python/classify_layers.py) เทียบ schema กับ**ทุก**เลเยอร์/block ในไฟล์ (220 เลเยอร์ + 132 block จาก layer/block table ทั้งหมด ไม่ใช่แค่ที่มี geometry ใน modelspace)

| พบว่า... | แก้/เพิ่มอะไร |
|---|---|
| เลเยอร์จริงมี `CONCRETE`/`คอนกรีต`, `เหล็ก`, `ROOF` เป็นคำเดี่ยวๆ ที่ schema ไม่มี | เพิ่มเข้าหมวด 1 |
| เลเยอร์จริงมี `PUMP`, `PIPE`, `CW PIPE` (cold water pipe) ที่ schema ไม่มี | เพิ่มเข้าหมวด 3 (⚠️ `PIPE` เดี่ยวๆ กำกวมกับท่อน้ำยาแอร์ในหมวด 5 ได้ — เป็น soft keyword ต้องมีบริบทอื่นช่วยยืนยัน) |
| เลเยอร์จริงมี `SWITCH`, `BREAKER` (คำอังกฤษของ สวิตช์/เบรกเกอร์) ที่ schema มีแค่คำไทย | เพิ่มเข้าหมวด 4 |
| เลเยอร์จริงสะกดผิด `FLOOR DAIN` (ขาด R จาก "DRAIN") | เพิ่ม `FLOOR DRAIN` ที่สะกดถูกเข้าหมวด 3.4 — ไฟล์นี้จะยังไม่ถูกจับเพราะสะกดผิด เป็นหลักฐานอีกชิ้นที่ต้องมี fuzzy matching (เหมือนกรณี `ประตู-หน้างต่าง`) |
| เลเยอร์จริงสะกดผิด `HACTH`/`HATC` (สลับ/ขาดตัวอักษรจาก "HATCH") | เพิ่มเป็น known-typo เข้า Layer Exclusion denylist ตรงๆ (ไม่ใช่ schema นี้ เพราะเป็นขยะ ไม่ใช่สัญญาณ) |
| Layer/block ชื่อ `TREE`, `CAR`, `Furniture`, `Shrub 4`, `Human_01`, `corolla`, `TREE_P0x` ยืนยันซ้ำว่าเป็นของตกแต่ง | เพิ่ม `TREE`/`SHRUB`/`FURNITURE`/`CAR` เข้า Layer Exclusion denylist (ไม่ใช่ schema นี้) |
| Block ที่ขึ้นต้นด้วย `_` (เช่น `_Dot`, `_Origin`, `_Open30`, `_Open90`, `_Oblique`, `_DatumBlank`, `_DOTSMALL`) ล้วนเป็น block มาตรฐานของ AutoCAD เอง (หัวลูกศร dimension ฯลฯ) | เพิ่ม pattern `^_` เข้า Layer Exclusion (ไม่ใช่ขยะจากดราฟต์แมน แต่เป็นของ built-in ของโปรแกรมเอง) |
| **114 → 73 เลเยอร์ และ 111 → 67 block ยังคง "ไม่รู้จัก" หลังแก้ทั้งหมดข้างบนแล้ว** | บันทึกเป็น `pending_review` ด้านล่าง แบ่งเป็นกลุ่มตามระดับความมั่นใจ — ไม่เดาใส่หมวดไหนทั้งสิ้น |

### รอบที่ 3 — เจ้าของโปรเจกต์ยืนยัน + ตรวจสอบไฟล์เพิ่มเติมด้วย ATTDEF/INSERT/spatial-proximity (2569-08-23)

| พบว่า... | แก้/เพิ่มอะไร |
|---|---|
| `FD-1` = Floor Drain #1 (ยืนยันจากเจ้าของโปรเจกต์) | เพิ่ม `FD` เข้าหมวด 3.4 |
| `DR090SL1` ฯลฯ = รหัสรุ่นประตู (ยืนยัน) | เพิ่ม `DR` เข้าหมวด 2.4 |
| `CT002P`/`C805P`/`C805S` = รหัสสินค้า COTTO จริง (ยืนยัน) — แต่ตรวจ DXF แล้วพบว่า **ไฟล์เองไม่ได้กำกับความหมายไว้เลย** (ดูหมวด 3.5) | บันทึกเป็น confirmed vocabulary ภายนอก ไม่ใช่ keyword ในไฟล์นี้ — ระบบ `vocabulary_review.csv` (ดู [09-vocabulary-review-workflow.md](./09-vocabulary-review-workflow.md)) |
| ⚠️ **พบสำคัญ:** `CT002P` insert อยู่บนเลเยอร์ `WALL`, `C805P`/`DR090SL1` insert อยู่บนเลเยอร์ `DIM` — คนละเลเยอร์กับที่ชื่อบอก | ยืนยันว่า **ห้ามใช้ชื่อเลเยอร์ตัดสิน block/INSERT เด็ดขาด** ต้องดูชื่อ block เท่านั้น เพิ่ม `entity_type_warning` ใน schema แล้ว |
| `B-1`/`B-2` เป็น block definition ที่ไม่เคยถูก insert ใช้งานเลย (0 ครั้ง) | ยืนยันว่าไม่ต้องจัดหมวด ไม่กระทบ BOQ |
| `L1`/`L2`/`L3` เป็นชื่อ**เลเยอร์**จริงที่มี geometry (LWPOLYLINE เป็นหลัก) แต่ไม่มี text ช่วยบอกความหมายเลย | ยังต้องเปิดไฟล์ดูด้วยตา — คงไว้ใน `pending_review` |

## ⚠️ ข้อขัดแย้งที่พบจริง: ถังบำบัด/บ่อพัก ควรอยู่หมวดไหน

ร่างเดิมเสนอให้ `ถังบำบัด`/`บ่อพัก` อยู่ในหมวด **1 (โครงสร้าง)** เพราะเป็นงานเทคอนกรีต/เหล็กเสริมเหมือนงานโครงสร้างอื่น (มุมมอง "ทางกายภาพ") — แต่ [08-ground-truth-boq-validation.md](./08-ground-truth-boq-validation.md) ยืนยันจาก BOQ จริงว่ารายการนี้ถูกตีราคาอยู่ใน **หมวดงานสุขาภิบาล** (มุมมอง "บัญชี/การจ้างช่าง" — เป็นงานที่ช่างสุขาภิบาลทำ ไม่ใช่ช่างโครงสร้าง) **ตัดสินใจ:** ให้ keyword นี้อยู่ใน**หมวด 3 (สุขาภิบาล)** ของ schema นี้ ให้ตรงกับธรรมเนียมการตีราคาจริงที่มีหลักฐานยืนยันแล้ว ไม่ใช่ตามสัญชาตญาณทางกายภาพ — หมวด 1 คงไว้แค่หมายเหตุชี้ทางไปหมวด 3

```json
{
  "schema_version": "2.0",
  "description": "Master CAD-Parsing and Search Schema for Py-Noi Engine -- project-agnostic, supports dynamic append",
  "matching_rules": {
    "case_sensitive": false,
    "match_type": "substring for needles >=4 chars; token-prefix match for shorter needles (see pynoi_parser.py _token_aware_match -- prevents 'AC'/'DB' false-positives while still letting 'DIM' catch 'DIMENSION')",
    "on_no_match": "route to the Drawing Readiness Report 'unclassified' bucket (03-ai-boq-procedure.md Step 1.5) -- never silently drop or guess",
    "entity_type_warning": "⚠️ layer-name exclusion must NEVER be applied to INSERT (block reference) entities based on the layer they happen to sit on -- confirmed in newhouse 2569.dxf that real product blocks (CT002P, C805P, DR090SL1) are inserted on layers 'WALL' and 'DIM', not on any layer that names what they are. Classify INSERT entities by their BLOCK NAME only. See 07-drawing-signal-vs-noise.md §12."
  },
  "exclusion_rules": {
    "_comment": "⚠️ TWO TIERS (restructured 2569-08-23, see 07-drawing-signal-vs-noise.md §15) -- 'not relevant to BOQ' does NOT mean 'not relevant to the drawing.' Dimensions, grid lines, title blocks, specs, hatch patterns -- even site landscaping -- are legitimate, human-intended content of a real construction drawing. They must never be physically deleted, only skipped when summing BOQ quantities. Only quantity_exclusion is used for that skip (pynoi_parser.py / classify_layers.py). Physical deletion (clean_dxf.py) may ONLY use safe_to_delete: confirmed zero-value software-internal artifacts where deleting loses no real information at all.",
    "quantity_exclusion": {
      "_comment": "Skip these when summing BOQ quantities. Still real, legitimate drawing content -- NEVER delete.",
      "exact": [
        "0"
      ],
      "keywords": [
        "HATCH",
        "CONSTRUCT",
        "HELP",
        "VIEWPORT",
        "DIM",
        "GRID",
        "TITLE",
        "BORDER",
        "BODR",
        "NOTE",
        "FRAME",
        "LOGO",
        "SPEC",
        "TABLE",
        "TEXT",
        "SECTIONCUTEDGES",
        "BREAKLINE",
        "เส้นงาน",
        "เส้นบาง",
        "เส้นร่าง",
        "บอกขนาด",
        "หนังสือ",
        "อักษร",
        "HACTH",
        "HATC",
        "TREE",
        "SHRUB",
        "FURNITURE",
        "CAR"
      ],
      "patterns": [
        "^[0-9]+(\\.[0-9]+)?$"
      ]
    },
    "safe_to_delete": {
      "_comment": "Confirmed software-internal artifacts only -- AutoCAD's own auto-generated names, never human-authored content. DEFPOINTS is here (not quantity_exclusion) because it's forced non-plotting (verified plot=0) -- no human ever sees it printed, so removing it loses nothing. This is the ONLY list clean_dxf.py Pass 1 may delete from.",
      "keywords": [
        "DEFPOINTS"
      ],
      "patterns": [
        "^A\\$C[0-9A-Fa-f]+$",
        "^(ADCADD|AUDIT_|AVE_)",
        "^_"
      ]
    }
  },
  "master_categories": [
    {
      "code": "1",
      "name": "งานโครงสร้าง (Structural Works)",
      "cad_search_layers": [
        "STR",
        "STRUCT",
        "FOUNDATION",
        "COLUMN",
        "COLM",
        "BEAM",
        "TRUSS",
        "STEEL",
        "STELL",
        "CONCRETE",
        "ROOF"
      ],
      "keywords": [
        "เสาเข็ม",
        "เข็มเจาะ",
        "ฐานราก",
        "ตอม่อ",
        "เสา ค.ส.ล.",
        "คานคอดิน",
        "คานชั้น",
        "พื้นสำเร็จ",
        "พื้น ค.ส.ล.",
        "โครงสร้างหลังคา",
        "โครงหลังคา",
        "แนวหลังคา",
        "คอนกรีต",
        "เหล็ก",
        "กำแพงหลังคา"
      ],
      "sub_categories": [
        {
          "code": "1.1",
          "name": "งานเสาเข็มและฐานราก",
          "keywords": [
            "เสาเข็ม",
            "ฐานราก",
            "ตอม่อ",
            "ตัดหัวเข็ม"
          ]
        },
        {
          "code": "1.2",
          "name": "งานเสา คาน และผนังโครงสร้าง",
          "keywords": [
            "เสา",
            "คาน",
            "ผนังคอนกรีต",
            "คานคอดิน"
          ]
        },
        {
          "code": "1.3",
          "name": "งานพื้นโครงสร้าง",
          "keywords": [
            "พื้นสำเร็จ",
            "ไวร์เมท",
            "พื้น ค.ส.ล.",
            "slab"
          ]
        },
        {
          "code": "1.4",
          "name": "งานโครงสร้างหลังคา",
          "keywords": [
            "โครงหลังคา",
            "จันทัน",
            "อกไก่",
            "แป",
            "เหล็กรูปพรรณ",
            "truss"
          ]
        },
        {
          "code": "1.5",
          "name": "งานโครงสร้างใต้ดินและอื่นๆ",
          "keywords": [],
          "note": "⚠️ ถังบำบัด/บ่อพัก/บ่อดักไขมัน ย้ายไปอยู่หมวด 3 (สุขาภิบาล) แล้ว ตามธรรมเนียมการตีราคาจริงที่ยืนยันจาก 08-ground-truth-boq-validation.md แม้ทางกายภาพจะเป็นงานเทคอนกรีตก็ตาม -- ตั้งใจเว้นว่างไว้ตรงนี้ ไม่ใช่ลืมใส่"
        }
      ]
    },
    {
      "code": "2",
      "name": "งานสถาปัตย์ (Architectural Works)",
      "cad_search_layers": [
        "ARCH",
        "WALL",
        "DOOR",
        "WINDOW",
        "WIND",
        "FINISH",
        "CEILING"
      ],
      "keywords": [
        "ผนัง",
        "อิฐมอญ",
        "ฉาบปูน",
        "พื้นผิว",
        "กระเบื้อง",
        "ฝ้าเพดาน",
        "ประตู",
        "หน้าต่าง",
        "สี"
      ],
      "sub_categories": [
        {
          "code": "2.1",
          "name": "งานพื้นผิว (Flooring Finishes)",
          "keywords": [
            "F1",
            "F2",
            "F3",
            "F4",
            "กระเบื้องแกรนิตโต",
            "ปูนขัดมัน",
            "หินขัด"
          ]
        },
        {
          "code": "2.2",
          "name": "งานผนังและฉาบปูน",
          "keywords": [
            "ผนังอิฐ",
            "ฉาบปูน",
            "เอ็นทับหลัง",
            "ทาสี"
          ]
        },
        {
          "code": "2.3",
          "name": "งานฝ้าเพดาน",
          "keywords": [
            "ฝ้าฉาบเรียบ",
            "ยิปซั่ม",
            "ฝ้าทีบาร์",
            "ฝ้าใต้ชายคา"
          ]
        },
        {
          "code": "2.4",
          "name": "งานประตูและหน้าต่าง",
          "keywords": [
            "D1",
            "D2",
            "D3",
            "D4",
            "D5",
            "W1",
            "W2",
            "W3",
            "W4",
            "ประตู",
            "หน้าต่าง",
            "UPVC",
            "อลูมิเนียม",
            "DR"
          ],
          "note": "ยืนยันแล้วโดยเจ้าของโปรเจกต์ (2569-08-23): DR0xxSLx = รหัสรุ่นประตู (เช่น DR090SL1) -- DR เป็น 2 ตัวอักษร เสี่ยง false positive ปานกลาง ใช้ token-prefix match ช่วยลดความเสี่ยงแล้ว"
        },
        {
          "code": "2.5",
          "name": "งานตกแต่งและผิวเคลือบพิเศษ",
          "keywords": [
            "กรวดล้าง",
            "ทรายล้าง",
            "ระแนง",
            "บัวเชิงผนัง"
          ]
        },
        {
          "code": "2.6",
          "name": "งานสุขภัณฑ์และอุปกรณ์ห้องน้ำ",
          "keywords": [
            "สุขภัณฑ์",
            "อ่างล้างหน้า",
            "โถส้วม",
            "โถปัสสาวะ",
            "ฝักบัว",
            "ก๊อกน้ำ",
            "สะดืออ่าง",
            "ฟลอร์เดรน",
            "FLOOR DRAIN",
            "FD"
          ],
          "note": "ยืนยันแล้วโดยเจ้าของโปรเจกต์ (2569-08-30): สุขภัณฑ์เป็นงานสถาปัตย์ตามระเบียบราชการ -- หมวดนี้เป็นที่เดียวที่จัดเก็บตัวสุขภัณฑ์/อุปกรณ์ห้องน้ำ **รวมถึง floor drain (FD)** ด้วย (ย้ายมาจากหมวด 3.4 เดิม เพราะเป็นอุปกรณ์เสริมเหมือนก๊อกน้ำ/ฝักบัว ไม่ใช่ตัวระบบท่อ) หมวด 3 (สุขาภิบาล) เหลือแค่งานระบบท่อ/บ่อพัก ไม่รวมอุปกรณ์ใดๆเลย -- ⚠️ พบเลเยอร์จริงสะกดผิดเป็น 'FLOOR DAIN' (ขาด R) keyword ที่สะกดถูกจะไม่จับ instance นี้ ต้องแก้ด้วยตาหรือรอ fuzzy matching (ยืนยันแล้ว 2569-08-23: FD-1 = Floor Drain #1)"
        },
        {
          "code": "2.7",
          "name": "งานรั้วรอบโครงการ",
          "keywords": [
            "รั้ว",
            "เสาคอนกรีต",
            "ลวดหนาม"
          ]
        }
      ]
    },
    {
      "code": "3",
      "name": "งานระบบสุขาภิบาล (Sanitary System)",
      "cad_search_layers": [
        "SAN",
        "PLUMBING",
        "DRAIN",
        "WATER",
        "WC",
        "PUMP",
        "PIPE"
      ],
      "keywords": [
        "ท่อน้ำดี",
        "ท่อน้ำทิ้ง",
        "ท่อน้ำโสโครก",
        "ท่อน้ำฝน",
        "PVC",
        "ถังบำบัด",
        "บ่อพัก",
        "บ่อแมนโฮล",
        "บ่อดักไขมัน",
        "CW PIPE"
      ],
      "note": "⚠️ (2569-08-30) ตัดคำว่า 'สุขภัณฑ์'/'อ่างล้างหน้า'/'โถส้วม'/'floor drain' ออกจากหมวดนี้แล้ว -- เดิมซ้ำกับหมวด 2.6 เจ้าของโปรเจกต์ยืนยันว่าตัวสุขภัณฑ์และอุปกรณ์ห้องน้ำทุกชนิด (รวม floor drain) เป็นงานสถาปัตย์ (หมวด 2.6) ทั้งหมด หมวดนี้เหลือแค่ระบบท่อ/บ่อพัก/ถังบำบัด (โครงสร้างพื้นฐานงานสุขาภิบาล ไม่ใช่ตัวอุปกรณ์เลย) -- เดิมมีหมวดย่อย 3.4 'งานติดตั้งสุขภัณฑ์และอุปกรณ์' ยุบทิ้งแล้วเพราะเนื้อหาว่างเปล่าหลังย้าย FD ออก",
      "sub_categories": [
        {
          "code": "3.1",
          "name": "ระบบประปาน้ำดี",
          "keywords": [
            "ท่อน้ำดี",
            "ท่อ PVC ชั้น 13.5",
            "ปั๊มน้ำ",
            "ถังเก็บน้ำ",
            "PUMP",
            "CW PIPE"
          ]
        },
        {
          "code": "3.2",
          "name": "ระบบระบายน้ำเสียและโสโครก",
          "keywords": [
            "ท่อน้ำทิ้ง",
            "ท่อน้ำโสโครก",
            "Vent Pipe",
            "ถังบำบัด",
            "บ่อแมนโฮล"
          ]
        },
        {
          "code": "3.3",
          "name": "ระบบระบายน้ำฝน",
          "keywords": [
            "ท่อน้ำฝน",
            "ระบายน้ำระเบียง"
          ]
        },
        {
          "code": "3.5",
          "name": "รหัสสินค้าแบรนด์ COTTO (ยืนยันแล้วว่าเป็นสัญญาณ ไม่ใช่ของตกแต่ง)",
          "keywords": [],
          "note": "⚠️ ยืนยันโดยเจ้าของโปรเจกต์ (2569-08-23) ว่า CT002P/C805P/C805S คือรหัสสุขภัณฑ์แบรนด์ COTTO จริง -- **แต่ตรวจสอบไฟล์ DXF แล้วพบว่า schema/รหัสนี้ไม่ได้ถูกกำกับความหมายไว้ในไฟล์เองเลย**: block definition ของ CT002P ไม่มี ATTDEF/ข้อความอธิบายใดๆ (มีแต่เส้น), C805P มี ATTDEF tag='SERIAL' default='C805' (แค่หมายเลขซีเรียล ไม่ใช่ชื่อสินค้า) และไม่พบ text 'CT002P'/'C805P' ที่ไหนในแบบเลย มีแค่ MTEXT บอกชื่อรุ่นแบบหลวมๆ ('COTTO DOS MEDIA', 'COTTO DOS FLEX 100') วางอยู่ *ใกล้ๆ* กลุ่ม block เหล่านี้บนเลเยอร์ DIM (ไม่ได้ผูกกับ block ไหนเจาะจงทาง data) -- สรุปว่า **โค้ดนี้ไม่มีทางรู้ความหมายที่แน่นอนได้จากไฟล์เพียงอย่างเดียว ต้องมี vocabulary ภายนอกที่มนุษย์ยืนยันไว้ล่วงหน้า** (ดู 09-vocabulary-review-workflow.md) รหัสสั้นเกินกว่าจะเขียนเป็น keyword ที่ปลอดภัย จึงไม่เพิ่มเป็น keyword ตรงๆ แต่บันทึกไว้ในระบบ vocabulary_review.csv แทน"
        }
      ]
    },
    {
      "code": "4",
      "name": "งานระบบไฟฟ้า (Electrical System)",
      "cad_search_layers": [
        "ELEC",
        "ELECT",
        "DB",
        "MDB",
        "LP",
        "LIGHT",
        "LAMP"
      ],
      "keywords": [
        "หม้อแปลง",
        "MDB",
        "DB",
        "LP",
        "ดวงโคม",
        "สวิตช์",
        "SWITCH",
        "เต้ารับ",
        "ท่อร้อยสาย",
        "สายไฟ",
        "Fire Alarm",
        "โทรศัพท์",
        "กล้องวงจรปิด",
        "เบรกเกอร์",
        "BREAKER"
      ],
      "sub_categories": [
        {
          "code": "4.1",
          "name": "งานระบบไฟฟ้าแรงสูงและหม้อแปลง",
          "keywords": [
            "หม้อแปลง",
            "แรงสูง",
            "PEA",
            "M.E.A"
          ]
        },
        {
          "code": "4.2",
          "name": "งานระบบไฟฟ้าแรงต่ำและตู้ควบคุม",
          "keywords": [
            "MDB",
            "DB",
            "LP",
            "ตู้โหลด",
            "เบรกเกอร์",
            "BREAKER"
          ]
        },
        {
          "code": "4.3",
          "name": "งานระบบแสงสว่างและกำลัง",
          "keywords": [
            "ดวงโคม",
            "LAMP",
            "LED",
            "สวิตช์",
            "SWITCH",
            "เต้ารับ",
            "ท่อ EMT",
            "ท่อ uPVC"
          ]
        },
        {
          "code": "4.4",
          "name": "งานระบบสื่อสารและป้องกันภัย",
          "keywords": [
            "Fire Alarm",
            "โทรศัพท์",
            "WIFI",
            "CCTV"
          ]
        }
      ]
    },
    {
      "code": "5",
      "name": "งานระบบปรับอากาศและระบายอากาศ (Air Conditioning & Ventilation)",
      "cad_search_layers": [
        "AC",
        "HVAC",
        "FCU",
        "CDU",
        "DUCT"
      ],
      "keywords": [
        "เครื่องปรับอากาศ",
        "FCU",
        "CDU",
        "สารทำความเย็น",
        "ท่อทองแดง",
        "ท่อน้ำทิ้งแอร์",
        "ท่อลม",
        "Air Duct"
      ],
      "sub_categories": [
        {
          "code": "5.1",
          "name": "ชุดปรับอากาศ",
          "keywords": [
            "FCU",
            "CDU",
            "Wall Type",
            "Ceiling Type"
          ]
        },
        {
          "code": "5.2",
          "name": "ท่อและระบบสารทำความเย็น",
          "keywords": [
            "ท่อทองแดง",
            "ฉนวนหุ้มท่อ",
            "น้ำยาแอร์"
          ]
        },
        {
          "code": "5.3",
          "name": "ท่อลมและระบบระบายอากาศ",
          "keywords": [
            "ท่อลม",
            "Air Duct",
            "Exhaust Fan",
            "พัดลมดูดอากาศ"
          ]
        }
      ]
    },
    {
      "code": "6",
      "name": "งานเตรียมการและบริหารโครงการ (Preliminaries)",
      "cad_search_layers": [
        "PRELIM",
        "TEMP",
        "SITE",
        "SIGN"
      ],
      "keywords": [
        "ควบคุมงาน",
        "สำนักงานชั่วคราว",
        "รั้วชั่วคราว",
        "ค่าน้ำไฟชั่วคราว",
        "ทดสอบดิน",
        "Shop Drawing",
        "นั่งร้าน",
        "ทำความสะอาด",
        "ขนขยะ",
        "เคลียร์พื้นที่"
      ],
      "sub_categories": [
        {
          "code": "6.1",
          "name": "บุคลากรควบคุมงาน",
          "keywords": [
            "วิศวกร",
            "สถาปนิก",
            "โฟเมน",
            "จป."
          ]
        },
        {
          "code": "6.2",
          "name": "สิ่งอำนวยความสะดวกและงานชั่วคราว",
          "keywords": [
            "สำนักงานชั่วคราว",
            "รั้วชั่วคราว",
            "น้ำไฟชั่วคราว",
            "นั่งร้าน",
            "สแลน",
            "ทำความสะอาด",
            "ขนขยะ",
            "เคลียร์พื้นที่"
          ]
        },
        {
          "code": "6.3",
          "name": "ค่าใช้จ่ายสนามและเอกสารวิศวกรรม",
          "keywords": [
            "ทดสอบดิน",
            "Shop Drawing",
            "As-Built",
            "ค่าวางผัง"
          ]
        }
      ]
    },
    {
      "code": "7",
      "name": "งานเบ็ดเตล็ด (Miscellaneous)",
      "cad_search_layers": [],
      "keywords": [],
      "note": "⚠️ เพิ่มเป็นหมวดที่ 7 ตามที่เจ้าของโปรเจกต์ยืนยัน (2569-08-30) เพื่อให้ครบ 7 หมวดมาตรฐานที่ใช้ถอดแบบจริง -- **ยังไม่มี keyword/cad_search_layers เพราะยังไม่มีหลักฐานจริงจากไฟล์ CAD หรือ BOQ ยืนยันว่าอะไรควรอยู่หมวดนี้บ้าง** (ต่างจากหมวด 1-6 ที่ผ่านการเทียบกับ newhouse 2569.dxf และ BOQ จริงมาแล้ว) ห้ามเดาใส่ keyword เอง -- รอตัวอย่างจริงจากโปรเจกต์ถัดไป หรือให้เจ้าของโปรเจกต์ยืนยันรายการที่เคยเจอในงานจริงก่อน (เช่น ค่าประกันภัยงานก่อสร้าง, งานที่ไม่เข้าหมวดใดเลย ฯลฯ)",
      "sub_categories": []
    }
  ],
  "pending_review": [
    {
      "group": "possible_missing_category",
      "names": [
        "KITCHEN",
        "KITCHEN2"
      ],
      "hypothesis": "งานเคาน์เตอร์/ตู้ครัวบิลท์อิน -- ไม่มีหมวดใดรองรับตอนนี้เลย อาจต้องเป็นหมวดย่อยใหม่ใต้ 2 (สถาปัตย์) ไม่ใช่แค่เพิ่ม keyword",
      "status": "needs_decision"
    },
    {
      "group": "possible_missing_category",
      "names": [
        "GAS"
      ],
      "hypothesis": "ระบบท่อแก๊ส -- ไม่มีหมวดใดรองรับเลยแม้แต่หมวดเดียว อาจเป็นทั้ง trade ที่ schema ยังไม่ครอบคลุม ไม่ใช่แค่ keyword เดียว",
      "status": "needs_decision"
    },
    {
      "group": "possible_missing_category",
      "names": [
        "Parking",
        "Road",
        "Ramp-2",
        "Set Back"
      ],
      "hypothesis": "งานภายนอกอาคาร/ที่จอดรถ/ถนน -- ไม่มีหมวด 'งานภายนอก/civil work' เลย อาจต้องเพิ่มหมวดใหม่ ไม่ใช่ยัดเข้าหมวดเตรียมการ",
      "status": "needs_decision"
    },
    {
      "group": "likely_decorative_landscaping_library",
      "names": [
        "TF0052P-Enthoven",
        "TF0504P-Acacia",
        "TF2088P-Plaza",
        "TF2310F",
        "TS303AXS",
        "TS304AS",
        "TS601P",
        "PM751P",
        "PM753P",
        "ts103bxf",
        "ts303af"
      ],
      "hypothesis": "รูปแบบชื่อ + คำต่อท้ายเป็นชื่อพันธุ์พืช (Acacia, Plaza) เดาว่าเป็น library ต้นไม้/พุ่มไม้ตกแต่งเว็บไซต์ (TF=Tree Foliage?, TS=Tree Species?, PM=Palm?) -- BOQ จริงที่ตรวจแล้วไม่มีรายการงานภูมิทัศน์เลย ทำให้เดาว่าเป็นของตกแต่งไม่ใช่รายการที่ต้องตีราคา แต่ยังไม่ยืนยัน 100% ห้าม auto-exclude จนกว่าจะเช็คด้วยตา",
      "status": "needs_decision"
    },
    {
      "group": "confirmed_brand_product_codes",
      "names": [
        "CT002P",
        "C805P",
        "C805S"
      ],
      "hypothesis": "ยืนยันแล้ว (2569-08-23): รหัสสินค้าแบรนด์ COTTO จริง -- ดูรายละเอียดเต็ม (รวมเหตุผลว่าทำไมไม่เขียนเป็น keyword ตรงๆ) ในหมวด 3.5 ด้านบน",
      "status": "confirmed_tracked_in_vocabulary_csv",
      "closed_out_2569-08-23": {
        "note": "แทนที่จะไล่ยืนยันทีละรหัส (ไม่ scale ข้ามโครงการ) ใช้หลักฐาน geometric+spatial-proximity (investigate_terms.py) ตัดสินตามเกณฑ์หลักฐานใน 07-drawing-signal-vs-noise.md §14 แทน -- ปิดกลุ่มนี้แล้ว ไม่ไล่ต่อทีละตัว",
        "corroborated_ok_to_treat_as_signal_via_layer": ["C106P", "C112S", "C814F", "C814S"],
        "corroborated_high_confidence": ["C812F"],
        "unused_block_definitions_irrelevant": ["C053S", "CT158AP", "CT767S", "ct1113ap"],
        "inconsistent_with_sanitary_hypothesis_do_not_assume": ["c0156f", "c805f", "ct268f"],
        "confirmed_single_drafter_mistake_this_file_only_not_a_pattern": ["ct0150p"]
      }
    },
    {
      "group": "confirmed_door_hardware_codes",
      "names": [
        "DR090SL1",
        "DR090SL2",
        "DR100SL9",
        "dr080sl2",
        "dr080sl3"
      ],
      "hypothesis": "ยืนยันแล้ว (2569-08-23): เป็นรหัสรุ่นประตู -- เพิ่ม keyword 'DR' เข้าหมวด 2.4 แล้ว",
      "status": "confirmed",
      "related_unconfirmed_similar_pattern": [
        "d01"
      ]
    },
    {
      "group": "ambiguous_structural_or_level",
      "names": [
        "B-3",
        "LEV-1",
        "level",
        "L",
        "L1",
        "L2",
        "L3"
      ],
      "hypothesis": "LEV/level=ชั้น/ระดับอาคาร?, L1-L3=หมายเลขชั้นหรือ Line? -- ตรวจสอบแล้วว่า L1/L2/L3 เป็นชื่อ**เลเยอร์**ที่มี geometry จริง (L1: 63 entities, L2: 18, L3: 5 -- ส่วนใหญ่เป็น LWPOLYLINE) แต่ไม่มี TEXT/MTEXT อยู่บนเลเยอร์เหล่านั้นเลยที่จะช่วยบอกความหมาย ต้องเปิดดูตำแหน่ง/รูปทรงจริงถึงจะรู้ -- B-3 เป็นชื่อ **block** ที่ insert จริง 3 ครั้งบนเลเยอร์ '0' (เลเยอร์ default ที่ไม่น่าเชื่อถือ) เดาว่า B=Beam แต่ยังไม่ยืนยัน",
      "status": "needs_decision"
    },
    {
      "group": "confirmed_unused_block_definitions",
      "names": [
        "B-1",
        "B-2"
      ],
      "hypothesis": "ตรวจสอบแล้ว (2569-08-23): block ทั้งสองนี้มีอยู่ใน block table ของไฟล์ แต่ **ไม่เคยถูก insert ใช้งานจริงในแบบเลยแม้แต่ครั้งเดียว** (0 INSERT ใน modelspace) -- เป็นซากจาก block library ที่ import เข้ามาเฉยๆ ไม่ต้องจัดหมวดหรือกังวล ไม่มีผลต่อ BOQ",
      "status": "confirmed_ignore"
    },
    {
      "group": "too_cryptic_needs_visual_inspection",
      "names": [
        "ARE",
        "ARR",
        "ASHADE",
        "BODY",
        "BX",
        "Bubble",
        "CEN",
        "CON",
        "DC",
        "DI",
        "DO",
        "ELEV",
        "ET",
        "FIXT",
        "FRAM",
        "HA",
        "HEAD",
        "ID-LOOSE",
        "INTERIOR",
        "METER",
        "OUT",
        "SEC",
        "SLIDE",
        "SPACE",
        "STAIR",
        "Stair-1",
        "STIR",
        "SYMB",
        "SYMBOL",
        "WAST",
        "CO",
        "WA",
        "AW",
        "Z",
        "S-BBUP",
        "TP-22",
        "VRH_FUVHU-W002AS_100 x100",
        "DI-E",
        "DIAGRAM"
      ],
      "hypothesis": "ไม่มี hypothesis ที่มั่นใจพอจะเขียน -- ต้องเปิดไฟล์ดูตำแหน่ง/รูปทรงจริงในโปรแกรม CAD ก่อน",
      "status": "needs_visual_inspection"
    },
    {
      "group": "meaningless_scratch_names",
      "names": [
        "aaa",
        "bbb",
        "hh",
        "kkkhf",
        "fwd",
        "l",
        "room1",
        "e1",
        "h1",
        "tex 1.",
        "134-0.09",
        "01___PRT_ALL_DTM_PLN",
        "02___PRT_ALL_AXES",
        "DEFAULT_1",
        "GENERAL-010",
        "LAYER2",
        "LAYER4",
        "LAYER5",
        "LAYER_1"
      ],
      "hypothesis": "ชื่อทดสอบ/placeholder ที่ดราฟต์แมนพิมพ์ทิ้งไว้ระหว่างทำงาน ไม่น่ามีเนื้อหาที่ตั้งใจ แต่ต้องยืนยันว่าไม่มี geometry สำคัญแอบอยู่ก่อน จะสรุปว่าไม่มีวันมี pattern ให้เขียน keyword จับได้ -- ต้องดูด้วยตาเสมอ ไม่ใช่แค่ไฟล์นี้",
      "status": "needs_visual_inspection"
    }
  ]
}
```

> ⚠️ **ยังไม่ยืนยัน:** ตำแหน่งของหมวด "งานเตรียมการ" ในไฟล์นี้ (code `6`, ท้ายสุด) **ไม่ได้แก้ปัญหาที่พบใน [08-ground-truth-boq-validation.md §3](./08-ground-truth-boq-validation.md#3-️-จุดที่ไม่ตรง-1-งานเตรียมการ-ไม่ใช่หมวดระดับบนในการคิดราคาจริง)** — BOQ จริงคิดราคารายการนี้เป็นหมวดย่อยซ้อนในโครงสร้าง ไม่ใช่หมวดใหญ่แยก ไม่ว่าจะอยู่ตำแหน่ง code ไหนก็ตาม schema นี้ (สำหรับค้นหา/จัดหมวดจาก CAD) ยังคงแยกเป็นหมวดใหญ่เพราะมีประโยชน์ตอนกวาดหาข้อมูล แต่ **ตอน assemble เป็น BOQ ราคาจริงปลายทาง** ต้องมีตรรกะแยกต่างหากว่าจะซ้อนหมวดนี้เข้าไปในโครงสร้างหรือไม่ — ยังไม่ตัดสินใจ ดู [BACKLOG.md](./BACKLOG.md)
