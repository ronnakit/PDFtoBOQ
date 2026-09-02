"""Fix a broken /ToUnicode CMap found in some AutoCAD-to-PDF Thai exports.

Confirmed in project/116-69/PDF/116-69 - แบบบ้านชั้นเดียว.pdf (producer
"Microsoft: Print To PDF", vector text via PyMuPDF get_text). Two independent
bugs, found by reverse-engineering against readable context elsewhere in the
same document -- there is no correct ToUnicode CMap to fall back on:

1. One embedded CID font (used for spec/legend paragraphs) has a ToUnicode
   CMap that maps most Thai glyphs straight through as if the intended
   TIS-620/cp874 single byte were itself the Unicode codepoint, landing them
   in the Latin-1 Supplement block (e.g. "ส" comes out as U+00CA "Ê", because
   0xCA is "ส" in TIS-620). A handful of tone-mark glyph variants (used when
   the mark stacks over a tall vowel) go through an *additional* bug: they
   land on ASCII letters m-r that are 123 codes below the byte they should
   have gotten (m=0x6D -> intended 0x6D+123=0xE8 "่").
2. A second, unrelated font family (used for title-block/legend text; several
   embedded subsets of what looks like the same source font, reused
   consistently across those subsets) sends a handful of combining tone
   marks/vowels to the IPA Modifier Letters Unicode block instead of the
   correct Thai combining character.

Both mappings were reconstructed by finding many occurrences of each broken
codepoint in recognizable Thai words (e.g. "เป[U+02DE]น" only ever makes sense
as "เป็น") and are believed stable for this document's fonts, since the
several fonts share consistent behavior across all pages that use them. A
different PDF (different export tool) would need this re-derived.
"""

# IPA Modifier Letters glyphs -> correct Thai combining character.
# Global fix: this Unicode block has no legitimate use in a Thai
# construction drawing, so it is safe to apply regardless of font.
MODIFIER_LETTER_FIX = {
    0x02CF: "ั",  # ั  sara a / mai han-akat
    0x02D1: "่",  # ่  mai ek
    0x02D3: "้",  # ้  mai tho
    0x02D4: "้",  # ้  mai tho (alternate stacking-height glyph)
    0x02D6: "๊",  # ๊  mai tri
    0x02DE: "็",  # ็  mai taikhu
    0x02E1: "ิ",  # ิ  sara i
    0x02E3: "ี",  # ี  sara ii
}

# Note: a few Latin-1 Supplement codepoints (degree sign, plus-minus,
# superscript 2) also occur elsewhere in this document as their literal,
# correct meaning ("30.00°", "0.30±0.05", "กก./ซม²") -- but always in fonts
# that are NOT flagged by is_broken_byteswap_font (their overall bad-char
# ratio stays far below threshold), so Rule A below never touches them.
# Inside the one font that *is* flagged broken, the same codepoints are
# confirmed (by context) to be byte-swapped Thai letters instead (e.g.
# U+00B0 -> "ฐ", U+00B3 -> "ณ", U+00BA -> "บ"), so no exclusion list is
# needed here.

# ascii_code + ASCII_SHIFT_OFFSET == the intended TIS-620/cp874 byte, for
# the "raised" tone-mark glyph variants that land on ascii letters m..r.
ASCII_SHIFT_OFFSET = 123
ASCII_SHIFT_CHARS = set(range(ord("m"), ord("r") + 1))


def _decode_cp874_byte(byte_value):
    try:
        return bytes([byte_value]).decode("cp874")
    except (UnicodeDecodeError, ValueError):
        return chr(byte_value)


def is_broken_byteswap_font(codepoints, threshold=0.15, min_chars=8):
    """True if this run of extracted codepoints looks like it came from the
    cp874-byte-swap-bug font: a large fraction of its characters land in the
    Latin-1 Supplement block outside the legitimate symbols."""
    if len(codepoints) < min_chars:
        return False
    bad = sum(1 for cp in codepoints if 0xA0 <= cp <= 0xFF)
    return (bad / len(codepoints)) >= threshold


def fix_codepoints(codepoints, byteswap_font=False):
    """Return the corrected string for a run of raw extracted codepoints
    (as produced by page.get_text("rawdict")'s already-ToUnicode-mapped
    'c' values). Pass byteswap_font=True only for spans whose font was
    flagged by is_broken_byteswap_font -- applying the byte-swap/ASCII-shift
    rules outside that font would corrupt legitimate text (e.g. "mm" units,
    "30.00°")."""
    out = []
    n = len(codepoints)
    for i, cp in enumerate(codepoints):
        if cp in MODIFIER_LETTER_FIX:
            out.append(MODIFIER_LETTER_FIX[cp])
            continue
        if byteswap_font:
            if 0xA0 <= cp <= 0xFF:
                out.append(_decode_cp874_byte(cp))
                continue
            if cp in ASCII_SHIFT_CHARS:
                prev_cp = codepoints[i - 1] if i > 0 else 0
                next_cp = codepoints[i + 1] if i + 1 < n else 0

                def _is_thai_ish(c):
                    return 0xA0 <= c <= 0xFF or 0x0E00 <= c <= 0x0E7F

                if _is_thai_ish(prev_cp) or _is_thai_ish(next_cp):
                    out.append(_decode_cp874_byte(cp + ASCII_SHIFT_OFFSET))
                    continue
        out.append(chr(cp))
    return "".join(out)


def extract_fixed_spans(page):
    """Extract a page's text spans with the font bug fixed.

    Returns a list of dicts: {text, bbox, font_xref, font_basefont}, one per
    text span (page.get_text("rawdict") span), in document order.

    The byte-swap-bug detection (is_broken_byteswap_font) is evaluated once
    per font over ALL of the page's characters in that font, not per span --
    most spans (grid dimensions, single-letter labels) are far too short on
    their own to hit the char-count/ratio threshold reliably.
    """
    fontlist = page.get_fonts(full=True)
    xref_by_basefont = {}
    for f in fontlist:
        xref_by_basefont.setdefault(f[3], f[0])

    d = page.get_text("rawdict")
    span_records = []
    codepoints_by_font = {}
    for block in d["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                basefont = span["font"]
                chars = span.get("chars", [])
                codepoints = [c["c"] if isinstance(c["c"], int) else ord(c["c"]) for c in chars]
                span_records.append((basefont, span["bbox"], codepoints))
                codepoints_by_font.setdefault(basefont, []).extend(codepoints)

    byteswap_by_font = {
        basefont: is_broken_byteswap_font(cps) for basefont, cps in codepoints_by_font.items()
    }

    spans_out = []
    for basefont, bbox, codepoints in span_records:
        text = fix_codepoints(codepoints, byteswap_font=byteswap_by_font.get(basefont, False))
        spans_out.append(
            {
                "text": text,
                "bbox": bbox,
                "font_xref": xref_by_basefont.get(basefont),
                "font_basefont": basefont,
            }
        )
    return spans_out


def fix_page_text(page):
    """Convenience wrapper: return the page's text as one string (spans
    joined with newlines), with the font bug fixed. Drop-in-ish replacement
    for page.get_text() when a page uses the broken fonts."""
    return "\n".join(s["text"] for s in extract_fixed_spans(page))
