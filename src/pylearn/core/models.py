# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Data models for PyLearn."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("pylearn.models")


class BlockType(Enum):
    """Types of content blocks extracted from PDFs."""
    HEADING1 = "heading1"
    HEADING2 = "heading2"
    HEADING3 = "heading3"
    BODY = "body"
    CODE = "code"
    CODE_REPL = "code_repl"
    NOTE = "note"
    WARNING = "warning"
    TIP = "tip"
    EXERCISE = "exercise"
    EXERCISE_ANSWER = "exercise_answer"
    TABLE = "table"
    LIST_ITEM = "list_item"
    FIGURE = "figure"
    FIGURE_CAPTION = "figure_caption"
    PAGE_HEADER = "page_header"
    PAGE_FOOTER = "page_footer"


class ReadStatus(Enum):
    """Chapter reading status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass
class FontSpan:
    """A span of text with font metadata from PDF extraction."""
    text: str
    font_name: str
    font_size: float
    is_bold: bool = False
    is_italic: bool = False
    is_monospace: bool = False
    color: int = 0
    page_num: int = 0
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0


@dataclass
class ContentBlock:
    """A classified block of content (heading, body text, code, etc.)."""
    block_type: BlockType
    text: str
    page_num: int = 0
    font_size: float = 0.0
    is_bold: bool = False
    is_monospace: bool = False
    block_id: str = ""
    language: str = "python"

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_type": self.block_type.value,
            "text": self.text,
            "page_num": self.page_num,
            "font_size": self.font_size,
            "is_bold": self.is_bold,
            "is_monospace": self.is_monospace,
            "block_id": self.block_id,
            "language": self.language,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContentBlock:
        try:
            block_type = BlockType(data["block_type"])
        except (ValueError, KeyError):
            logger.warning("Unknown block_type %r, defaulting to BODY", data.get("block_type"))
            block_type = BlockType.BODY
        return cls(
            block_type=block_type,
            text=data.get("text", ""),
            page_num=data.get("page_num", 0),
            font_size=data.get("font_size", 0.0),
            is_bold=data.get("is_bold", False),
            is_monospace=data.get("is_monospace", False),
            block_id=data.get("block_id", ""),
            language=data.get("language", "python"),
        )


@dataclass
class Section:
    """A section within a chapter."""
    title: str
    level: int  # 1=chapter, 2=section, 3=subsection
    page_num: int
    block_index: int  # index into chapter's content_blocks list
    children: list[Section] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "level": self.level,
            "page_num": self.page_num,
            "block_index": self.block_index,
            "children": [c.to_dict() for c in self.children],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Section:
        try:
            return cls(
                title=data["title"],
                level=data["level"],
                page_num=data["page_num"],
                block_index=data["block_index"],
                children=[Section.from_dict(c) for c in data.get("children", [])],
            )
        except KeyError as e:
            raise ValueError(f"Section missing required key: {e}") from e


@dataclass
class Chapter:
    """A chapter from a book."""
    chapter_num: int
    title: str
    start_page: int
    end_page: int
    content_blocks: list[ContentBlock] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_num": self.chapter_num,
            "title": self.title,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "content_blocks": [b.to_dict() for b in self.content_blocks],
            "sections": [s.to_dict() for s in self.sections],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Chapter:
        try:
            return cls(
                chapter_num=data["chapter_num"],
                title=data["title"],
                start_page=data["start_page"],
                end_page=data["end_page"],
                content_blocks=[ContentBlock.from_dict(b) for b in data.get("content_blocks", [])],
                sections=[Section.from_dict(s) for s in data.get("sections", [])],
            )
        except KeyError as e:
            raise ValueError(f"Chapter missing required key: {e}") from e


@dataclass
class Book:
    """A parsed book."""
    book_id: str
    title: str
    pdf_path: str
    profile_name: str = ""
    language: str = "python"
    total_pages: int = 0
    chapters: list[Chapter] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "book_id": self.book_id,
            "title": self.title,
            "pdf_path": self.pdf_path,
            "profile_name": self.profile_name,
            "language": self.language,
            "total_pages": self.total_pages,
            "chapters": [c.to_dict() for c in self.chapters],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Book:
        try:
            book_id = data["book_id"]
            title = data["title"]
            pdf_path = data["pdf_path"]
        except KeyError as e:
            raise ValueError(f"Book missing required key: {e}") from e

        language = data.get("language", "")
        if not language:
            # Migrate old caches: derive language from profile_name
            from pylearn.parser.book_profiles import get_profile
            profile_name = data.get("profile_name", "")
            language = get_profile(profile_name).language if profile_name else "python"
        return cls(
            book_id=book_id,
            title=title,
            pdf_path=pdf_path,
            profile_name=data.get("profile_name", ""),
            language=language,
            total_pages=data.get("total_pages", 0),
            chapters=[Chapter.from_dict(c) for c in data.get("chapters", [])],
        )


@dataclass
class Exercise:
    """An exercise or quiz question from a book."""
    exercise_id: str
    book_id: str
    chapter_num: int
    title: str
    description: str
    exercise_type: str  # "quiz", "exercise", "recipe"
    answer: Optional[str] = None
    page_num: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "exercise_id": self.exercise_id,
            "book_id": self.book_id,
            "chapter_num": self.chapter_num,
            "title": self.title,
            "description": self.description,
            "exercise_type": self.exercise_type,
            "answer": self.answer,
            "page_num": self.page_num,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Exercise:
        return cls(
            exercise_id=data["exercise_id"],
            book_id=data["book_id"],
            chapter_num=data["chapter_num"],
            title=data["title"],
            description=data["description"],
            exercise_type=data["exercise_type"],
            answer=data.get("answer"),
            page_num=data.get("page_num", 0),
        )


@dataclass
class Bookmark:
    """A user bookmark."""
    bookmark_id: int
    book_id: str
    chapter_num: int
    scroll_position: int
    label: str
    created_at: str = ""


@dataclass
class Note:
    """A user note."""
    note_id: int
    book_id: str
    chapter_num: int
    section_title: str
    content: str
    created_at: str = ""
    updated_at: str = ""
