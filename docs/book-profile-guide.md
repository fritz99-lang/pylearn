# Custom Book Profile Creation Guide

A **book profile** tells the PyLearn parser how to classify text in a PDF — what's a heading, what's body text, what's code. Each book uses different fonts and sizes, so the parser needs a profile to know the rules.

## When do you need a custom profile?

PyLearn has **auto-detection** (`get_auto_profile`) that samples your PDF and guesses the thresholds. Try that first — it works well for standard O'Reilly formatting. You need a custom profile when:

- Auto-detect misclassifies headings (too many or too few)
- Code blocks aren't being recognized
- Chapters aren't splitting in the right places
- The book uses unusual fonts or layout (non-O'Reilly books especially)

## Workflow overview

1. **Analyze** your PDF to see what fonts it uses
2. **Create** a `BookProfile` with the right thresholds
3. **Register** the profile and book entry
4. **Test** in PyLearn and iterate

---

## Step 1: Analyze your PDF

Run the font analysis script:

```bash
python scripts/analyze_pdf_fonts.py path/to/book.pdf
```

To scan only the first N pages (faster for large books):

```bash
python scripts/analyze_pdf_fonts.py path/to/book.pdf --pages 50
```

### Reading the output

The script prints a table like this:

```
Font                                      Size Flags  Bold  Ital   Count  Pages  Sample
----------------------------------------------------------------------------
TimesNewRomanPSMT                         10.0     0     .     .    8452    312  Python is a general-purpose programming
CourierNewPSMT                             8.5     0     .     .    3210    298  def hello_world():
TimesNewRomanPS-BoldMT                    20.0    16     Y     .      84     28  Chapter 1: Getting Started
TimesNewRomanPS-BoldMT                    15.0    16     Y     .     312     85  Variables and Assignments
TimesNewRomanPS-BoldMT                    12.5    16     Y     .     580    142  String Formatting
TimesNewRomanPS-ItalicMT                  10.0     2     .     Y     420    180  Note: This is important
```

After the table, you'll see two summary sections:

- **MONOSPACE CANDIDATES** — fonts with "Mono", "Courier", "Console", or "Code" in the name
- **HEADING CANDIDATES** — fonts larger than 12pt that are bold

### How to identify each role

| Role | How to spot it |
|------|---------------|
| **Body font** | Highest count, non-monospace. In the example above: `TimesNewRomanPSMT` at 10.0pt |
| **Code font** | Highest count, monospace (Courier, Mono, etc). Above: `CourierNewPSMT` at 8.5pt |
| **Heading 1** | Largest bold font. Above: 20.0pt bold = chapter titles |
| **Heading 2** | Next largest bold font. Above: 15.0pt bold = section headers |
| **Heading 3** | Next largest bold font. Above: 12.5pt bold = subsection headers |

---

## Step 2: Create the profile

Profiles live in `src/pylearn/parser/book_profiles.py`.

### BookProfile field reference

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | *(required)* | Unique identifier for this profile |
| `language` | `str` | `"python"` | Language for syntax highlighting: `"python"`, `"cpp"`, `"c"`, `"html"` |
| `heading1_min_size` | `float` | `18.0` | Minimum font size for H1 (chapter titles) |
| `heading2_min_size` | `float` | `14.0` | Minimum font size for H2 (sections) |
| `heading3_min_size` | `float` | `12.0` | Minimum font size for H3 (subsections) |
| `body_size` | `float` | `10.0` | Expected body text font size |
| `code_size` | `float` | `9.0` | Expected code font size |
| `monospace_fonts` | `list[str]` | `["Courier", "Mono", ...]` | Substrings to match monospace font names |
| `heading_fonts` | `list[str]` | `[]` | Substrings to match heading-specific fonts (if any) |
| `chapter_pattern` | `str` | `r"^Chapter\s+(\d+)\s*[\.:]"` | Regex to detect chapter starts |
| `part_pattern` | `str` | `r"^Part\s+([IVXLC]+)\."` | Regex to detect part divisions |
| `skip_pages_start` | `int` | `0` | Pages to skip at the beginning (front matter) |
| `skip_pages_end` | `int` | `0` | Pages to skip at the end (index, back matter) |
| `exercise_start_pattern` | `str` | `""` | Regex for exercise question sections |
| `exercise_answer_pattern` | `str` | `""` | Regex for exercise answer sections |
| `margin_top` | `float` | `72.0` | Top margin in points (~1 inch) to skip headers |
| `margin_bottom` | `float` | `72.0` | Bottom margin in points to skip footers |
| `margin_left` | `float` | `54.0` | Left margin in points |
| `margin_right` | `float` | `54.0` | Right margin in points |

### How heading detection works

This is important to understand when setting thresholds:

- **H1:** Detected by size alone — any text with `font_size >= heading1_min_size`
- **H2:** Requires size AND bold — `font_size >= heading2_min_size` and the font must be bold
- **H3:** Requires size AND bold — `font_size >= heading3_min_size` and the font must be bold
- **Font matching** is case-insensitive substring matching (e.g., `"Courier"` matches `"CourierNewPSMT"`)

### Setting the threshold values

The `_min_size` fields are **minimums**, not exact matches. Set them **between** the sizes you see in the font table:

- If H1 text is 20.0pt and H2 text is 15.0pt, set `heading1_min_size` somewhere between them (e.g., 17.0 or 18.0)
- If H2 text is 15.0pt and H3 text is 12.5pt, set `heading2_min_size` to 14.0 or so
- If H3 text is 12.5pt and body is 10.0pt, set `heading3_min_size` to 11.0 or 12.0

The profile auto-validates that `heading1 >= heading2 >= heading3`. If you get them out of order, it auto-sorts them.

### Template

Copy this into `book_profiles.py` and fill in your values:

```python
MY_BOOK = BookProfile(
    name="my_book",
    language="python",                          # or "cpp", "c", "html"
    # Font thresholds — set between observed font sizes
    heading1_min_size=18.0,                     # chapter titles
    heading2_min_size=14.0,                     # section headers
    heading3_min_size=12.0,                     # subsection headers
    body_size=10.0,                             # body text
    code_size=8.5,                              # code blocks
    # Chapter detection
    chapter_pattern=r"^Chapter\s+(\d+)\s*[\.:]",
    # Pages to skip
    skip_pages_start=15,                        # front matter
    skip_pages_end=15,                          # index / back matter
)
```

---

## Step 3: Register the book

### Add profile to the PROFILES dict

In `src/pylearn/parser/book_profiles.py`, add your profile to the `PROFILES` dictionary near the bottom of the file:

```python
PROFILES: dict[str, BookProfile] = {
    "learning_python": LEARNING_PYTHON,
    "python_cookbook": PYTHON_COOKBOOK,
    # ... existing profiles ...
    "my_book": MY_BOOK,                        # <-- add this
}
```

### Add book entry to books.json

In `config/books.json`, add an entry for your book:

```json
{
  "books": [
    {
      "book_id": "my_book_first_edition",
      "title": "My Book First Edition",
      "pdf_path": "C:/path/to/My_Book.pdf",
      "profile_name": "my_book"
    }
  ]
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `book_id` | Yes | Unique identifier (lowercase, underscores) |
| `title` | Yes | Display name shown in PyLearn's book selector |
| `pdf_path` | Yes | Absolute path to the PDF file (use forward slashes) |
| `profile_name` | No | Name matching a key in `PROFILES`. Leave empty `""` for auto-detect |
| `language` | No | Override language if different from the profile's default |

---

## Step 4: Test and iterate

1. **Launch PyLearn:** `python -m pylearn`
2. **Select your book** from the book dropdown
3. **Let it parse** — first parse builds the cache

### What to look for

- **Headings:** Are chapter titles and section headers detected? Check the table of contents panel.
- **Code blocks:** Are code samples rendered with syntax highlighting? They should appear in a monospace font with a shaded background.
- **Chapter splits:** Does each chapter start at the right place? Navigate through the TOC.
- **Body text:** Is regular text displaying normally, without being classified as code or headings?

### Re-parsing after changes

After editing a profile, you need to clear the cache:

**Book > Re-parse Current Book** (or delete the cache file from `data/`)

### Common issues

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Body text shows as heading | Heading thresholds too low | Raise `heading2_min_size` / `heading3_min_size` |
| Headings not detected | Thresholds too high | Lower the threshold for that heading level |
| Code not recognized | Monospace font not in the list | Add the font name substring to `monospace_fonts` |
| Headers/footers in content | Margins too small | Increase `margin_top` / `margin_bottom` |
| Front matter included | `skip_pages_start` too low | Increase it — check the PDF page numbers |
| Index pages included | `skip_pages_end` too low | Increase it |
| Chapters not splitting | `chapter_pattern` doesn't match | Check the exact text of chapter headings and adjust the regex |
| Wrong syntax highlighting | `language` field incorrect | Set to `"python"`, `"cpp"`, `"c"`, or `"html"` |

---

## Reference: Built-in profiles

These six profiles ship with PyLearn. If your book is similar to one of these, start from it and adjust.

| Profile | Language | H1 min | H2 min | H3 min | Body | Code | Skip start | Skip end |
|---------|----------|--------|--------|--------|------|------|-----------|----------|
| `learning_python` | python | 20.0 | 15.0 | 12.5 | 10.0 | 8.5 | 20 | 30 |
| `python_cookbook` | python | 20.0 | 14.0 | 11.5 | 10.0 | 8.5 | 15 | 15 |
| `programming_python` | python | 20.0 | 15.0 | 12.0 | 10.0 | 8.5 | 20 | 30 |
| `cpp_generic` | cpp | 18.0 | 14.0 | 12.0 | 10.0 | 8.5 | 15 | 15 |
| `cpp_primer` | cpp | 20.0 | 14.0 | 12.0 | 10.0 | 8.5 | 20 | 30 |
| `effective_cpp` | cpp | 18.0 | 14.0 | 12.0 | 10.0 | 8.5 | 15 | 15 |

---

## Tips

- **Try auto-detect first.** If you leave `profile_name` empty in `books.json`, PyLearn uses `get_auto_profile()` which samples the PDF and computes thresholds automatically. Only create a custom profile if auto-detect gets it wrong.
- **Start from the closest built-in profile.** Copy an existing profile that matches your book's publisher/style, rename it, and tweak the values. This is faster than starting from scratch.
- **Margins** are only worth adjusting if you see page headers or footers bleeding into the parsed content. The defaults (72pt top/bottom) work for most books.
- **`monospace_fonts`** — the default list covers Courier, Mono, Consolas, Menlo, and several others. You only need to add entries if your book uses an unusual code font that isn't matched (check the MONOSPACE CANDIDATES section of the analysis output).
- **Exercise patterns** are only needed if your book has structured exercises (like "Test Your Knowledge" sections). Most books don't need these.
- **`chapter_pattern`** — if your book uses "Lesson" instead of "Chapter", or numbers chapters differently, update this regex. For example: `r"^Lesson\s+(\d+)"` or `r"^(?:Item|Chapter)\s+(\d+)"`.
