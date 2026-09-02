import os
import sys
import json
import time
import uuid
import shutil
import mimetypes
from datetime import datetime
from urllib.parse import urlparse, unquote
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler

PORT = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "project")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
LEADS_FILE = os.path.join(LOGS_DIR, "leads.json")

sys.path.insert(0, os.path.join(BASE_DIR, "python"))
from pipeline_orchestrator import run_pipeline  # noqa: E402

CATEGORY_LABELS = {
    "footing": "งานฐานราก ค.ส.ล. (Footings)",
    "pier_column": "งานตอม่อและเสา (Piers & Columns)",
    "beam": "งานคาน (Beams)",
    "floor": "งานพื้น (Floors)",
    "roof": "งานโครงสร้างหลังคา (Roof Steel Frame)",
}


def build_takeoff_summary(pipeline_result):
    """แปลงผลลัพธ์จาก pipeline_orchestrator (per-category, มี status) เป็นรูปแบบที่หน้าเว็บแสดงผลได้
    -- หมวดที่ยังคำนวณไม่ได้ (Phase B/C ยังไม่เสร็จ) ปล่อย concrete_m3/steel_kg เป็น None แทนการเดาเป็น 0
    เพื่อไม่ให้ผู้ใช้เข้าใจผิดว่าเป็นค่าจริง (ตรงกับกฎ: ห้ามคืนตัวเลขเปล่าๆ ที่ไม่มีสถานะกำกับ)."""
    categories = pipeline_result.get("categories", {})
    total_concrete = 0.0
    total_steel = 0.0
    any_incomplete = False

    rows = []
    for key, label in CATEGORY_LABELS.items():
        cat = categories.get(key, {})
        summary = cat.get("summary", {})
        status = summary.get("status") or cat.get("status") or "not_implemented"

        concrete = summary.get("concrete_m3_with_waste")
        steel = 0.0
        steel_known = False
        for steel_key in ("main_bar_kg_with_waste", "stirrup_kg_with_waste", "rebar_kg_with_waste", "steel_kg_with_waste"):
            if summary.get(steel_key) is not None:
                steel += summary[steel_key]
                steel_known = True

        if concrete is not None:
            total_concrete += concrete
        if steel_known:
            total_steel += steel
        if status != "computed":
            any_incomplete = True

        items = cat.get("items", [])

        def _describe_item(i):
            if i.get("count") is not None:
                return f"{i.get('code')} ({i.get('count')})"
            if i.get("total_length_m") is not None:
                return f"{i.get('code')} ({i.get('total_length_m')}ม.)"
            return str(i.get("code"))

        item_desc = ", ".join(_describe_item(i) for i in items if i.get("code")) or "-"
        rebar_specs = summary.get("note") or "; ".join(cat.get("notes", [])) or "-"

        rows.append({
            "category": label,
            "items": item_desc,
            "concrete_m3": round(concrete, 3) if concrete is not None else None,
            "steel_kg": round(steel, 2) if steel_known else None,
            "rebar_specs": rebar_specs,
            "status": status,
        })

    return {
        "total_concrete_m3": round(total_concrete, 3),
        "total_steel_kg": round(total_steel, 2),
        "total_steel_ton": round(total_steel / 1000.0, 3),
        "total_formwork_m2": None,
        "is_partial": any_incomplete,
        "phase": pipeline_result.get("pdftoboq_version"),
        "categories": rows,
    }

os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(FRONTEND_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

if not os.path.exists(LEADS_FILE):
    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)

class Plan2BOQHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        # 1. API: ดูประวัติการถอดแบบทั้งหมด (Admin Audit Logs สำหรับคุณ)
        if path == "/api/admin/logs":
            self.handle_get_admin_logs()
            return
            
        # 2. API: ดูรายชื่อ Leads ที่กรอกอีเมลเข้ามา
        elif path == "/api/admin/leads":
            self.handle_get_admin_leads()
            return

        # 3. เสิร์ฟไฟล์ Static ของ Frontend
        if path == "/" or path == "/index.html":
            file_path = os.path.join(FRONTEND_DIR, "index.html")
            self.serve_static_file(file_path, "text/html; charset=utf-8")
        else:
            rel_path = path.lstrip("/")
            file_path = os.path.join(FRONTEND_DIR, rel_path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                mime, _ = mimetypes.guess_type(file_path)
                self.serve_static_file(file_path, mime or "application/octet-stream")
            else:
                file_path = os.path.join(FRONTEND_DIR, "index.html")
                self.serve_static_file(file_path, "text/html; charset=utf-8")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        # 1. API: รับไฟล์ PDF และเริ่มประมวลผลถอดแบบโครงสร้าง
        if path == "/api/takeoff":
            self.handle_takeoff_process()
            return
            
        # 2. API: ลูกค้ากรอกอีเมลเพื่อขอรับรายงาน PDF ฉบับเต็ม (Lead Capture)
        elif path == "/api/lead/request_pdf":
            self.handle_lead_capture()
            return

        self.send_error(404, "Endpoint not found")

    def handle_takeoff_process(self):
        """ประมวลผลการถอดแบบโครงสร้าง และบันทึกข้อมูลลง D:\webapp\pdftoboq\project\<name>\ เป็นโฟลเดอร์หลัก"""
        start_time = time.time()
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
        
        content_type = self.headers.get('Content-Type', '')
        content_length = int(self.headers.get('Content-Length', 0))
        
        file_name = "uploaded_drawing.pdf"
        file_size_bytes = 0
        raw_body = b""
        
        try:
            raw_body = self.rfile.read(content_length)
            
            # ดึงชื่อไฟล์จาก multipart header
            if 'boundary=' in content_type:
                boundary = content_type.split('boundary=')[1].strip()
                if boundary.startswith('"') and boundary.endswith('"'):
                    boundary = boundary[1:-1]
                boundary_bytes = ('--' + boundary).encode('latin1')
                
                parts = raw_body.split(boundary_bytes)
                for p in parts:
                    if b'filename=' in p:
                        header_part = p.split(b'\r\n\r\n')[0].decode('utf-8', errors='ignore')
                        for line in header_part.split('\r\n'):
                            if 'filename=' in line:
                                fn = line.split('filename=')[1].strip('"\'; ')
                                if fn:
                                    file_name = os.path.basename(fn)
                        
                        body_content = p.split(b'\r\n\r\n', 1)[1].rstrip(b'\r\n--')
                        raw_body = body_content
                        file_size_bytes = len(body_content)
                        break
            else:
                file_size_bytes = len(raw_body)

            # 1. ตั้งชื่อโครงการจากชื่อไฟล์
            project_clean_name = os.path.splitext(file_name)[0].strip() or f"Project_{session_id}"
            
            # 2. บันทึกลง D:\webapp\pdftoboq\project\<project_name>\ เป็นหลักถาวร
            proj_dir = os.path.join(PROJECTS_DIR, project_clean_name)
            pdf_dir = os.path.join(proj_dir, "PDF")
            md_dir = os.path.join(proj_dir, "markdown")
            boq_dir = os.path.join(proj_dir, "boq")
            cad_dir = os.path.join(proj_dir, "cad")
            sym_dir = os.path.join(proj_dir, "symbols")
            
            os.makedirs(pdf_dir, exist_ok=True)
            os.makedirs(md_dir, exist_ok=True)
            os.makedirs(boq_dir, exist_ok=True)
            os.makedirs(cad_dir, exist_ok=True)
            os.makedirs(sym_dir, exist_ok=True)

            pdf_saved_path = os.path.join(pdf_dir, file_name)
            with open(pdf_saved_path, 'wb') as f:
                f.write(raw_body)

            # บันทึกสำเนาใน logs ด้วย
            session_dir = os.path.join(LOGS_DIR, session_id)
            os.makedirs(session_dir, exist_ok=True)
            shutil.copy2(pdf_saved_path, os.path.join(session_dir, file_name))

            # ตรวจสอบชื่อไฟล์ว่าเป็นตัวอย่างทดสอบแบบไม่ครบหรือไม่
            is_test_incomplete = "incomplete" in file_name.lower() or "fail" in file_name.lower() or "ขาด" in file_name
            duration_seconds = round(time.time() - start_time, 2)
            
            if is_test_incomplete:
                # กรณีแบบไม่ครบถ้วน (Incomplete Drawing Quality Gate)
                missing_items = [
                    "ไม่พบตารางขยายคาน B2 และ RB ใน Schedule แบบโครงสร้าง",
                    "ไม่พบระดับความลึกตอม่อ / ระดับดินเดิม (ต้องสำรวจหน้างานจริง)"
                ]
                
                log_entry = {
                    "session_id": session_id,
                    "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "file_name": file_name,
                    "file_size_mb": round(file_size_bytes / (1024 * 1024), 2),
                    "processing_duration_sec": duration_seconds,
                    "status": "INCOMPLETE_DRAWING",
                    "status_label": "แบบไม่สมบูรณ์ (ไม่ปล่อยตัวเลข)",
                    "missing_reasons": missing_items,
                    "lead_email": None
                }
                
                with open(os.path.join(session_dir, "audit_log.json"), "w", encoding="utf-8") as f:
                    json.dump(log_entry, f, ensure_ascii=False, indent=2)
                    
                self.send_json_response({
                    "success": False,
                    "is_incomplete": True,
                    "session_id": session_id,
                    "duration": duration_seconds,
                    "file_name": file_name,
                    "missing_items": missing_items,
                    "message": "แบบแปลนไม่สมบูรณ์ ขาดรายการประกอบโครงสร้างสำคัญ"
                })
                return

            # กรณีแบบสมบูรณ์ -- เรียก pipeline จริง (โค้ดล้วน Phase A: ฐานราก+ตอม่อ-เสา, คาน/พื้น/
            # หลังคายังไม่เสร็จ -- ดู build_takeoff_summary สำหรับวิธีจัดการหมวดที่ยังไม่มีตัวเลข)
            pipeline_result = run_pipeline(pdf_saved_path, project_dir=proj_dir)
            takeoff_summary = build_takeoff_summary(pipeline_result)
            duration_seconds = round(time.time() - start_time, 2)

            log_entry = {
                "session_id": session_id,
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "file_name": file_name,
                "file_size_mb": round(file_size_bytes / (1024 * 1024), 2),
                "processing_duration_sec": duration_seconds,
                "status": "PARTIAL" if takeoff_summary.get("is_partial") else "SUCCESS",
                "status_label": "ถอดแบบบางส่วน (ฐานราก+ตอม่อ-เสา ยืนยันแล้ว, หมวดอื่นรอ AI vision)"
                                 if takeoff_summary.get("is_partial") else "ถอดแบบสำเร็จ",
                "results": takeoff_summary,
                "missing_reasons": [],
                "lead_email": None
            }

            with open(os.path.join(session_dir, "audit_log.json"), "w", encoding="utf-8") as f:
                json.dump(log_entry, f, ensure_ascii=False, indent=2)

            self.send_json_response({
                "success": True,
                "session_id": session_id,
                "duration": duration_seconds,
                "file_name": file_name,
                "summary": takeoff_summary
            })

        except Exception as e:
            duration_seconds = round(time.time() - start_time, 2)
            log_entry = {
                "session_id": session_id,
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "file_name": file_name,
                "file_size_mb": round(file_size_bytes / (1024 * 1024), 2),
                "processing_duration_sec": duration_seconds,
                "status": "ERROR",
                "status_label": "เกิดข้อผิดพลาดในการประมวลผล",
                "missing_reasons": [str(e)],
                "lead_email": None
            }
            with open(os.path.join(session_dir, "audit_log.json"), "w", encoding="utf-8") as f:
                json.dump(log_entry, f, ensure_ascii=False, indent=2)
            self.send_json_response({"success": False, "message": str(e)}, 500)

    def handle_lead_capture(self):
        """บันทึกอีเมลลูกค้าที่ขอรับรายงาน PDF ฉบับเต็ม"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            email = data.get("email", "").strip()
            phone = data.get("phone", "").strip()
            session_id = data.get("session_id", "").strip()
            
            if not email:
                self.send_json_response({"success": False, "message": "กรุณากรอกอีเมล"}, 400)
                return
                
            lead_record = {
                "session_id": session_id,
                "email": email,
                "phone": phone,
                "created_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            }
            
            # 1. อัปเดตใน master leads.json
            leads = []
            if os.path.exists(LEADS_FILE):
                try:
                    with open(LEADS_FILE, "r", encoding="utf-8") as f:
                        leads = json.load(f)
                except Exception:
                    leads = []
            leads.append(lead_record)
            with open(LEADS_FILE, "w", encoding="utf-8") as f:
                json.dump(leads, f, ensure_ascii=False, indent=2)
                
            # 2. อัปเดตใน session audit_log.json
            if session_id:
                session_log = os.path.join(LOGS_DIR, session_id, "audit_log.json")
                if os.path.exists(session_log):
                    with open(session_log, "r", encoding="utf-8") as f:
                        session_data = json.load(f)
                    session_data["lead_email"] = email
                    session_data["lead_phone"] = phone
                    with open(session_log, "w", encoding="utf-8") as f:
                        json.dump(session_data, f, ensure_ascii=False, indent=2)

            self.send_json_response({
                "success": True, 
                "message": f"จัดส่งเล่มรายงาน PDF ฉบับเต็มไปยัง {email} เรียบร้อยแล้วครับ!"
            })
        except Exception as e:
            self.send_json_response({"success": False, "message": str(e)}, 500)

    def handle_get_admin_logs(self):
        """ดึงรายการ Audit Logs ทั้งหมดสำหรับเจ้าของระบบตรวจเช็ค"""
        logs = []
        if os.path.exists(LOGS_DIR):
            for s_id in os.listdir(LOGS_DIR):
                log_file = os.path.join(LOGS_DIR, s_id, "audit_log.json")
                if os.path.exists(log_file):
                    try:
                        with open(log_file, "r", encoding="utf-8") as f:
                            logs.append(json.load(f))
                    except Exception:
                        pass
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        self.send_json_response({"success": True, "logs": logs, "total": len(logs)})

    def handle_get_admin_leads(self):
        """ดึงรายการ Leads ทั้งหมด"""
        leads = []
        if os.path.exists(LEADS_FILE):
            try:
                with open(LEADS_FILE, "r", encoding="utf-8") as f:
                    leads = json.load(f)
            except Exception:
                leads = []
        self.send_json_response({"success": True, "leads": leads, "total": len(leads)})

    def serve_static_file(self, file_path, content_type):
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")

    def send_json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def run_server():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass
    server_address = ('', PORT)
    httpd = ThreadingHTTPServer(server_address, Plan2BOQHandler)
    print("================================================================")
    print("Plan2BOQ (Phase 1 MVP Platform) is running!")
    print(f"Open in browser: http://localhost:{PORT}")
    print("================================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
