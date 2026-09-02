"""Detect repeated door-label text (e.g. "D1") on a scanned/raster PDF page via
normalized cross-correlation template matching — pure numpy + PyMuPDF, no
OCR/OpenCV (neither is installed in this environment; see 10-pdf-mvp-spec.md).

Built to test whether a raster construction-permit PDF (zero vector, zero
extractable text — see pdf_inspector.py findings) can still support *some*
automated quantity-counting, as an experiment separate from the v1 MVP's
manual-click workflow.

Usage:
    python pdf_door_label_matcher.py <pdf> <page_number_1indexed> \
        --template <template.png> [--dpi 300] [--threshold 0.55] [--min-dist 40]
"""
import argparse

import fitz
import numpy as np
from PIL import Image


def load_page_gray(pdf_path, page_index, dpi):
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    return arr.astype(np.float64)


def load_template_gray(path):
    img = Image.open(path).convert("L")
    return np.asarray(img, dtype=np.float64)


def ncc_map(image, template):
    """Normalized cross-correlation score map (like cv2.matchTemplate TM_CCOEFF_NORMED),
    implemented via FFT convolution since OpenCV isn't available here."""
    inv_image = 255.0 - image
    inv_template = 255.0 - template
    th, tw = inv_template.shape
    H, W = inv_image.shape
    n = th * tw

    t_zero = inv_template - inv_template.mean()
    t_norm = np.sqrt(np.sum(t_zero ** 2))

    fft_shape = (H + th - 1, W + tw - 1)
    fi = np.fft.rfft2(inv_image, fft_shape)
    ft = np.fft.rfft2(t_zero[::-1, ::-1], fft_shape)
    num_full = np.fft.irfft2(fi * ft, fft_shape)
    numerator = num_full[th - 1:H, tw - 1:W]

    ones = np.ones((th, tw))
    f_ones = np.fft.rfft2(ones[::-1, ::-1], fft_shape)
    fi_sq = np.fft.rfft2(inv_image ** 2, fft_shape)
    local_sum = np.fft.irfft2(fi * f_ones, fft_shape)[th - 1:H, tw - 1:W]
    local_sumsq = np.fft.irfft2(fi_sq * f_ones, fft_shape)[th - 1:H, tw - 1:W]

    local_var = np.maximum(local_sumsq - (local_sum ** 2) / n, 0)
    local_std = np.sqrt(local_var)

    denom = local_std * t_norm
    return np.where(denom > 1e-6, numerator / (denom + 1e-6), 0.0)


def find_peaks(score_map, threshold, min_dist):
    ys, xs = np.where(score_map >= threshold)
    candidates = sorted(zip(score_map[ys, xs], ys, xs), reverse=True)
    kept = []
    for s, y, x in candidates:
        if all((y - ky) ** 2 + (x - kx) ** 2 >= min_dist ** 2 for _, ky, kx in kept):
            kept.append((s, y, x))
    return kept


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf")
    ap.add_argument("page", type=int, help="1-indexed page number")
    ap.add_argument("--template", required=True)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--threshold", type=float, default=0.55)
    ap.add_argument("--min-dist", type=int, default=40)
    args = ap.parse_args()

    image = load_page_gray(args.pdf, args.page - 1, args.dpi)
    template = load_template_gray(args.template)
    score = ncc_map(image, template)
    peaks = find_peaks(score, args.threshold, args.min_dist)

    th, tw = template.shape
    print(f"template size: {tw}x{th}px, threshold={args.threshold}, min_dist={args.min_dist}")
    print(f"matches found: {len(peaks)}")
    for s, y, x in peaks:
        print(f"  score={s:.3f}  top-left=({x},{y})  center=({x + tw // 2},{y + th // 2})")


if __name__ == "__main__":
    main()
