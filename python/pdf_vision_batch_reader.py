"""Read door labels off pre-cropped floor-plan tiles using the Claude API Batches
endpoint (50% cheaper than live calls) with Claude Haiku 4.5 — the production
version of the procedure documented in 03-ai-boq-procedure.md.

Requires ANTHROPIC_API_KEY in the environment and the `anthropic` package.

Usage:
    python pdf_vision_batch_reader.py <tile1.png> <tile2.png> ...
"""
import argparse
import base64
import json
import sys
import time

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

MODEL = "claude-haiku-4-5"

PROMPT = """You are an expert Architectural Blueprint Analyzer.
This is ONE TILE cropped from a larger Thai residential floor plan (scanned, ~300dpi).
Expected door codes on this drawing (from the door schedule page): D1, D2, D3, D4, D5.
Some labels may be cut off at tile edges - only count a label you can read clearly, not a fragment.
Count each occurrence of each code separately in THIS TILE ONLY.
If a label is illegible, note it instead of guessing.
Respond with ONLY a JSON object: {"D1": 2, "D4": 1, "notes": "..."}"""

PRICE_PER_MTOK = {"input": 1.00, "output": 5.00}  # claude-haiku-4-5, batch = 50% of this


def build_request(tile_path, custom_id):
    with open(tile_path, "rb") as f:
        b64 = base64.standard_b64encode(f.read()).decode("ascii")
    return Request(
        custom_id=custom_id,
        params=MessageCreateParamsNonStreaming(
            model=MODEL,
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                    {"type": "text", "text": PROMPT},
                ],
            }],
        ),
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tiles", nargs="+", help="tile image paths")
    args = ap.parse_args()

    client = anthropic.Anthropic()
    requests = [build_request(p, f"tile-{i}") for i, p in enumerate(args.tiles)]

    batch = client.messages.batches.create(requests=requests)
    print(f"batch id: {batch.id}  status: {batch.processing_status}")

    while True:
        batch = client.messages.batches.retrieve(batch.id)
        if batch.processing_status == "ended":
            break
        print(f"  ...{batch.processing_status} "
              f"(succeeded={batch.request_counts.succeeded}, processing={batch.request_counts.processing})")
        time.sleep(15)

    totals = {}
    total_input_tok = 0
    total_output_tok = 0
    per_tile = {}

    for result in client.messages.batches.results(batch.id):
        idx = int(result.custom_id.split("-")[1])
        tile_name = args.tiles[idx]
        if result.result.type != "succeeded":
            print(f"[{tile_name}] FAILED: {result.result.type}")
            continue
        msg = result.result.message
        text = next((b.text for b in msg.content if b.type == "text"), "{}")
        total_input_tok += msg.usage.input_tokens
        total_output_tok += msg.usage.output_tokens
        try:
            data = json.loads(text.strip().removeprefix("```json").removesuffix("```").strip())
        except json.JSONDecodeError:
            print(f"[{tile_name}] could not parse: {text!r}")
            continue
        per_tile[tile_name] = data
        for code, count in data.items():
            if code == "notes" or not isinstance(count, int):
                continue
            totals[code] = totals.get(code, 0) + count

    print("\n=== per-tile results ===")
    for tile, data in per_tile.items():
        print(f"{tile}: {data}")

    print("\n=== totals (raw sum, no dedup across tile overlaps yet) ===")
    for code in sorted(totals):
        print(f"  {code}: {totals[code]}")

    cost_usd = (total_input_tok * PRICE_PER_MTOK["input"] + total_output_tok * PRICE_PER_MTOK["output"]) / 1_000_000
    cost_usd_batch = cost_usd * 0.5
    print(f"\ninput_tokens={total_input_tok} output_tokens={total_output_tok}")
    print(f"cost (live pricing): ${cost_usd:.5f}")
    print(f"cost (batch, -50%):  ${cost_usd_batch:.5f}  (~{cost_usd_batch*36.5:.2f} THB)")


if __name__ == "__main__":
    main()
