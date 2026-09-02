"""
clean_dxf -- materialize a cleaned copy of a DXF in two passes, save as a new
file. Never touches the source file.

⚠️ Corrected 2569-08-23 (see 07-drawing-signal-vs-noise.md §15): the project
owner caught that Pass 1 was deleting things that ARE relevant to the drawing
even though they aren't relevant to the BOQ -- dimensions, grid lines, title
blocks, specs, hatch patterns are legitimate, human-intended drawing content.
"Not counted as a quantity" must never mean "deleted from the file."

Pass 1 -- Safe-Delete only (04-category-schema.md's exclusion_rules.safe_to_delete):
removes ONLY confirmed zero-value software-internal artifacts -- AutoCAD's own
auto-generated names (anonymous blocks, built-in arrowhead blocks, DesignCenter/
audit-repair/render-plugin tags, the always-non-plotting DEFPOINTS layer). These
were never human-authored content, so removing them loses no real information.
This is is_safe_to_delete(), a much narrower check than is_excluded_layer()
(quantity_exclusion) -- DIM/GRID/TITLE/SPEC/HATCH/decorative blocks are excluded
from BOQ counting elsewhere in the pipeline, but they are NOT touched here.

Pass 2 -- Duplicate Purge (§5.3, aka AutoCAD's OVERKILL): drop LINE/LWPOLYLINE/
TEXT/MTEXT entities that are exact duplicates of one already kept on the same
layer -- same endpoints/vertices (direction-independent) for geometry, same
wording AND same position for text (added 2569-08-23, see §16 -- a repeated
pipe-size label like 'CW Ø3/4"' is only a duplicate if it sits at the SAME
spot; the same wording at a different spot is a different real pipe run and
must stay). Deleting a true duplicate loses zero information -- the kept copy
still represents the same real content -- so this is safe regardless of the
tier question above. This is what "ลบคำซ้ำๆ" targets -- a wall redrawn on top
of itself, a label copy-pasted onto itself. Tested against the WALL layer's
289,034 sqm problem: barely moved it (289,033.50) -- the real cause is
distinct hatch/detail loops sharing the layer, not duplicated geometry, so
Bounding Box Filter is still the open item for that (not built).

Known limitation: Duplicate Purge only catches EXACT-order or fully-reversed
duplicates. A closed rectangle re-drawn starting from a different corner
(rotated vertex order) will NOT be caught.

Pass 3 (opt-in, --standardize-font) -- repoint every TEXT STYLE to one font.
Confirmed real problem in newhouse 2569.dxf: 66 text styles reference dozens
of different fonts (CordiaUPC.ttf under a dozen different style names,
angsana.shx, thai2.shx, even broken references like an absolute path
'C:\\AECPLUS/fonts/SIMPLEX') -- evidence of copy-pasting from many source
files without cleanup. Does not rename/merge styles, only their font.

Pass 4 (opt-in, --purge-layers) -- remove layer table entries no entity
anywhere (any layout, any block definition) actually uses. Targets leftover
layers merged in from other projects' files that never got used here.
Never removes layer "0" (AutoCAD requires it to always exist).

Pass 5 (opt-in, --purge-styles) -- remove TEXT STYLE table entries nothing
references (checks TEXT/MTEXT/ATTDEF/ATTRIB entities AND every DIMSTYLE's
dimtxsty, since a style can be "in use" purely for dimensioning). Runs
before Pass 3 so standardize_fonts() only has to touch styles that survive.
Never removes "STANDARD".

Entity-type-aware, per the entity_type_warning in 04-category-schema.md:
- INSERT (block reference) entities are judged by their BLOCK NAME only
  (Pass 1) and never touched by Pass 2 (duplicate *placements* of a real
  fixture, e.g. two toilets that happen to be identical, are not noise).
- Every other entity type is judged by the LAYER it's on (Pass 1), and by
  geometry (Pass 2).

Usage:
    python clean_dxf.py "../../new house/cad/newhouse 2569.dxf"
    -> writes "../../new house/cad/newhouse 2569.cleaned.dxf"
    python clean_dxf.py "...dxf" --dup-tolerance 3   # stricter matching (fewer dupes found)
    python clean_dxf.py "...dxf" --no-duplicate-purge  # Pass 1 only
    python clean_dxf.py "...dxf" --extra-delete "SOME_LAYER"  # user-confirmed one-off deletion for this file only
"""

import argparse
import re
import sys
from pathlib import Path

import ezdxf

sys.path.insert(0, str(Path(__file__).parent))
from pynoi_parser import is_safe_to_delete  # noqa: E402


def _round_point(p, ndigits: int) -> tuple:
    return (round(p[0], ndigits), round(p[1], ndigits))


def _duplicate_key(e, ndigits: int):
    """None if this entity type isn't handled by Duplicate Purge yet."""
    if e.dxftype() == "LINE":
        p1 = _round_point(e.dxf.start, ndigits)
        p2 = _round_point(e.dxf.end, ndigits)
        endpoints = frozenset((p1, p2))
        return (e.dxf.layer, "LINE", endpoints)
    if e.dxftype() == "LWPOLYLINE":
        points = tuple(_round_point(p, ndigits) for p in e.get_points("xy"))
        if not points:
            return None
        # direction-independent: a line/loop drawn backwards is still the same duplicate
        canonical = min(points, tuple(reversed(points)))
        return (e.dxf.layer, "LWPOLYLINE", bool(e.closed), canonical)
    if e.dxftype() in ("TEXT", "MTEXT"):
        # same wording AND same position = a genuine duplicate (e.g. a pipe-size
        # label like 'CW Ø3/4"' copy-pasted on top of itself). Same wording at a
        # DIFFERENT position is NOT a duplicate -- it's a different real pipe run
        # that happens to be the same size, and must stay (see
        # 07-drawing-signal-vs-noise.md §16).
        content = (e.plain_text() if hasattr(e, "plain_text") else getattr(e, "text", "")).strip()
        if not content:
            return None
        pos = _round_point(e.dxf.insert, ndigits)
        return (e.dxf.layer, e.dxftype(), content, pos)
    return None


def purge_duplicates(msp, ndigits: int) -> list:
    """Returns the list of entities to delete -- keeps the first occurrence of
    each (layer, geometry) key, marks every later one on the same layer as a
    duplicate."""
    seen = set()
    to_delete = []
    for e in msp:
        key = _duplicate_key(e, ndigits)
        if key is None:
            continue
        if key in seen:
            to_delete.append(e)
        else:
            seen.add(key)
    return to_delete


def standardize_fonts(doc, font_name: str = "THSarabunPSK.ttf") -> int:
    """Set every TEXT STYLE's font to one font, uniformly. Confirmed real problem
    in newhouse 2569.dxf: 66 text styles reference dozens of different fonts
    (CordiaUPC.ttf under a dozen different style names, angsana.shx, thai2.shx,
    even broken/absolute-path references like 'C:\\AECPLUS/fonts/SIMPLEX' and
    '-DB 75 Narai') -- textbook evidence of copy-pasting content from many
    different source files without ever cleaning up. Does NOT rename or merge
    the styles (that would break which style each TEXT/MTEXT entity points to)
    -- only repoints every style's font to the same file."""
    changed = 0
    for style in doc.styles:
        if style.dxf.font != font_name:
            style.dxf.font = font_name
            style.dxf.bigfont = ""
            changed += 1
    return changed


_INLINE_FONT_CODE = re.compile(r"\\f[^;]*;")


def strip_inline_font_overrides(msp) -> int:
    """MTEXT can embed its OWN font override inside the text content itself
    (formatting code '\\f<typeface>|b#|i#|c#|p#;'), which takes precedence
    over whatever font the entity's TEXT STYLE points to -- standardize_fonts()
    only touches the style table, so it has zero effect on text carrying one
    of these. Confirmed real and serious in newhouse 2569.dxf: 179 MTEXT
    entities reference 7 different inline fonts (including 'TH SarabunPSK',
    which the project owner does not have installed) -- this is exactly what
    rendered as broken/disconnected Thai glyphs in GstarCAD after the style-
    table fix alone. Removing the override code (not replacing the font name)
    makes the text fall back to its style's font, i.e. whatever
    standardize_fonts() just set -- so run this together with that, not
    instead of it."""
    changed = 0
    for e in msp:
        if e.dxftype() != "MTEXT":
            continue
        new_text, n = _INLINE_FONT_CODE.subn("", e.text)
        if n:
            e.text = new_text
            changed += 1
    return changed


def purge_unused_layers(doc) -> list:
    """Remove layer table entries that no entity anywhere actually uses --
    modelspace, every paperspace layout, and every block definition (a layer
    can be used only inside a block and nowhere else). Layer '0' is never
    purged (AutoCAD requires it to always exist, even if unused)."""
    used = set()
    for layout in doc.layouts:
        for e in layout:
            if e.dxf.hasattr("layer"):
                used.add(e.dxf.layer)
    for block in doc.blocks:
        for e in block:
            if e.dxf.hasattr("layer"):
                used.add(e.dxf.layer)

    removed = []
    for layer in list(doc.layers):
        name = layer.dxf.name
        if name == "0" or name in used:
            continue
        doc.layers.remove(name)
        removed.append(name)
    return removed


def purge_unused_styles(doc) -> list:
    """Remove TEXT STYLE table entries no entity actually references --
    modelspace, every layout, every block definition (TEXT/MTEXT/ATTDEF/ATTRIB
    all carry a 'style' attribute), plus every DIMSTYLE's dimtxsty (the text
    style a dimension style uses for its own text -- a style can be 'in use'
    purely for dimensioning even with zero direct TEXT entities pointing to
    it). 'STANDARD' is never purged (AutoCAD requires it to always exist)."""
    used = set()
    for layout in doc.layouts:
        for e in layout:
            if e.dxftype() in ("TEXT", "MTEXT", "ATTDEF", "ATTRIB") and e.dxf.hasattr("style"):
                used.add(e.dxf.style)
    for block in doc.blocks:
        for e in block:
            if e.dxftype() in ("TEXT", "MTEXT", "ATTDEF", "ATTRIB") and e.dxf.hasattr("style"):
                used.add(e.dxf.style)
    for dimstyle in doc.dimstyles:
        style_name = dimstyle.dxf.get("dimtxsty", None)
        if style_name:
            used.add(style_name)

    removed = []
    for style in list(doc.styles):
        name = style.dxf.name
        if name == "STANDARD" or name in used:
            continue
        doc.styles.remove(name)
        removed.append(name)
    return removed


def clean(doc, extra_delete=None, dup_tolerance: int | None = 2, standardize_font: str | None = None, purge_layers: bool = False, purge_styles: bool = False) -> dict:
    msp = doc.modelspace()
    to_delete = []
    removed_by_layer = 0
    removed_by_block_name = 0

    for e in msp:
        if e.dxftype() == "INSERT":
            if is_safe_to_delete(e.dxf.name) or (extra_delete and any(x.upper() in e.dxf.name.upper() for x in extra_delete)):
                to_delete.append(e)
                removed_by_block_name += 1
            continue
        if is_safe_to_delete(e.dxf.layer) or (extra_delete and any(x.upper() in e.dxf.layer.upper() for x in extra_delete)):
            to_delete.append(e)
            removed_by_layer += 1

    total_before = len(list(msp))
    for e in to_delete:
        msp.delete_entity(e)

    removed_by_duplicate = 0
    if dup_tolerance is not None:
        duplicates = purge_duplicates(msp, dup_tolerance)
        removed_by_duplicate = len(duplicates)
        for e in duplicates:
            msp.delete_entity(e)

    kept = total_before - len(to_delete) - removed_by_duplicate

    # purge unused styles BEFORE repointing fonts -- fewer entries left to touch,
    # and a purged style's font never needed changing in the first place
    styles_purged = purge_unused_styles(doc) if purge_styles else []
    styles_changed = standardize_fonts(doc, standardize_font) if standardize_font else 0
    # inline \f overrides inside MTEXT content bypass the style table entirely --
    # must run whenever fonts are being standardized, not as a separate opt-in,
    # or the style-table fix silently does nothing for text carrying one of these
    inline_fonts_stripped = strip_inline_font_overrides(msp) if standardize_font else 0
    layers_purged = purge_unused_layers(doc) if purge_layers else []

    return {
        "removed_by_layer": removed_by_layer,
        "removed_by_block_name": removed_by_block_name,
        "removed_by_duplicate": removed_by_duplicate,
        "removed_total": len(to_delete) + removed_by_duplicate,
        "kept": kept,
        "styles_changed": styles_changed,
        "inline_fonts_stripped": inline_fonts_stripped,
        "layers_purged": layers_purged,
        "styles_purged": styles_purged,
    }


def next_versioned_output_path(source: Path) -> Path:
    """<name>.cleaned.v1.dxf, .v2.dxf, ... -- never overwrites a previous run's
    output, so before/after can still be compared (a real need surfaced during
    testing: the project owner couldn't tell whether a re-send actually picked
    up a fix, since the same filename was silently overwritten each time)."""
    base = source.stem
    directory = source.parent
    pattern = re.compile(rf"^{re.escape(base)}\.cleaned\.v(\d+)\.dxf$", re.I)
    max_version = 0
    for f in directory.glob(f"{base}.cleaned.v*.dxf"):
        m = pattern.match(f.name)
        if m:
            max_version = max(max_version, int(m.group(1)))
    return directory / f"{base}.cleaned.v{max_version + 1}.dxf"


def main() -> None:
    ap = argparse.ArgumentParser(description="delete only confirmed-safe noise + duplicate entities, save a cleaned DXF copy")
    ap.add_argument("file", type=Path)
    ap.add_argument("--extra-delete", default="", help="comma-separated extra layer/block names YOU have confirmed are safe to delete for this file only -- not a guess, a decision you're making")
    ap.add_argument("--out", type=Path, default=None, help="output path (default: auto-versioned <name>.cleaned.vN.dxf next to the source, never overwrites a previous run)")
    ap.add_argument("--dup-tolerance", type=int, default=2, help="round coordinates to N decimal places before comparing (default 2); higher = stricter match, fewer duplicates found")
    ap.add_argument("--no-duplicate-purge", action="store_true", help="Pass 1 (safe-delete only) only, skip Duplicate Purge")
    ap.add_argument("--standardize-font", default=None, help="set every TEXT STYLE's font to this file, e.g. THSarabunPSK.ttf (default: off)")
    ap.add_argument("--purge-layers", action="store_true", help="remove layer table entries no entity anywhere actually uses (default: off)")
    ap.add_argument("--purge-styles", action="store_true", help="remove text style table entries no entity/dimstyle anywhere actually uses (default: off)")
    args = ap.parse_args()
    extra_delete = [kw.strip() for kw in args.extra_delete.split(",") if kw.strip()]

    out_path = args.out or next_versioned_output_path(args.file)
    if out_path.resolve() == args.file.resolve():
        raise SystemExit("refusing to overwrite the source file -- pass --out or rename")

    doc = ezdxf.readfile(str(args.file))
    stats = clean(
        doc,
        extra_delete,
        dup_tolerance=None if args.no_duplicate_purge else args.dup_tolerance,
        standardize_font=args.standardize_font,
        purge_layers=args.purge_layers,
        purge_styles=args.purge_styles,
    )
    doc.saveas(str(out_path))

    def _list_preview(names: list) -> str:
        if not names:
            return ""
        shown = ", ".join(names[:10])
        return f": {shown}{'...' if len(names) > 10 else ''}"

    print(f"Source:  {args.file}  ({stats['removed_total'] + stats['kept']} entities in modelspace)")
    print(f"Removed: {stats['removed_total']}  (by layer: {stats['removed_by_layer']}, by block name: {stats['removed_by_block_name']}, duplicates: {stats['removed_by_duplicate']})")
    print(f"Kept:    {stats['kept']}  (DIM/GRID/TITLE/SPEC/HATCH/decorative etc. all kept -- not counted for BOQ elsewhere, but not deleted here)")
    if args.standardize_font:
        print(f"Fonts:   {stats['styles_changed']} text style(s) repointed to {args.standardize_font}, "
              f"{stats['inline_fonts_stripped']} MTEXT inline font override(s) stripped")
    if args.purge_layers:
        print(f"Purged:  {len(stats['layers_purged'])} unused layer(s){_list_preview(stats['layers_purged'])}")
    if args.purge_styles:
        print(f"Purged:  {len(stats['styles_purged'])} unused text style(s){_list_preview(stats['styles_purged'])}")
    print(f"Saved -> {out_path}")


if __name__ == "__main__":
    main()
