#!/usr/bin/env python3
# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""LLM-assisted content generation for PyLearn.

Generate quiz questions, code challenges, and project steps using Claude API.
All output goes to a drafts/ staging directory for human review before committing.

Usage:
    # Generate quiz questions
    python scripts/generate_content.py --book learning_python_fifth_edition --chapter 6 --type quiz

    # Generate code challenges
    python scripts/generate_content.py --book cpp_primer_fifth_edition --chapter 3 --type challenge

    # Generate a project step
    python scripts/generate_content.py --book cpp_primer_fifth_edition --chapter 3 --type project \\
        --project-title "Matrix Calculator" --project-desc "Build a matrix calculator from scratch"

    # Preview the prompt without calling the API
    python scripts/generate_content.py --book learning_python_fifth_edition --chapter 6 --type quiz --dry-run

    # Validate a draft file
    python scripts/generate_content.py --validate drafts/cpp_primer_fifth_edition/quizzes/ch03.json

    # Accept a draft into content/
    python scripts/generate_content.py --accept drafts/cpp_primer_fifth_edition/quizzes/ch03.json

Requires: pip install anthropic  (or: pip install pylearn-reader[content-gen])
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pylearn.core.constants import APP_DIR, CACHE_DIR  # noqa: E402
from pylearn.core.models import (  # noqa: E402
    Book,
    ChallengeSet,
    ProjectStep,
    QuizSet,
)

CONTENT_DIR = APP_DIR / "content"
DRAFTS_DIR = PROJECT_ROOT / "drafts"

# Book ID -> short prefix for content IDs
BOOK_PREFIXES: dict[str, str] = {
    "learning_python_fifth_edition": "lp",
    "cpp_primer_fifth_edition": "cp",
    "cpp_primer": "cp",
    "effective_cpp": "ec",
    "html_css_design": "hc",
}


def _get_prefix(book_id: str) -> str:
    """Get the short prefix for content IDs."""
    if book_id in BOOK_PREFIXES:
        return BOOK_PREFIXES[book_id]
    # Fallback: first letter of each word
    parts = book_id.replace("_", " ").split()
    return "".join(p[0] for p in parts if p and p[0].isalpha())[:3].lower()


# ---------------------------------------------------------------------------
# Chapter context extraction
# ---------------------------------------------------------------------------


@dataclass
class ChapterContext:
    """Structured chapter content for prompt building."""

    book_id: str
    book_title: str
    language: str
    chapter_num: int
    chapter_title: str
    headings: list[str]
    body_snippets: list[str]
    code_examples: list[str]


def extract_chapter_context(book_id: str, chapter_num: int) -> ChapterContext:
    """Extract structured chapter content from the book cache."""
    book = _load_book(book_id)

    chapter = None
    for ch in book.chapters:
        if ch.chapter_num == chapter_num:
            chapter = ch
            break

    if not chapter:
        print(f"Error: Chapter {chapter_num} not found in {book_id}")
        print(f"Available chapters: {[ch.chapter_num for ch in book.chapters]}")
        sys.exit(1)

    headings = []
    body_snippets = []
    code_examples = []

    current_heading = ""
    body_chars = 0

    for block in chapter.content_blocks:
        bt = block.block_type.value

        if bt.startswith("heading"):
            level = int(bt[-1])
            indent = "  " * (level - 1)
            heading_text = block.text.strip()
            headings.append(f"{indent}- {heading_text}")
            current_heading = heading_text
            body_chars = 0

        elif bt == "body" and body_chars < 500:
            text = block.text.strip()
            if text and len(text) > 20:
                if body_chars == 0 and current_heading:
                    body_snippets.append(f"[{current_heading}]")
                body_snippets.append(text[:200])
                body_chars += len(text)

        elif bt in ("code", "code_repl"):
            preview = block.text.strip()[:300]
            if preview:
                code_examples.append(preview)

    return ChapterContext(
        book_id=book_id,
        book_title=book.title,
        language=book.language,
        chapter_num=chapter_num,
        chapter_title=chapter.title,
        headings=headings,
        body_snippets=body_snippets,
        code_examples=code_examples[:10],  # Limit to 10 code examples
    )


def _load_book(book_id: str) -> Book:
    """Load a book from cache or exit."""
    cache_path = CACHE_DIR / f"{book_id}.json"
    if not cache_path.exists():
        available = [p.stem for p in CACHE_DIR.glob("*.json")] if CACHE_DIR.exists() else []
        print(f"Error: Cache not found: {cache_path}")
        print(f"Available caches: {available}")
        print("Run: python scripts/parse_books.py first")
        sys.exit(1)
    data = json.loads(cache_path.read_text(encoding="utf-8"))
    return Book.from_dict(data)


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------


def build_prompt(
    ctx: ChapterContext,
    content_type: str,
    count: int,
    difficulty: str,
    project_title: str = "",
    project_desc: str = "",
    previous_steps: list[dict] | None = None,
) -> str:
    """Build the LLM prompt for content generation."""
    from content_prompts import (
        CHALLENGE_PROMPT,
        PROJECT_STEP_PROMPT,
        QUIZ_PROMPT,
        format_challenge_example,
        format_project_example,
        format_quiz_example,
    )

    prefix = _get_prefix(ctx.book_id)
    ch_padded = f"{ctx.chapter_num:02d}"

    common_vars = {
        "count": count,
        "chapter_num": ctx.chapter_num,
        "chapter_num_padded": ch_padded,
        "chapter_title": ctx.chapter_title,
        "book_title": ctx.book_title,
        "book_id": ctx.book_id,
        "language": ctx.language,
        "id_prefix": prefix,
        "headings": "\n".join(ctx.headings) or "(no headings extracted)",
        "body_snippets": "\n".join(ctx.body_snippets) or "(no body text extracted)",
        "code_examples": "\n---\n".join(ctx.code_examples) or "(no code examples extracted)",
    }

    if content_type == "quiz":
        common_vars["example_section"] = format_quiz_example()
        return QUIZ_PROMPT.format(**common_vars)

    elif content_type == "challenge":
        common_vars["difficulty"] = difficulty
        common_vars["example_section"] = format_challenge_example()
        return CHALLENGE_PROMPT.format(**common_vars)

    elif content_type == "project":
        # Build previous steps context
        prev_section = ""
        if previous_steps:
            summaries = []
            for s in previous_steps:
                summaries.append(
                    f"- Step {s.get('chapter_num', '?')}: {s.get('title', '?')} (id: {s.get('step_id', '?')})"
                )
            prev_section = "Previous project steps:\n" + "\n".join(summaries)
        else:
            prev_section = "This is the first step of the project."

        builds_on = ""
        if previous_steps:
            builds_on = previous_steps[-1].get("step_id", "")

        common_vars["project_title"] = project_title
        common_vars["project_description"] = project_desc
        common_vars["previous_steps_section"] = prev_section
        common_vars["builds_on"] = builds_on
        common_vars["step_number"] = len(previous_steps or []) + 1
        common_vars["example_section"] = format_project_example()
        return PROJECT_STEP_PROMPT.format(**common_vars)

    else:
        print(f"Error: Unknown content type: {content_type}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Claude API caller
# ---------------------------------------------------------------------------


def call_claude_api(prompt: str, model: str) -> str:
    """Send prompt to Claude API and return the JSON response."""
    try:
        import anthropic
    except ImportError:
        print("Error: anthropic package not installed.")
        print("Install with: pip install anthropic")
        print("Or: pip install pylearn-reader[content-gen]")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        print("Get your key at: https://console.anthropic.com/")
        sys.exit(1)

    from content_prompts import SYSTEM_PROMPT

    client = anthropic.Anthropic(api_key=api_key)

    max_tokens = 4096 if "quiz" in prompt[:200].lower() else 8192

    print("Calling Claude API...")
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text

    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*\n", "", text.strip())
    text = re.sub(r"\n```\s*$", "", text.strip())

    return text


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_content(data: dict, content_type: str) -> list[str]:
    """Validate generated JSON against the expected schema. Returns error list."""
    errors: list[str] = []

    try:
        if content_type == "quiz":
            quiz_set = QuizSet.from_dict(data)
            for q in quiz_set.questions:
                qid = q.question_id
                if q.question_type == "multiple_choice":
                    if len(q.choices) != 4:
                        errors.append(f"{qid}: MC must have exactly 4 choices, got {len(q.choices)}")
                    if not isinstance(q.correct, int):
                        errors.append(f"{qid}: MC 'correct' must be an int, got {type(q.correct).__name__}")
                    elif q.correct < 0 or q.correct > 3:
                        errors.append(f"{qid}: correct index {q.correct} out of range (0-3)")
                elif q.question_type == "fill_in_blank":
                    if not isinstance(q.correct, str) or not q.correct.strip():
                        errors.append(f"{qid}: fill_in_blank 'correct' must be a non-empty string")
                    if q.choices:
                        errors.append(f"{qid}: fill_in_blank should not have choices")
                else:
                    errors.append(f"{qid}: unknown type '{q.question_type}'")

                if not q.explanation:
                    errors.append(f"{qid}: missing explanation")
                if not q.concepts:
                    errors.append(f"{qid}: missing concepts")

            # Check for duplicate IDs
            ids = [q.question_id for q in quiz_set.questions]
            dupes = {x for x in ids if ids.count(x) > 1}
            if dupes:
                errors.append(f"Duplicate IDs: {dupes}")

        elif content_type == "challenge":
            challenge_set = ChallengeSet.from_dict(data)
            for c in challenge_set.challenges:
                cid = c.challenge_id
                if not c.test_code or "assert" not in c.test_code:
                    errors.append(f"{cid}: test_code must contain at least one assert")
                if not c.starter_code:
                    errors.append(f"{cid}: missing starter_code")
                if c.difficulty not in ("easy", "medium", "hard"):
                    errors.append(f"{cid}: difficulty must be easy/medium/hard, got '{c.difficulty}'")
                if not c.hints:
                    errors.append(f"{cid}: missing hints")

            ids = [c.challenge_id for c in challenge_set.challenges]
            dupes = {x for x in ids if ids.count(x) > 1}
            if dupes:
                errors.append(f"Duplicate IDs: {dupes}")

        elif content_type == "project":
            step = ProjectStep.from_dict(data)
            if not step.test_code or "assert" not in step.test_code:
                errors.append(f"{step.step_id}: test_code must contain at least one assert")
            if not step.starter_code:
                errors.append(f"{step.step_id}: missing starter_code")
            if not step.acceptance_criteria:
                errors.append(f"{step.step_id}: missing acceptance_criteria")

    except (ValueError, KeyError) as e:
        errors.append(f"Schema error: {e}")

    return errors


# ---------------------------------------------------------------------------
# Draft file management
# ---------------------------------------------------------------------------


def _draft_path(book_id: str, content_type: str, chapter_num: int) -> Path:
    """Get the draft file path."""
    type_dir = {"quiz": "quizzes", "challenge": "challenges", "project": "project"}[content_type]
    return DRAFTS_DIR / book_id / type_dir / f"ch{chapter_num:02d}.json"


def _content_path(book_id: str, content_type: str, chapter_num: int) -> Path:
    """Get the final content file path."""
    type_dir = {"quiz": "quizzes", "challenge": "challenges", "project": "project"}[content_type]
    return CONTENT_DIR / book_id / type_dir / f"ch{chapter_num:02d}.json"


def save_draft(data: dict, content_type: str) -> Path:
    """Save generated content to the drafts directory."""
    book_id = data.get("book_id", "unknown")
    chapter_num = data.get("chapter_num", 0)

    # For project steps, chapter_num is at top level
    if content_type == "project" and "chapter_num" not in data:
        chapter_num = 0

    path = _draft_path(book_id, content_type, chapter_num)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def accept_draft(draft_path_str: str, force: bool = False) -> None:
    """Validate and copy a draft file into content/."""
    draft_path = Path(draft_path_str)
    if not draft_path.exists():
        print(f"Error: Draft not found: {draft_path}")
        sys.exit(1)

    data = json.loads(draft_path.read_text(encoding="utf-8"))

    # Detect content type from directory structure
    parent_name = draft_path.parent.name
    type_map = {"quizzes": "quiz", "challenges": "challenge", "project": "project"}
    content_type = type_map.get(parent_name)
    if not content_type:
        print(f"Error: Cannot determine content type from path: {draft_path}")
        print("Expected parent directory: quizzes/, challenges/, or project/")
        sys.exit(1)

    # Validate
    errors = validate_content(data, content_type)
    if errors:
        print(f"Validation failed ({len(errors)} issues):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    # Determine target path
    book_id = data.get("book_id", "unknown")
    chapter_num = data.get("chapter_num", 0)
    target = _content_path(book_id, content_type, chapter_num)

    if target.exists() and not force:
        print(f"Error: {target} already exists. Use --force to overwrite.")
        sys.exit(1)

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(draft_path, target)
    print(f"Accepted: {target}")


def validate_file(path_str: str) -> None:
    """Validate a JSON file and print results."""
    path = Path(path_str)
    if not path.exists():
        print(f"Error: File not found: {path}")
        sys.exit(1)

    data = json.loads(path.read_text(encoding="utf-8"))

    parent_name = path.parent.name
    type_map = {"quizzes": "quiz", "challenges": "challenge", "project": "project"}
    content_type = type_map.get(parent_name)
    if not content_type:
        # Try to guess from content
        if "questions" in data:
            content_type = "quiz"
        elif "challenges" in data:
            content_type = "challenge"
        elif "step_id" in data:
            content_type = "project"
        else:
            print("Error: Cannot determine content type. Place file in quizzes/, challenges/, or project/")
            sys.exit(1)

    errors = validate_content(data, content_type)
    if errors:
        print(f"{len(errors)} issues found:")
        for e in errors:
            print(f"  - {e}")
    else:
        # Summary
        if content_type == "quiz":
            n = len(data.get("questions", []))
            print(f"Valid. {n} quiz questions for ch{data.get('chapter_num', '??'):02d}.")
        elif content_type == "challenge":
            n = len(data.get("challenges", []))
            print(f"Valid. {n} challenges for ch{data.get('chapter_num', '??'):02d}.")
        elif content_type == "project":
            print(f"Valid. Project step: {data.get('title', '??')}")


# ---------------------------------------------------------------------------
# Main generation flow
# ---------------------------------------------------------------------------


def generate(args: argparse.Namespace) -> None:
    """Main generation workflow."""
    ctx = extract_chapter_context(args.book, args.chapter)
    print(f"Extracted context for Ch {ctx.chapter_num}: {ctx.chapter_title}")
    print(
        f"  {len(ctx.headings)} headings, {len(ctx.body_snippets)} text snippets, {len(ctx.code_examples)} code examples"
    )

    # Load previous project steps if generating project content
    previous_steps: list[dict] | None = None
    if args.type == "project":
        if not args.project_title:
            print("Error: --project-title is required for project generation")
            sys.exit(1)
        previous_steps = _load_existing_project_steps(args.book)

    prompt = build_prompt(
        ctx=ctx,
        content_type=args.type,
        count=args.count,
        difficulty=args.difficulty,
        project_title=getattr(args, "project_title", "") or "",
        project_desc=getattr(args, "project_desc", "") or "",
        previous_steps=previous_steps,
    )

    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN — Prompt that would be sent:")
        print("=" * 60)
        print(prompt)
        print("=" * 60)
        print(f"Estimated prompt length: ~{len(prompt.split())} words")
        return

    # Call the API
    raw_response = call_claude_api(prompt, args.model)

    # Parse JSON
    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError as e:
        print(f"Error: API returned invalid JSON: {e}")
        print("Raw response (first 500 chars):")
        print(raw_response[:500])
        # Save raw response for debugging
        debug_path = DRAFTS_DIR / "last_error_response.txt"
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        debug_path.write_text(raw_response, encoding="utf-8")
        print(f"Full response saved to: {debug_path}")
        sys.exit(1)

    # Validate
    errors = validate_content(data, args.type)
    if errors:
        print(f"Warning: {len(errors)} validation issues (draft saved anyway):")
        for e in errors:
            print(f"  - {e}")

    # Save draft
    draft_path = save_draft(data, args.type)
    print(f"\nDraft saved: {draft_path}")
    print("Review the file, then accept with:")
    print(f"  python scripts/generate_content.py --accept {draft_path}")


def _load_existing_project_steps(book_id: str) -> list[dict]:
    """Load existing project steps from both content/ and drafts/."""
    steps: list[dict] = []
    for base_dir in [CONTENT_DIR, DRAFTS_DIR]:
        project_dir = base_dir / book_id / "project"
        if not project_dir.exists():
            continue
        for f in sorted(project_dir.glob("ch*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if "step_id" in data:
                    steps.append(data)
            except (json.JSONDecodeError, OSError):
                pass
    # Deduplicate by step_id, preferring content/ over drafts/
    seen: dict[str, dict] = {}
    for s in steps:
        seen[s["step_id"]] = s
    return sorted(seen.values(), key=lambda s: s.get("chapter_num", 0))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LLM-assisted content generation for PyLearn",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Requires: pip install anthropic (or: pip install pylearn-reader[content-gen])",
    )

    # Generation options
    parser.add_argument("--book", help="Book ID (e.g., learning_python_fifth_edition)")
    parser.add_argument("--chapter", type=int, help="Chapter number")
    parser.add_argument("--type", choices=["quiz", "challenge", "project"], help="Content type to generate")
    parser.add_argument("--count", type=int, default=6, help="Number of questions/challenges (default: 6)")
    parser.add_argument(
        "--difficulty", default="mixed", help="Challenge difficulty: easy, medium, hard, or mixed (default: mixed)"
    )
    parser.add_argument(
        "--model", default="claude-sonnet-4-20250514", help="Claude model (default: claude-sonnet-4-20250514)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Print prompt without calling API")

    # Project-specific
    parser.add_argument("--project-title", help="Project title (required for --type project)")
    parser.add_argument("--project-desc", default="", help="Project description")

    # Post-generation
    parser.add_argument("--validate", metavar="PATH", help="Validate a JSON file")
    parser.add_argument("--accept", metavar="PATH", help="Accept a draft into content/")
    parser.add_argument("--force", action="store_true", help="Overwrite existing content files")

    args = parser.parse_args()

    # Dispatch
    if args.validate:
        validate_file(args.validate)
    elif args.accept:
        accept_draft(args.accept, force=args.force)
    elif args.book and args.chapter and args.type:
        generate(args)
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python scripts/generate_content.py --book learning_python_fifth_edition --chapter 6 --type quiz")
        print("  python scripts/generate_content.py --book cpp_primer_fifth_edition --chapter 3 --type challenge")
        print("  python scripts/generate_content.py --validate drafts/book_id/quizzes/ch03.json")
        print("  python scripts/generate_content.py --accept drafts/book_id/quizzes/ch03.json")


if __name__ == "__main__":
    main()
