"""
schema_loader -- shared helper to read 04-category-schema.md's fenced ```json
block. Both pynoi_parser.py (exclusion_rules) and classify_layers.py
(master_categories) load through here so there is exactly one place that
knows how to parse the schema file -- adding a new noise pattern or category
keyword only ever means editing that one markdown file, never this code.
"""

import json
import re
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / ".." / ".." / ".." / "04-category-schema.md"


def load_schema(path: Path = SCHEMA_PATH) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"```json\n(.*?)\n```", text, re.S)
    if not match:
        raise ValueError(f"no ```json fenced block found in {path}")
    return json.loads(match.group(1))
