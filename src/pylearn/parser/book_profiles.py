# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Per-book parsing configuration profiles.

Each book has different font names, sizes, and structural patterns.
Run scripts/analyze_pdf_fonts.py on each book to discover these values.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BookProfile:
    """Configuration for parsing a specific book's PDF."""

    name: str
    language: str = "python"  # "python", "cpp", "c"

    # Font size thresholds
    heading1_min_size: float = 18.0
    heading2_min_size: float = 14.0
    heading3_min_size: float = 12.0
    body_size: float = 10.0
    code_size: float = 9.0

    # Font name patterns (substrings to match)
    monospace_fonts: list[str] = field(
        default_factory=lambda: [
            "Courier",
            "Mono",
            "Consolas",
            "Menlo",
            "DejaVuSansMono",
            "LucidaConsole",
            "Ubuntu Mono",
            "SourceCodePro",
        ]
    )
    heading_fonts: list[str] = field(default_factory=list)

    # Chapter detection
    chapter_pattern: str = r"^Chapter\s+(\d+)\s*[\.:]"
    part_pattern: str = r"^Part\s+([IVXLC]+)\."

    # Page range to skip (front matter, index)
    skip_pages_start: int = 0
    skip_pages_end: int = 0

    # Exercise patterns
    exercise_start_pattern: str = ""
    exercise_answer_pattern: str = ""

    # Content area margins (to skip headers/footers)
    margin_top: float = 72.0  # ~1 inch
    margin_bottom: float = 72.0
    margin_left: float = 54.0
    margin_right: float = 54.0

    def __post_init__(self) -> None:
        """Validate that heading thresholds are ordered correctly."""
        if not (self.heading1_min_size >= self.heading2_min_size >= self.heading3_min_size):
            # Auto-fix reversed thresholds
            sizes = sorted([self.heading1_min_size, self.heading2_min_size, self.heading3_min_size], reverse=True)
            self.heading1_min_size, self.heading2_min_size, self.heading3_min_size = sizes
        # Pre-lowercase monospace font names and initialize lookup cache
        self._mono_lower: list[str] = [m.lower() for m in self.monospace_fonts]
        self._mono_cache: dict[str, bool] = {}

    def is_monospace(self, font_name: str) -> bool:
        """Check if a font name indicates monospace."""
        if not font_name:
            return False
        if font_name not in self._mono_cache:
            name_lower = font_name.lower()
            self._mono_cache[font_name] = any(m in name_lower for m in self._mono_lower)
        return self._mono_cache[font_name]


# Pre-configured profiles for the three O'Reilly books

LEARNING_PYTHON = BookProfile(
    name="learning_python",
    heading1_min_size=20.0,
    heading2_min_size=15.0,
    heading3_min_size=12.5,
    body_size=10.0,
    code_size=8.5,
    chapter_pattern=r"^Chapter\s+(\d+)\s*[\.:]",
    part_pattern=r"^Part\s+([IVXLCDM]+)\s*[\.:]",
    skip_pages_start=20,  # Front matter
    skip_pages_end=30,  # Index
    exercise_start_pattern=r"Test Your Knowledge:\s*Quiz",
    exercise_answer_pattern=r"Test Your Knowledge:\s*Answers",
)

PYTHON_COOKBOOK = BookProfile(
    name="python_cookbook",
    heading1_min_size=20.0,
    heading2_min_size=14.0,
    heading3_min_size=11.5,
    body_size=10.0,
    code_size=8.5,
    chapter_pattern=r"^Chapter\s+(\d+)\s*[\.:]",
    skip_pages_start=15,
    skip_pages_end=15,
    exercise_start_pattern=r"^(\d+\.\d+)\.\s+",  # Recipe pattern: "1.1. "
)

PROGRAMMING_PYTHON = BookProfile(
    name="programming_python",
    heading1_min_size=20.0,
    heading2_min_size=15.0,
    heading3_min_size=12.0,
    body_size=10.0,
    code_size=8.5,
    chapter_pattern=r"^Chapter\s+(\d+)\s*[\.:]",
    part_pattern=r"^Part\s+([IVXLCDM]+)\s*[\.:]",
    skip_pages_start=20,
    skip_pages_end=30,
)


# Generic C++ profile — adjust after running analyze_pdf_fonts.py on your books
CPP_GENERIC = BookProfile(
    name="cpp_generic",
    language="cpp",
    heading1_min_size=18.0,
    heading2_min_size=14.0,
    heading3_min_size=12.0,
    body_size=10.0,
    code_size=8.5,
    chapter_pattern=r"^Chapter\s+(\d+)\s*[\.:]",
    skip_pages_start=15,
    skip_pages_end=15,
)

CPP_PRIMER = BookProfile(
    name="cpp_primer",
    language="cpp",
    heading1_min_size=20.0,
    heading2_min_size=14.0,
    heading3_min_size=12.0,
    body_size=10.0,
    code_size=8.5,
    chapter_pattern=r"^Chapter\s+(\d+)\s*[\.:]",
    skip_pages_start=20,
    skip_pages_end=30,
)

EFFECTIVE_CPP = BookProfile(
    name="effective_cpp",
    language="cpp",
    heading1_min_size=18.0,
    heading2_min_size=14.0,
    heading3_min_size=12.0,
    body_size=10.0,
    code_size=8.5,
    chapter_pattern=r"^(?:Item|Chapter)\s+(\d+)",
    skip_pages_start=15,
    skip_pages_end=15,
)


PROFILES: dict[str, BookProfile] = {
    "learning_python": LEARNING_PYTHON,
    "python_cookbook": PYTHON_COOKBOOK,
    "programming_python": PROGRAMMING_PYTHON,
    "cpp_generic": CPP_GENERIC,
    "cpp_primer": CPP_PRIMER,
    "effective_cpp": EFFECTIVE_CPP,
}


def get_profile(name: str) -> BookProfile:
    """Get a book profile by name, or return a default profile."""
    return PROFILES.get(name, BookProfile(name=name))


def get_auto_profile(pdf_path: str, language: str = "python") -> BookProfile:
    """Auto-detect font thresholds from a PDF and return a BookProfile."""
    from pylearn.parser.font_analyzer import FontAnalyzer

    analyzer = FontAnalyzer(pdf_path)
    return analyzer.build_profile(language)
