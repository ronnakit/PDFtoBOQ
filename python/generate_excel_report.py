# -*- coding: utf-8 -*-
import os
import sys
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import re
import openpyxl
import argparse
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

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

def generate_excel_boq(project_name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.join(base_dir, '..', 'project', project_name)
    md_path = os.path.join(project_dir, 'markdown', 'confirm_boq.md')
    out_dir = os.path.join(project_dir, 'boq')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f'Plan2BOQ_Complete_Structural_BOQ_{project_name}.xlsx')

    sections = parse_markdown_sections(md_path)

    wb = openpyxl.Workbook()
    wb.remove(wb.active) # Remove default sheet

    font_title = Font(name='Tahoma', size=13, bold=True, color='0F172A')
    font_header = Font(name='Tahoma', size=9, bold=True, color='FFFFFF')
    font_sub = Font(name='Tahoma', size=8.5, bold=True, color='475569')
    font_body = Font(name='Tahoma', size=8.5, color='1E293B')
    font_bold = Font(name='Tahoma', size=8.5, bold=True, color='0F172A')

    fill_header_orange = PatternFill(start_color='EA580C', end_color='EA580C', fill_type='solid')
    fill_header_dark = PatternFill(start_color='0F172A', end_color='0F172A', fill_type='solid')
    fill_total = PatternFill(start_color='FED7AA', end_color='FED7AA', fill_type='solid')
    fill_alt = PatternFill(start_color='F8FAFC', end_color='F8FAFC', fill_type='solid')

    thin = Side(border_style='thin', color='CBD5E1')
    border_cell = Border(left=thin, right=thin, top=thin, bottom=thin)

    align_center = Alignment(horizontal='center', vertical='center')
    align_left = Alignment(horizontal='left', vertical='center')
    align_right = Alignment(horizontal='right', vertical='center')

    for sec_name, lines in sections.items():
        if sec_name == 'header':
            continue
        rows = parse_table_from_lines(lines)
        if not rows:
            continue

        clean_title = re.sub(r'[:\?\*\[\]/\\\\]', ' ', sec_name).strip()
        sheet_title = clean_title[:31] if clean_title else f'Sheet{len(wb.worksheets)+1}'
        ws = wb.create_sheet(sheet_title)
        
        ws.append([f'Plan2BOQ Report: {sec_name}'])
        ws.append([f'โครงการ: {project_name} | แหล่งข้อมูล: confirm_boq.md (Dynamic Engine)'])
        ws.append([])

        for r_idx, row in enumerate(rows):
            # Try converting numeric strings to float/int
            converted_row = []
            for cell in row:
                cleaned = cell.replace(',', '').replace('%', '').replace('ม.', '').replace('กก.', '').replace('ตร.ม.', '').replace('ลบ.ม.', '').replace('ม³', '').replace('ตัน', '').strip()
                try:
                    val = float(cleaned)
                    converted_row.append(val)
                except ValueError:
                    converted_row.append(cell)
            ws.append(converted_row)

        ws.views.sheetView[0].showGridLines = True
        ws.row_dimensions[1].height = 24
        ws.cell(row=1, column=1).font = font_title
        ws.cell(row=2, column=1).font = font_sub

        header_fill = fill_header_orange if '1.' in sec_name else fill_header_dark
        for row in ws.iter_rows(min_row=4, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
            for cell in row:
                if cell.row == 4:
                    cell.font = font_header
                    cell.fill = header_fill
                    cell.alignment = align_center
                elif cell.row == ws.max_row and ('รวม' in str(ws.cell(row=ws.max_row, column=1).value or '') or 'Grand' in str(ws.cell(row=ws.max_row, column=1).value or '')):
                    cell.font = font_bold
                    cell.fill = fill_total
                    cell.alignment = align_right if isinstance(cell.value, (int, float)) else align_left
                else:
                    cell.font = font_body
                    cell.alignment = align_right if isinstance(cell.value, (int, float)) else align_left
                    if cell.row % 2 == 0:
                        cell.fill = fill_alt
                cell.border = border_cell

        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = str(cell.value or '')
                if len(val) > max_len:
                    max_len = len(val)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    wb.save(out_path)
    print(f'Successfully generated Dynamic Excel BOQ: {out_path}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-name', required=True, help='Project folder name under project/')
    args = parser.parse_args()
    generate_excel_boq(args.project_name)
