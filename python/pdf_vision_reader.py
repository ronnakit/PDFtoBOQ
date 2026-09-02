"""Read a construction-drawing PDF page using a vision-language model (Claude API),
instead of OCR/template-matching (both proven unreliable for this content — see
pdf_door_label_matcher.py and 10-pdf-mvp-spec.md §5.4).

This is the "ไพน้อย" version of what Claude did manually in-session: render the page,
look at it, and read the door/window labels off the drawing. Requires an Anthropic
API key (ANTHROPIC_API_KEY env var) and has a real per-call cost — this is the
"variable cost" risk already flagged in 11-founding-member-pricing.md §2, now made
concrete: every page read this way costs money, so pricing must account for it.

Usage:
    python pdf_vision_reader.py <pdf> <page_number_1indexed> [--dpi 300]
"""
import argparse
import base64
import io
import json
import os

import anthropic
import fitz

MODEL = "claude-opus-4-5-20251101"

COUNT_TOOL = {
    "name": "report_door_counts",
    "description": "Report every door/window label found on the drawing tile, grouped by code.",
    "input_schema": {
        "type": "object",
        "properties": {
            "counts": {
                "type": "object",
                "description": "Map of label code (e.g. 'D1', 'D4', 'W3') to the number of times it appears on this image.",
                "additionalProperties": {"type": "integer"},
            },
            "notes": {
                "type": "string",
                "description": "Anything ambiguous, illegible, or worth flagging for human review.",
            },
        },
        "required": ["counts"],
    },
}

PROMPT = """This is a tile cropped from a Thai residential construction floor plan (scanned, ~300dpi).
Find every door label (codes like D1, D2, D3, D4, D5) and window label (W1-W4) printed on this tile.
Count each occurrence of each code — a code repeated at 3 different doors counts as 3, not 1.
Do not guess at labels you cannot actually read; note anything illegible instead of inventing a value.
Call report_door_counts with your findings."""


def render_page(pdf_path, page_index, dpi):
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    pix = page.get_pixmap(dpi=dpi)
    return pix.tobytes("png")


def read_tile(client, image_bytes):
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[COUNT_TOOL],
        tool_choice={"type": "tool", "name": "report_door_counts"},
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                {"type": "text", "text": PROMPT},
            ],
        }],
    )
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError("model did not call the tool")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf")
    ap.add_argument("page", type=int, help="1-indexed page number")
    ap.add_argument("--dpi", type=int, default=300)
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY first (get one at console.anthropic.com)")

    client = anthropic.Anthropic()
    image_bytes = render_page(args.pdf, args.page - 1, args.dpi)
    result = read_tile(client, image_bytes)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
