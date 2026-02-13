"""Diagnostic script: dump font information from a PDF.

Usage: python scripts/analyze_pdf_fonts.py <path_to_pdf> [--pages N]

Outputs a table of all fonts used in the PDF with their sizes, flags,
and sample text. Use this to build book profiles for the parser.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import fitz


def analyze_fonts(pdf_path: str, max_pages: int = 0) -> None:
    doc = fitz.open(pdf_path)
    total = len(doc)
    print(f"PDF: {pdf_path}")
    print(f"Total pages: {total}")
    print()

    font_stats: dict[str, dict] = {}
    pages_to_scan = min(total, max_pages) if max_pages > 0 else total

    for page_num in range(pages_to_scan):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    font = span.get("font", "unknown")
                    size = round(span.get("size", 0), 1)
                    flags = span.get("flags", 0)
                    key = f"{font}|{size}|{flags}"
                    if key not in font_stats:
                        font_stats[key] = {
                            "font": font,
                            "size": size,
                            "flags": flags,
                            "is_bold": bool(flags & 16),
                            "is_italic": bool(flags & 2),
                            "is_superscript": bool(flags & 1),
                            "count": 0,
                            "pages": set(),
                            "sample": "",
                        }
                    font_stats[key]["count"] += 1
                    font_stats[key]["pages"].add(page_num)
                    if not font_stats[key]["sample"]:
                        text = span.get("text", "").strip()
                        if text and len(text) > 3:
                            font_stats[key]["sample"] = text[:60]

    doc.close()

    # Sort by frequency
    sorted_stats = sorted(font_stats.values(), key=lambda x: -x["count"])

    print(f"{'Font':<40} {'Size':>5} {'Flags':>5} {'Bold':>5} {'Ital':>5} {'Count':>7} {'Pages':>6}  Sample")
    print("-" * 140)
    for s in sorted_stats:
        print(
            f"{s['font']:<40} {s['size']:>5} {s['flags']:>5} "
            f"{'Y' if s['is_bold'] else '.':>5} "
            f"{'Y' if s['is_italic'] else '.':>5} "
            f"{s['count']:>7} {len(s['pages']):>6}  {s['sample']}"
        )

    # Summary
    print()
    print("MONOSPACE CANDIDATES (fonts with 'Mono', 'Courier', 'Console', 'Code'):")
    for s in sorted_stats:
        name_lower = s["font"].lower()
        if any(kw in name_lower for kw in ["mono", "courier", "console", "code"]):
            print(f"  {s['font']} (size={s['size']}, count={s['count']})")

    print()
    print("HEADING CANDIDATES (size > 12, bold):")
    for s in sorted_stats:
        if s["size"] > 12 and s["is_bold"]:
            print(f"  {s['font']} (size={s['size']}, count={s['count']}, sample={s['sample'][:40]})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_pdf_fonts.py <path_to_pdf> [--pages N]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    max_pages = 0
    if "--pages" in sys.argv:
        idx = sys.argv.index("--pages")
        if idx + 1 < len(sys.argv):
            max_pages = int(sys.argv[idx + 1])

    analyze_fonts(pdf_path, max_pages)
