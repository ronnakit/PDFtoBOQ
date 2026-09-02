import ezdxf
import os
import re

BASE_CAD_DIR = r"G:\My Drive\project\welcome maerem\cad"
TARGET_FILE = "Kadfarang Drawing.dxf"

def train_py_noi_floor_parser():
    file_path = os.path.join(BASE_CAD_DIR, TARGET_FILE)
    if not os.path.exists(file_path):
        print(f"[Error] ไม่พบไฟล์ที่: {file_path}")
        return

    doc = ezdxf.readfile(file_path)
    block_name = 'X ref Kad Plan 1st'
    
    if block_name not in doc.blocks:
        print(f"[Error] ไม่พบ Block เป้าหมาย: {block_name}")
        return

    target_block = doc.blocks[block_name]
    print(f"\n--- 🤖 'ไพน้อย' เริ่มปฏิบัติการสแกนหาตารางและสัญลักษณ์พื้น (FL Codes) ---")

    floor_counts = {}
    # ใช้ RegEx ค้นหารูปแบบคำว่า FL ตามด้วยตัวเลข (เช่น FL1, FL2, FL3 ...) ไม่ว่าจะพิมพ์ติดกันหรือมีเว้นวรรค
    pattern = re.compile(r'FL\s*([0-9]+)', re.IGNORECASE)

    text_scanned = 0
    for entity in target_block:
        if entity.dxftype() in ['TEXT', 'MTEXT']:
            text_val = entity.text if hasattr(entity, 'text') else ""
            text_scanned += 1
            
            match = pattern.search(text_val)
            if match:
                fl_code = f"FL{match.group(1)}"
                floor_counts[fl_code] = floor_counts.get(fl_code, 0) + 1

    print(f" - สแกนข้อความในแปลนชั้น 1 ทั้งหมด: {text_scanned} จุด")
    print("\n" + "="*40)
    print(" 🏷 ผลการตรวจจับสัญลักษณ์พื้น (FL Schedule Matching)")
    print("="*40)
    
    if floor_counts:
        for code, count in sorted(floor_counts.items()):
            print(f" ✨ พบป้ายสัญลักษณ์ '{code}' : ปรากฏในแบบจำนวน {count} จุด")
    else:
        print(" ⚠️ ยังไม่พบป้าย FL แบบข้อความตรงๆ (อาจถูกห่อหุ้มไว้ใน Block ย่อย หรือ Attribute ของสัญลักษณ์)")
    print("="*40)

if __name__ == "__main__":
    train_py_noi_floor_parser()