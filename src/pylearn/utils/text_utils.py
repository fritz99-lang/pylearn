"""PDF text cleanup utilities."""

from __future__ import annotations

import re
import unicodedata


def clean_text(text: str) -> str:
    """Clean text extracted from PDF, fixing common encoding issues."""
    if not text:
        return ""
    # Normalize unicode
    text = unicodedata.normalize("NFKC", text)
    # Fix common PDF ligatures
    replacements = {
        "\ufb01": "fi",
        "\ufb02": "fl",
        "\ufb03": "ffi",
        "\ufb04": "ffl",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "--",
        "\u2026": "...",
        "\u00a0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def clean_code_text(text: str) -> str:
    """Clean code extracted from PDF, preserving indentation."""
    text = clean_text(text)
    # Remove page headers/footers that crept into code blocks
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        # Skip lines that look like page numbers
        stripped = line.strip()
        if re.match(r"^\d+$", stripped) and len(stripped) <= 4:
            continue
        # Skip lines that look like chapter headers in code
        if re.match(r"^Chapter \d+[:.]\s", stripped):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces/newlines but preserve paragraph breaks."""
    # Collapse multiple spaces to single
    text = re.sub(r" {2,}", " ", text)
    # Collapse 3+ newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def is_page_header_or_footer(text: str, page_num: int = 0) -> bool:
    """Detect common page header/footer patterns in O'Reilly books."""
    stripped = text.strip()
    if not stripped:
        return True
    # Page number only
    if re.match(r"^\d{1,4}$", stripped):
        return True
    # "Chapter N" or "Part N" standalone
    if re.match(r"^(Chapter|Part)\s+\w+$", stripped, re.IGNORECASE):
        return True
    # Pipe-separated header: "123 | Chapter 5: Title"
    if re.match(r"^\d+\s*\|\s*(Chapter|Part)", stripped):
        return True
    # Generic running header/footer patterns (book-specific titles removed —
    # margin-based spatial filtering in PDFParser handles those)
    header_patterns = [
        r"www\.\S+\.\w+",  # URLs
    ]
    for pattern in header_patterns:
        if re.match(pattern, stripped, re.IGNORECASE):
            return True
    return False


def detect_repl_code(text: str) -> bool:
    """Check if code text looks like Python REPL (interactive) output."""
    stripped = text.strip()
    if not stripped:
        return False
    lines = stripped.split("\n")
    prompt_count = sum(1 for line in lines if line.startswith(">>> ") or line.startswith("... "))
    return prompt_count >= 1 and prompt_count / len(lines) > 0.2


def strip_repl_prompts(text: str) -> str:
    """Strip >>> and ... prompts from REPL code to make it runnable."""
    lines = text.strip().split("\n")
    code_lines = []
    for line in lines:
        if line.startswith(">>> "):
            code_lines.append(line[4:])
        elif line.startswith("... "):
            code_lines.append(line[4:])
        elif line.startswith(">>>"):
            code_lines.append(line[3:])
        elif line.startswith("..."):
            code_lines.append(line[3:])
        # Skip output lines (lines that don't start with prompts in REPL blocks)
    return "\n".join(code_lines)
