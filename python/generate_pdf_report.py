# -*- coding: utf-8 -*-
import os
import sys
import re
import argparse

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

def parse_markdown_sections(md_path):
    if not os.path.exists(md_path):
        raise FileNotFoundError(f'ไม่พบไฟล์ {md_path}')
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    sections = {}
    current_sec = 'header'
    lines = content.splitlines()
    sec_lines = []

    for line in lines:
        if line.startswith('## '):
            if sec_lines:
                sections[current_sec] = sec_lines
            current_sec = line.replace('## ', '').strip()
            sec_lines = []
        else:
            sec_lines.append(line)
    if sec_lines:
        sections[current_sec] = sec_lines

    return sections

def parse_table_from_lines(lines):
    table_rows = []
    for line in lines:
        s = line.strip()
        if s.startswith('|') and s.endswith('|'):
            if re.match(r'^[|\s\-:]+$', s):
                continue
            cols = [c.strip() for c in s.split('|')[1:-1]]
            if any(cols):
                table_rows.append(cols)
    return table_rows

def create_structural_pdf(project_name, owner_name=None, site_address=None):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.join(base_dir, '..', 'project', project_name)
    md_path = os.path.join(project_dir, 'markdown', 'confirm_boq.md')
    out_dir = os.path.join(project_dir, 'boq')
    os.makedirs(out_dir, exist_ok=True)
    output_pdf_path = os.path.join(out_dir, f'Plan2BOQ_Structural_Report_{project_name}.pdf')

    sections = parse_markdown_sections(md_path)

    # A4 width = 595.27 pt. Margins 20pt left/right => usable width = 555 pt.
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=A4,
        rightMargin=20,
        leftMargin=20,
        topMargin=16,
        bottomMargin=16
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('ThaiTitle', parent=styles['Heading1'], fontName=font_bold, fontSize=13, leading=15, textColor=colors.HexColor('#0f172a'), alignment=1)
    subtitle_style = ParagraphStyle('ThaiSubtitle', parent=styles['Normal'], fontName=font_main, fontSize=7.5, leading=9.5, textColor=colors.HexColor('#64748b'), alignment=1)
    h2_style = ParagraphStyle('ThaiH2', parent=styles['Heading2'], fontName=font_bold, fontSize=8.5, leading=11, textColor=colors.HexColor('#ea580c'), spaceBefore=3, spaceAfter=2)
    body_style = ParagraphStyle('ThaiBody', parent=styles['Normal'], fontName=font_main, fontSize=6.5, leading=8.5, textColor=colors.HexColor('#1e293b'))
    bold_style = ParagraphStyle('ThaiBold', parent=styles['Normal'], fontName=font_bold, fontSize=6.5, leading=8.5, textColor=colors.HexColor('#0f172a'))
    header_th = ParagraphStyle('ThaiHeaderTH', parent=styles['Normal'], fontName=font_bold, fontSize=6.5, leading=8.5, textColor=colors.white, alignment=1)
    cell_th = ParagraphStyle('ThaiCellTH', parent=styles['Normal'], fontName=font_main, fontSize=6.5, leading=8.5, textColor=colors.HexColor('#1e293b'))
    cell_right = ParagraphStyle('ThaiCellRight', parent=styles['Normal'], fontName=font_main, fontSize=6.5, leading=8.5, textColor=colors.HexColor('#1e293b'), alignment=2)
    cell_right_bold = ParagraphStyle('ThaiCellRightBold', parent=styles['Normal'], fontName=font_bold, fontSize=6.5, leading=8.5, textColor=colors.HexColor('#0f172a'), alignment=2)

    elements = []

    # PAGE 1: HEADER & EXECUTIVE SUMMARY & FOOTINGS & COLUMNS
    elements.append(Paragraph('รายงานผลการถอดแบบและประมาณราคาโครงสร้างฉบับสมบูรณ์', title_style))
    elements.append(Paragraph('PLAN2BOQ STRUCTURAL QUANTITY TAKEOFF COMPLETE REPORT', subtitle_style))
    elements.append(Spacer(1, 2))
    elements.append(HRFlowable(width='100%', thickness=1.0, color=colors.HexColor('#ea580c'), spaceAfter=3))

    meta_data = [
        [
            Paragraph(f'<b>โครงการ:</b> {project_name}' + (f' ({owner_name})' if owner_name else ''), body_style),
            Paragraph(f'<b>สถานที่:</b> {site_address or "(ไม่ระบุ)"}', body_style),
        ],
        [
            Paragraph('<b>เครื่องมือประมวลผล:</b> PDFtoBOQ Dynamic Engine (อ่านจาก confirm_boq.md สด 100%)', body_style),
            Paragraph('<b>สถานะการตรวจสอบ:</b> สกัดตรงจากแบบก่อสร้างของโครงการนี้', body_style)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[277, 278])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('PADDING', (0,0), (-1,-1), 2.5),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 3))

    def build_dynamic_table(title, raw_rows, col_widths, is_summary=False):
        if not raw_rows:
            return
        elements.append(Paragraph(title, h2_style))
        formatted_table = []
        for i, row in enumerate(raw_rows):
            row_cells = []
            for j, cell in enumerate(row):
                if i == 0:
                    row_cells.append(Paragraph(cell, header_th))
                elif i == len(raw_rows) - 1 and ('รวม' in row[0] or 'Grand' in row[0]):
                    row_cells.append(Paragraph(f'<b>{cell}</b>', bold_style if j == 0 or j == len(row)-1 else cell_right_bold))
                else:
                    cleaned = cell.replace(',', '').replace('%', '').replace('ม.', '').replace('กก.', '').replace('ตร.ม.', '').replace('ลบ.ม.', '').replace('ม³', '').replace('ตัน', '').strip()
                    is_num = False
                    try:
                        float(cleaned)
                        is_num = True
                    except ValueError:
                        is_num = False

                    if is_num or j in [1, 2, 3]:
                        row_cells.append(Paragraph(cell, cell_right if not cell.startswith('<b>') else cell_right_bold))
                    else:
                        row_cells.append(Paragraph(cell, cell_th))
            formatted_table.append(row_cells)

        t = Table(formatted_table, colWidths=col_widths)
        bg_header = colors.HexColor('#ea580c') if is_summary else colors.HexColor('#0f172a')
        style = [
            ('BACKGROUND', (0,0), (-1,0), bg_header),
            ('PADDING', (0,0), (-1,-1), 2.0),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1 if not ('รวม' in raw_rows[-1][0]) else -2), [colors.white, colors.HexColor('#f8fafc')]),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]
        if 'รวม' in raw_rows[-1][0] or 'Grand' in raw_rows[-1][0]:
            style.append(('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#fed7aa')))
        t.setStyle(TableStyle(style))
        elements.append(t)
        elements.append(Spacer(1, 3))

    # Total usable width = 555 pt
    # 1. Executive Summary
    for sec_name, lines in sections.items():
        if '1. สรุปภาพรวม' in sec_name:
            rows = parse_table_from_lines(lines)
            build_dynamic_table(f'1. {sec_name}', rows, [195, 80, 80, 120, 80], is_summary=True)

    # 2. Footings
    for sec_name, lines in sections.items():
        if '2. งานฐานราก' in sec_name:
            rows = parse_table_from_lines(lines)
            build_dynamic_table(f'{sec_name}', rows, [45, 45, 115, 115, 145, 90])

    # 3. Columns
    for sec_name, lines in sections.items():
        if '3. งานตอม่อและเสา' in sec_name:
            rows = parse_table_from_lines(lines)
            build_dynamic_table(f'{sec_name}', rows, [75, 45, 75, 125, 105, 130])

    elements.append(PageBreak())

    # PAGE 2: BEAMS, FLOORS, ROOF, AND REBAR OPTIMIZATION
    # 4. Beams
    for sec_name, lines in sections.items():
        if '4. งานคาน' in sec_name or '4. งานคานคอดิน' in sec_name:
            rows = parse_table_from_lines(lines)
            build_dynamic_table(f'{sec_name}', rows, [45, 65, 55, 75, 95, 220])

    # 5. Floors
    for sec_name, lines in sections.items():
        if '5. งานระบบพื้น' in sec_name or '5. งานพื้น' in sec_name:
            rows = parse_table_from_lines(lines)
            build_dynamic_table(f'{sec_name}', rows, [125, 80, 75, 105, 170])

    # 6. Roof
    for sec_name, lines in sections.items():
        if '6. งานโครงสร้างหลังคา' in sec_name or '6. งานโครงหลังคา' in sec_name:
            rows = parse_table_from_lines(lines)
            build_dynamic_table(f'{sec_name}', rows, [125, 125, 95, 90, 120])

    # 7. FFD Rebar
    for sec_name, lines in sections.items():
        if '7. การบริหารเศษเหล็ก' in sec_name or '7. ตัดเศษเหล็ก' in sec_name:
            rows = parse_table_from_lines(lines)
            build_dynamic_table(f'{sec_name}', rows, [125, 105, 105, 110, 110])

    qa_box = [
        [
            Paragraph(
                '<b>หมายเหตุการประมวลผล (PDFtoBOQ Dynamic Engine):</b><br/>'
                '• สกัดข้อมูลปริมาณงานตามแบบก่อสร้างจริงของโครงการนี้ — ตัวเลขทั้งหมดในรายงานนี้มาจาก '
                f'confirm_boq.md ของโครงการ {project_name} เท่านั้น<br/>'
                '• รายการเหล็กเสริม (ถ้ามีการตัดเศษ) ผ่านการจัดเรียงด้วยอัลกอริทึม First-Fit-Decreasing (FFD)',
                body_style
            )
        ]
    ]
    t_qa = Table(qa_box, colWidths=[555])
    t_qa.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('PADDING', (0,0), (-1,-1), 3.0),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#94a3b8')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(t_qa)

    doc.build(elements)
    print(f'Generated Fitted Dynamic PDF report: {output_pdf_path}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-name', required=True, help='Project folder name under project/')
    parser.add_argument('--owner-name', default=None, help='Project owner name (for report header)')
    parser.add_argument('--site-address', default=None, help='Site address (for report header)')
    args = parser.parse_args()
    create_structural_pdf(project_name=args.project_name, owner_name=args.owner_name, site_address=args.site_address)
