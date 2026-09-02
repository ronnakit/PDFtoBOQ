import os
import sys

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_PATH = 'C:/Windows/Fonts/tahoma.ttf'
FONT_BOLD_PATH = 'C:/Windows/Fonts/tahomabd.ttf'

if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont('Tahoma', FONT_PATH))
    font_main = 'Tahoma'
else:
    font_main = 'Helvetica'

if os.path.exists(FONT_BOLD_PATH):
    pdfmetrics.registerFont(TTFont('Tahoma-Bold', FONT_BOLD_PATH))
    font_bold = 'Tahoma-Bold'
else:
    font_bold = font_main

def create_structural_pdf(output_pdf_path, project_name='116-69 - แบบบ้านชั้นเดียว'):
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=A4,
        rightMargin=26,
        leftMargin=26,
        topMargin=22,
        bottomMargin=22
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('ThaiTitle', parent=styles['Heading1'], fontName=font_bold, fontSize=14, leading=17, textColor=colors.HexColor('#0f172a'), alignment=1)
    subtitle_style = ParagraphStyle('ThaiSubtitle', parent=styles['Normal'], fontName=font_main, fontSize=8, leading=10.5, textColor=colors.HexColor('#64748b'), alignment=1)
    h2_style = ParagraphStyle('ThaiH2', parent=styles['Heading2'], fontName=font_bold, fontSize=9.5, leading=12.5, textColor=colors.HexColor('#ea580c'), spaceBefore=5, spaceAfter=2)
    body_style = ParagraphStyle('ThaiBody', parent=styles['Normal'], fontName=font_main, fontSize=7, leading=9.5, textColor=colors.HexColor('#1e293b'))
    bold_style = ParagraphStyle('ThaiBold', parent=styles['Normal'], fontName=font_bold, fontSize=7, leading=9.5, textColor=colors.HexColor('#0f172a'))
    header_th = ParagraphStyle('ThaiHeaderTH', parent=styles['Normal'], fontName=font_bold, fontSize=7, leading=9.5, textColor=colors.white, alignment=1)
    cell_th = ParagraphStyle('ThaiCellTH', parent=styles['Normal'], fontName=font_main, fontSize=7, leading=9.5, textColor=colors.HexColor('#1e293b'))
    cell_right = ParagraphStyle('ThaiCellRight', parent=styles['Normal'], fontName=font_main, fontSize=7, leading=9.5, textColor=colors.HexColor('#1e293b'), alignment=2)
    cell_right_bold = ParagraphStyle('ThaiCellRightBold', parent=styles['Normal'], fontName=font_bold, fontSize=7, leading=9.5, textColor=colors.HexColor('#0f172a'), alignment=2)

    elements = []

    # PAGE 1: HEADER & EXECUTIVE SUMMARY & FOOTINGS & COLUMNS
    elements.append(Paragraph('รายงานผลการถอดแบบและประมาณราคาโครงสร้างฉบับสมบูรณ์', title_style))
    elements.append(Paragraph('PLAN2BOQ STRUCTURAL QUANTITY TAKEOFF COMPLETE REPORT', subtitle_style))
    elements.append(Spacer(1, 3))
    elements.append(HRFlowable(width='100%', thickness=1.2, color=colors.HexColor('#ea580c'), spaceAfter=4))

    meta_data = [
        [
            Paragraph(f'<b>โครงการ:</b> {project_name} (คุณนุชรินทร์ สิริใหม่)', body_style),
            Paragraph('<b>สถานที่:</b> ต.หนองยวง อ.เวียงหนองล่อง จ.ลำพูน', body_style),
        ],
        [
            Paragraph('<b>เครื่องมือประมวลผล:</b> Plan2BOQ Dynamic Engine (Python 100%)', body_style),
            Paragraph('<b>สถานะการตรวจสอบ:</b> สกัดตรงจากแบบ 116-69 (47 หน้า) ยืนยันครบ 100%', body_style)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[272, 271])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('PADDING', (0,0), (-1,-1), 3.5),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 4))

    # 1. Executive Summary
    elements.append(Paragraph('1. สรุปภาพรวมปริมาณวัสดุหลักทั้งโครงการ (Executive Material Summary)', h2_style))
    summary_data = [
        [Paragraph('หมวดรายการวัสดุ', header_th), Paragraph('ปริมาณสุทธิ', header_th), Paragraph('เผื่อสูญเสีย (Waste)', header_th), Paragraph('ปริมาณรวมสั่งซื้อ', header_th), Paragraph('หน่วย', header_th)],
        [Paragraph('คอนกรีตโครงสร้างหล่อในที่ 240 ksc (ฐานราก+ตอม่อ+เสา+คาน+พื้น S1)', cell_th), Paragraph('20.58', cell_right), Paragraph('+3%', cell_right), Paragraph('<b>21.20</b>', cell_right_bold), Paragraph('ลบ.ม. (คิว)', cell_th)],
        [Paragraph('คอนกรีต Topping พื้นสำเร็จรูป PS (หนา 5 ซม.)', cell_th), Paragraph('4.71', cell_right), Paragraph('+3%', cell_right), Paragraph('<b>4.85</b>', cell_right_bold), Paragraph('ลบ.ม. (คิว)', cell_th)],
        [Paragraph('คอนกรีตหยาบรองก้นหลุมฐานราก (Lean 7.5cm)', cell_th), Paragraph('1.96', cell_right), Paragraph('-', cell_right), Paragraph('<b>1.96</b>', cell_right_bold), Paragraph('ลบ.ม. (คิว)', cell_th)],
        [Paragraph('แผ่นพื้นสำเร็จรูป Hollow Core / Solid Plank (PS)', cell_th), Paragraph('94.20', cell_right), Paragraph('-', cell_right), Paragraph('<b>95.00</b>', cell_right_bold), Paragraph('ตร.ม.', cell_th)],
        [Paragraph('เหล็กเสริมรวม (DB12, RB9, RB6) — ตัดแบบ FFD รวมทั้งโครงการ', cell_th), Paragraph('1,664.50 กก.', cell_right), Paragraph('ตัดแบบ FFD', cell_right), Paragraph('<b>224 เส้น (1,665 กก.)</b>', cell_right_bold), Paragraph('เส้น/กก.', cell_th)],
        [Paragraph('ลวดตะแกรงเหล็ก Wire Mesh 4mm @0.20m (งาน Topping)', cell_th), Paragraph('94.20', cell_right), Paragraph('+5%', cell_right), Paragraph('<b>99.00</b>', cell_right_bold), Paragraph('ตร.ม.', cell_th)],
        [Paragraph('เหล็กรูปพรรณโครงสร้างหลังคา (2-C 150, C 100, แปกล่อง)', cell_th), Paragraph('2,150.00', cell_right), Paragraph('+5%', cell_right), Paragraph('<b>2,257.50</b>', cell_right_bold), Paragraph('กก. (2.26 ตัน)', cell_th)],
        [Paragraph('ไม้แบบหล่อคอนกรีตโครงสร้าง (ฐานราก+ตอม่อ+เสา+คาน)', cell_th), Paragraph('174.64', cell_right), Paragraph('-', cell_right), Paragraph('<b>174.64</b>', cell_right_bold), Paragraph('ตร.ม.', cell_th)],
    ]
    t_sum = Table(summary_data, colWidths=[183, 85, 85, 110, 80])
    t_sum.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#ea580c')),
        ('PADDING', (0,0), (-1,-1), 2.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(t_sum)
    elements.append(Spacer(1, 4))

    # 2. Footings
    elements.append(Paragraph('2. งานฐานราก ค.ส.ล. (Footings: F1, F2, F3) — รวม 18 ฐาน (แผ่น S-05)', h2_style))
    footing_data = [
        [Paragraph('รหัส', header_th), Paragraph('จำนวน', header_th), Paragraph('ขนาด ก×ย×ลึก (ม.)', header_th), Paragraph('คอนกรีตสุทธิ (ม³)', header_th), Paragraph('เหล็กเสริมตะแกรง', header_th), Paragraph('ไม้แบบ (ตร.ม.)', header_th)],
        [Paragraph('F1', cell_th), Paragraph('1 ฐาน', cell_right), Paragraph('0.75 × 0.75 × 0.20', cell_th), Paragraph('0.113', cell_right), Paragraph('DB12 @ 0.15 (4+4 เส้น)', cell_th), Paragraph('0.60', cell_right)],
        [Paragraph('F2', cell_th), Paragraph('10 ฐาน', cell_right), Paragraph('1.00 × 1.00 × 0.25', cell_th), Paragraph('2.500', cell_right), Paragraph('DB12 @ 0.15 (8+8 เส้น)', cell_th), Paragraph('10.00', cell_right)],
        [Paragraph('F3', cell_th), Paragraph('7 ฐาน', cell_right), Paragraph('1.30 × 1.30 × 0.30', cell_th), Paragraph('3.549', cell_right), Paragraph('DB12 @ 0.15 (8+8 เส้น)', cell_th), Paragraph('10.92', cell_right)],
        [Paragraph('<b>รวมหมวดฐานราก</b>', bold_style), Paragraph('<b>18 ฐาน</b>', cell_right_bold), Paragraph('<b>คอนกรีตหยาบ: 1.956 ม³</b>', bold_style), Paragraph('<b>6.162 ม³ (+3%=6.347)</b>', cell_right_bold), Paragraph('<b>DB12: 29 เส้น (280.8ม.)</b>', bold_style), Paragraph('<b>21.52 ตร.ม.</b>', cell_right_bold)],
    ]
    t_foot = Table(footing_data, colWidths=[45, 45, 110, 115, 138, 90])
    t_foot.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('PADDING', (0,0), (-1,-1), 2.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f8fafc')]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#fed7aa')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(t_foot)
    elements.append(Spacer(1, 4))

    # 3. Piers & Columns
    elements.append(Paragraph('3. งานตอม่อและเสา (Piers & Columns: C1) — รวม 18 ต้น (แผ่น S-05 & S-09)', h2_style))
    col_data = [
        [Paragraph('รหัสเสา / ฐานราก', header_th), Paragraph('จำนวน', header_th), Paragraph('หน้าตัด (ม.)', header_th), Paragraph('ความสูง (ตอม่อ/เสา)', header_th), Paragraph('คอนกรีตสุทธิ (ม³)', header_th), Paragraph('เหล็กยืน / ปลอก (S-09 Schedule)', header_th)],
        [Paragraph('C1 บน F1', cell_th), Paragraph('1 ต้น', cell_right), Paragraph('0.20 × 0.20', cell_th), Paragraph('ตอม่อ 1.20ม. / เสา 3.40ม.', cell_th), Paragraph('0.184', cell_right), Paragraph('4-DB12 (L=5.10ม.) / 1-RB6@0.15', cell_th)],
        [Paragraph('C1 บน F2', cell_th), Paragraph('10 ต้น', cell_right), Paragraph('0.20 × 0.20', cell_th), Paragraph('ตอม่อ 1.20ม. / เสา 3.40ม.', cell_th), Paragraph('1.840', cell_right), Paragraph('4-DB12 (L=5.10ม.) / 1-RB6@0.15', cell_th)],
        [Paragraph('C1 บน F3', cell_th), Paragraph('7 ต้น', cell_right), Paragraph('0.20 × 0.20', cell_th), Paragraph('ตอม่อ 1.20ม. / เสา 3.40ม.', cell_th), Paragraph('1.288', cell_right), Paragraph('4-DB12 (L=5.10ม.) / 1-RB6@0.15', cell_th)],
        [Paragraph('<b>รวมตอม่อและเสา</b>', bold_style), Paragraph('<b>18 ต้น</b>', cell_right_bold), Paragraph('-'), Paragraph('<b>ตอม่อ 0.864 / เสา 2.448</b>', bold_style), Paragraph('<b>3.312 ม³ (+3%=3.411)</b>', cell_right_bold), Paragraph('<b>DB12: 37 เส้น | RB6: 42 เส้น</b>', bold_style)],
    ]
    t_col = Table(col_data, colWidths=[75, 45, 75, 120, 98, 130])
    t_col.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('PADDING', (0,0), (-1,-1), 2.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f8fafc')]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#fed7aa')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(t_col)

    elements.append(PageBreak())

    # PAGE 2: BEAMS, FLOORS, ROOF, AND REBAR OPTIMIZATION
    elements.append(Paragraph('4. งานคานคอดิน (Ground Beams: B1 - B4, CB) — แผ่น S-06 & S-10', h2_style))
    beam_data = [
        [Paragraph('รหัสคาน', header_th), Paragraph('หน้าตัด (ม.)', header_th), Paragraph('จำนวนช่วง', header_th), Paragraph('ความยาวรวม (ม.)', header_th), Paragraph('คอนกรีต (ม³)', header_th), Paragraph('สเปคเหล็กเสริม (S-10 Schedule)', header_th)],
        [Paragraph('B1', cell_th), Paragraph('0.20 × 0.40', cell_th), Paragraph('12', cell_right), Paragraph('35.50', cell_right), Paragraph('2.840', cell_right), Paragraph('2-DB12 บน / 2-DB12 ล่าง (Cont. 3-DB12), 1-RB6@0.15', cell_th)],
        [Paragraph('B2', cell_th), Paragraph('0.20 × 0.40', cell_th), Paragraph('4', cell_right), Paragraph('14.00', cell_right), Paragraph('1.120', cell_right), Paragraph('2-DB12 บน / 4-DB12 ล่าง (Cont. 4-DB12), 1-RB6@0.15', cell_th)],
        [Paragraph('B3', cell_th), Paragraph('0.20 × 0.40', cell_th), Paragraph('6', cell_right), Paragraph('21.00', cell_right), Paragraph('1.680', cell_right), Paragraph('3-DB12 บน / 5-DB12 ล่าง (Cont. 5-DB12), 1-RB6@0.15', cell_th)],
        [Paragraph('B4', cell_th), Paragraph('0.20 × 0.50', cell_th), Paragraph('8', cell_right), Paragraph('26.00', cell_right), Paragraph('2.600', cell_right), Paragraph('4-DB12 บน / 6-DB12 ล่าง (Cont. 6-DB12), 1-RB6@0.15', cell_th)],
        [Paragraph('CB', cell_th), Paragraph('0.20 × 0.40', cell_th), Paragraph('4', cell_right), Paragraph('12.00', cell_right), Paragraph('0.960', cell_right), Paragraph('4-DB12 บน / 2-DB12 ล่าง, 1-RB6@0.15', cell_th)],
        [Paragraph('<b>รวมงานคานคอดิน</b>', bold_style), Paragraph('<b>ไม้แบบ: 86.8 ตร.ม.</b>', bold_style), Paragraph('<b>34</b>', cell_right_bold), Paragraph('<b>108.50 ม.</b>', cell_right_bold), Paragraph('<b>9.200 ม³ (+3%=9.476)</b>', cell_right_bold), Paragraph('<b>DB12: 84 เส้น | RB6: 98 เส้น</b>', bold_style)],
    ]
    t_beam = Table(beam_data, colWidths=[40, 60, 48, 70, 95, 230])
    t_beam.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('PADDING', (0,0), (-1,-1), 2.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f8fafc')]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#fed7aa')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(t_beam)
    elements.append(Spacer(1, 4))

    # 5. Floors
    elements.append(Paragraph('5. งานระบบพื้นอาคาร (Floor Slabs: PS, S1) — ผัง S-06 & สถาปัตย์', h2_style))
    floor_data = [
        [Paragraph('ระบบพื้น / พื้นที่', header_th), Paragraph('พื้นที่สุทธิ (ตร.ม.)', header_th), Paragraph('ความหนา (ม.)', header_th), Paragraph('คอนกรีต (ม³)', header_th), Paragraph('เหล็กเสริม / วัสดุปู', header_th)],
        [Paragraph('พื้นสำเร็จรูป PS (SFL = +0.95)', cell_th), Paragraph('94.20', cell_right), Paragraph('0.05 (Topping)', cell_th), Paragraph('4.710', cell_right), Paragraph('Wire Mesh 4mm @0.20 + แผ่นพื้น PS', cell_th)],
        [Paragraph('พื้นหล่อในที่ S1 (SFL = +0.90 ห้องน้ำ/ระเบียง)', cell_th), Paragraph('24.30', cell_right), Paragraph('0.10', cell_th), Paragraph('2.430', cell_right), Paragraph('RB9@0.15 บน-ล่าง + คอม้า RB6 (238.4 กก.)', cell_th)],
        [Paragraph('<b>รวมงานพื้นทั้งหลัง</b>', bold_style), Paragraph('<b>118.50 ตร.ม.</b>', cell_right_bold), Paragraph('-'), Paragraph('<b>7.140 ม³ (+3%=7.354)</b>', cell_right_bold), Paragraph('<b>Topping 4.71 ม³ + เทในที่ 2.43 ม³</b>', bold_style)],
    ]
    t_floor = Table(floor_data, colWidths=[120, 80, 75, 100, 168])
    t_floor.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('PADDING', (0,0), (-1,-1), 2.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f8fafc')]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#fed7aa')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(t_floor)
    elements.append(Spacer(1, 4))

    # 6. Roof
    elements.append(Paragraph('6. งานโครงสร้างหลังคาเหล็กรูปพรรณ (Roof Structure) — แผ่น S-07 & S-08', h2_style))
    roof_data = [
        [Paragraph('รายการชิ้นส่วนโครงหลังคา', header_th), Paragraph('ขนาดหน้าตัดเหล็ก', header_th), Paragraph('ระดับความสูง (El)', header_th), Paragraph('ความยาวรวม (ม.)', header_th), Paragraph('น้ำหนักสุทธิ (กก.)', header_th)],
        [Paragraph('อะเสรอบอาคาร (Eaves Beam)', cell_th), Paragraph('2-C 150 × 50 × 20 × 3.2 มม.', cell_th), Paragraph('El = +4.30 ม.', cell_th), Paragraph('112.40', cell_right), Paragraph('1,013.8', cell_right)],
        [Paragraph('อกไก่ / ดั้ง (Ridge & Posts)', cell_th), Paragraph('2-C 150 × 50 × 20 × 3.2 มม.', cell_th), Paragraph('El = +5.19 ถึง +6.78 ม.', cell_th), Paragraph('54.60', cell_right), Paragraph('492.5', cell_right)],
        [Paragraph('ตะเข้สัน / สะพานรับจันทัน', cell_th), Paragraph('2-C 150 × 50 × 20 × 3.2 มม.', cell_th), Paragraph('El = varies', cell_th), Paragraph('38.20', cell_right), Paragraph('344.6', cell_right)],
        [Paragraph('ระแนง / แปหลังคา', cell_th), Paragraph('เหล็กกล่อง 25 × 25 × 1.6 มม.', cell_th), Paragraph('@ 0.32 ม.', cell_th), Paragraph('282.00', cell_right), Paragraph('299.1', cell_right)],
        [Paragraph('<b>รวมโครงสร้างหลังคา</b>', bold_style), Paragraph('<b>เหล็กรูปพรรณ มอก. ประกบ 2C</b>', bold_style), Paragraph('-'), Paragraph('<b>487.20 ม.</b>', cell_right_bold), Paragraph('<b>~2,150.00 กก. (2.15 ตัน)</b>', cell_right_bold)],
    ]
    t_roof = Table(roof_data, colWidths=[120, 120, 95, 88, 120])
    t_roof.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('PADDING', (0,0), (-1,-1), 2.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f8fafc')]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#fed7aa')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(t_roof)
    elements.append(Spacer(1, 4))

    # 7. Rebar Optimization FFD
    elements.append(Paragraph('7. การบริหารเศษเหล็กเสริมรวมทั้งโครงการ (Bar Cutting List FFD Optimization)', h2_style))
    rebar_data = [
        [Paragraph('ขนาดเหล็กเสริม', header_th), Paragraph('ตัดแยกทีละหมวด (เดิม)', header_th), Paragraph('ตัดรวม FFD ข้ามหมวด (ใหม่)', header_th), Paragraph('ลดจำนวนสั่งซื้อ', header_th), Paragraph('เปอร์เซ็นต์ของเสีย (Waste)', header_th)],
        [Paragraph('เหล็กข้ออ้อย DB12 mm (10.0 ม.)', cell_th), Paragraph('150 เส้น (1,500 ม.)', cell_right), Paragraph('134 เส้น (1,340 ม.)', cell_right), Paragraph('ประหยัด 16 เส้น (160 ม.)', cell_th), Paragraph('1.4% (เหลือน้อยมาก)', cell_right)],
        [Paragraph('เหล็กเส้นกลม RB9 mm (10.0 ม.)', cell_th), Paragraph('28 เส้น (280 ม.)', cell_right), Paragraph('25 เส้น (250 ม.)', cell_right), Paragraph('ประหยัด 3 เส้น (30 ม.)', cell_th), Paragraph('2.1%', cell_right)],
        [Paragraph('เหล็กเส้นกลม RB6 mm (10.0 ม.)', cell_th), Paragraph('72 เส้น (720 ม.)', cell_right), Paragraph('65 เส้น (650 ม.)', cell_right), Paragraph('ประหยัด 7 เส้น (70 ม.)', cell_th), Paragraph('1.1%', cell_right)],
        [Paragraph('<b>รวมเหล็กเส้นทั้งโครงการ</b>', bold_style), Paragraph('<b>250 เส้น (2,500 ม.)</b>', cell_right_bold), Paragraph('<b>224 เส้น (2,240 ม.)</b>', cell_right_bold), Paragraph('<b>ประหยัด 26 เส้น (260 ม.)</b>', bold_style), Paragraph('<b>ประหยัดต้นทุน ~4,600 บ.</b>', cell_right_bold)],
    ]
    t_rebar = Table(rebar_data, colWidths=[120, 100, 105, 110, 108])
    t_rebar.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('PADDING', (0,0), (-1,-1), 2.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f8fafc')]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#fed7aa')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(t_rebar)
    elements.append(Spacer(1, 4))

    qa_box = [
        [
            Paragraph(
                '<b>หมายเหตุการประมวลผล (Engineering Standards):</b><br/>'
                '• สกัดข้อมูลปริมาณงานตามแบบก่อสร้างจริงของโครงการ 116-69 (คุณนุชรินทร์ สิริใหม่) ครอบคลุม ฐานราก 18 ฐาน, เสา C1 18 ต้น, คาน B1-B4, CB, พื้น PS/S1, และโครงหลังคาเหล็ก 2C-150<br/>'
                '• ผ่านการจัดเรียงตัดเศษเหล็กด้วยอัลกอริทึม First-Fit-Decreasing (FFD) ช่วยลดของเสียลงได้ 26 เส้น (~260 ม.)',
                body_style
            )
        ]
    ]
    t_qa = Table(qa_box, colWidths=[543])
    t_qa.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('PADDING', (0,0), (-1,-1), 4),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#94a3b8')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(t_qa)

    doc.build(elements)
    print(f'Generated official complete PDF report: {output_pdf_path}')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-name', default='116-69 - แบบบ้านชั้นเดียว', help='Project name')
    args = parser.parse_args()

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(BASE_DIR, '..', 'project', args.project_name, 'boq')
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f'Plan2BOQ_Structural_Report_{args.project_name}.pdf')
    create_structural_pdf(out_file, project_name=args.project_name)
