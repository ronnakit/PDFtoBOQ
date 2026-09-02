"""Diagnose what kind of content a PDF actually contains, page by page.

Distinguishes three failure/success modes we've found in real client files:
  - vector_with_text   : real CAD "Plot to PDF" export (best case — some DXF-style signal usable)
  - vector_no_text     : exploded/tessellated vector, text drawn as raw line segments (Kadfarang case)
  - raster_scan        : page is just an embedded image, no vector/text at all (scanned paper)
  - empty              : nothing found (blank page or unsupported content)

Usage:
    python pdf_inspector.py "<path to pdf>" [--pages N]
"""
import argparse
import sys

import fitz


def estimate_dpi(img_w_px, img_h_px, page_w_pt, page_h_pt):
    if not page_w_pt or not page_h_pt:
        return None
    dpi_x = img_w_px / (page_w_pt / 72.0)
    dpi_y = img_h_px / (page_h_pt / 72.0)
    return round((dpi_x + dpi_y) / 2, 1)


def classify_page(vector_objs, text_len, image_count):
    if vector_objs == 0 and text_len == 0 and image_count >= 1:
        return "raster_scan"
    if vector_objs > 0 and text_len == 0:
        return "vector_no_text"
    if text_len > 0:
        return "vector_with_text"
    return "empty"


def analyze_page(doc, page, index):
    text = page.get_text("text")
    drawings = page.get_drawings()
    images = page.get_images(full=True)

    image_info = []
    for img in images:
        xref = img[0]
        base = doc.extract_image(xref)
        dpi = estimate_dpi(base["width"], base["height"], page.rect.width, page.rect.height)
        image_info.append({
            "width": base["width"],
            "height": base["height"],
            "ext": base["ext"],
            "estimated_dpi": dpi,
        })

    curve_count = sum(
        1 for d in drawings for item in d.get("items", []) if item[0] == "c"
    )

    kind = classify_page(len(drawings), len(text), len(images))

    return {
        "page": index + 1,
        "kind": kind,
        "page_size_pt": (round(page.rect.width, 1), round(page.rect.height, 1)),
        "vector_objs": len(drawings),
        "curve_segments": curve_count,
        "text_len": len(text),
        "text_sample": text[:40],
        "images": image_info,
    }


def analyze_pdf(path, max_pages=None):
    doc = fitz.open(path)
    ocgs = doc.get_ocgs()
    n_pages = len(doc) if max_pages is None else min(max_pages, len(doc))
    pages = [analyze_page(doc, doc[i], i) for i in range(n_pages)]

    kinds = {p["kind"] for p in pages}
    if kinds == {"vector_with_text"}:
        overall = "vector_with_text"
    elif kinds == {"raster_scan"}:
        overall = "raster_scan"
    elif kinds == {"vector_no_text"}:
        overall = "vector_no_text"
    else:
        overall = "mixed(" + ",".join(sorted(kinds)) + ")"

    return {
        "path": path,
        "total_pages": len(doc),
        "pages_checked": n_pages,
        "ocg_layer_count": len(ocgs),
        "metadata": doc.metadata,
        "overall_kind": overall,
        "pages": pages,
    }


def print_report(report):
    print(f"file: {report['path']}")
    print(f"pages: {report['pages_checked']}/{report['total_pages']} checked")
    print(f"OCG (layer) count: {report['ocg_layer_count']}")
    meta = report["metadata"]
    print(f"producer: {meta.get('producer')!r}  creator: {meta.get('creator')!r}")
    print(f"overall classification: {report['overall_kind']}")
    print()
    for p in report["pages"]:
        img_desc = ", ".join(
            f"{im['width']}x{im['height']}px ~{im['estimated_dpi']}dpi ({im['ext']})"
            for im in p["images"]
        ) or "-"
        print(
            f"  page {p['page']:>2}: kind={p['kind']:<16} vector_objs={p['vector_objs']:<6} "
            f"curves={p['curve_segments']:<5} text_len={p['text_len']:<6} images=[{img_desc}]"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf_path")
    parser.add_argument("--pages", type=int, default=None, help="limit to first N pages")
    args = parser.parse_args()

    report = analyze_pdf(args.pdf_path, max_pages=args.pages)
    print_report(report)


if __name__ == "__main__":
    main()
