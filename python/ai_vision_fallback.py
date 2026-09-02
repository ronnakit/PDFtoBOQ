"""PDFtoBOQ -- AI vision fallback: อ่านตาราง/ข้อมูลที่ถูก flatten เป็น vector ด้วย AI vision

ใช้เฉพาะจุดที่โค้ดล้วนอ่านไม่ได้จริงๆ (page.get_text() ว่างเปล่าในโซนที่ควรมีตาราง) -- ไม่ใช่ทางเลือก
แรกเสมอ เพราะมีต้นทุน/rate limit ต่อการเรียก

**สถานะ (2569-09-02):** ใช้ Anthropic API key ที่เจ้าของโปรเจกต์ให้มาชั่วคราว (paid, จนกว่าเครดิตจะหมด
แล้วจะเปลี่ยน provider) -- เป้าหมายผลิตภัณฑ์จริงยังคือ free-tier only (ดู BACKLOG.md ของเอกสารพิมพ์
เขียว) ดังนั้นจุดที่ผูกกับ Anthropic SDK อยู่เฉพาะใน call_vision_json()/_get_client() เท่านั้น --
เปลี่ยนไป provider อื่น (เช่น Gemini free tier) แก้แค่สองฟังก์ชันนี้ ที่เหลือ (prompt, การ render หน้า,
การ parse ผล) ใช้ร่วมได้ไม่ต้องแก้

API key ต้องอยู่ใน .env (ANTHROPIC_API_KEY=...) เท่านั้น -- ห้าม hardcode ในโค้ด ห้าม commit .env
(อยู่ใน .gitignore แล้ว)
"""
import base64
import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = os.environ.get("PDFTOBOQ_VISION_MODEL", "claude-haiku-4-5-20251001")

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY ไม่ถูกตั้งค่า -- ใส่ไว้ใน .env (ห้าม commit ไฟล์นี้)")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def render_page_png(page, dpi=150):
    """แปลงหน้า PDF (fitz page) เป็นภาพ PNG bytes -- dpi=150 พอสำหรับตารางตัวเลข/ข้อความบนกระดาษ A3"""
    return page.get_pixmap(dpi=dpi).tobytes("png")


def call_vision_json(image_png_bytes, prompt, model=None):
    """ส่งภาพ + prompt ไปให้ AI vision อ่าน คืน dict ที่ parse จาก JSON ในคำตอบ -- prompt ต้องสั่งให้ตอบ
    เป็น JSON ล้วนๆ เท่านั้น ไม่มีข้อความอื่นแทรก คืน {"_parse_error": True, "_raw": text} ถ้า parse
    ไม่ได้ (ให้ผู้เรียกจัดการ fallback เอง แทนที่จะโยน exception ทำให้ pipeline ทั้งหมดล้ม)."""
    client = _get_client()
    b64 = base64.b64encode(image_png_bytes).decode("ascii")
    resp = client.messages.create(
        model=model or DEFAULT_MODEL,
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    text = "".join(block.text for block in resp.content if block.type == "text").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_parse_error": True, "_raw": text}
