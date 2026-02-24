# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Convert assets/pylearn.ico to assets/pylearn.icns for macOS builds.

Requires Pillow:  pip install Pillow

Usage:
    python scripts/generate_icns.py
"""

import sys
from pathlib import Path

SIZES = [16, 32, 48, 128, 256, 512]


def main() -> int:
    try:
        from PIL import Image
    except ImportError:
        print("ERROR: Pillow is not installed.")
        print("  Install it with: pip install Pillow")
        return 1

    project_root = Path(__file__).resolve().parent.parent
    ico_path = project_root / "assets" / "pylearn.ico"
    icns_path = project_root / "assets" / "pylearn.icns"

    if not ico_path.exists():
        print(f"ERROR: source icon not found: {ico_path}")
        return 1

    img = Image.open(ico_path)

    # Extract the largest frame from the ICO
    best = None
    best_size = 0
    for frame_idx in range(getattr(img, "n_frames", 1)):
        img.seek(frame_idx)
        w, _h = img.size
        if w >= best_size:
            best_size = w
            best = img.copy()

    if best is None:
        print("ERROR: could not read any frames from ICO file")
        return 1

    # Ensure RGBA
    if best.mode != "RGBA":
        best = best.convert("RGBA")

    # Build the sizes list for ICNS
    icon_sizes = []
    for s in SIZES:
        if s <= best_size:
            icon_sizes.append((s, s))

    if not icon_sizes:
        icon_sizes = [(best_size, best_size)]

    # Save as ICNS — Pillow handles the multi-size format
    best.save(icns_path, format="ICNS", sizes=icon_sizes)

    size_kb = icns_path.stat().st_size / 1024
    print(f"Generated {icns_path} ({size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
