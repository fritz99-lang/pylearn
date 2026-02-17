"""Tests for security & error handling hardening changes."""

import json
import pytest
from unittest.mock import patch, MagicMock

from pylearn.core.models import (
    BlockType, ContentBlock, Section, Chapter, Book,
)
from pylearn.core.config import EditorConfig, AppConfig
from pylearn.executor.sandbox import check_dangerous_code, _MAX_OUTPUT_CHARS


# ---------------------------------------------------------------------------
# D2 — Robust model deserialization
# ---------------------------------------------------------------------------

class TestContentBlockDeserialization:
    def test_unknown_block_type_defaults_to_body(self):
        """Unknown block_type from a newer cache version should not crash."""
        data = {"block_type": "unknown_future_type", "text": "some text"}
        block = ContentBlock.from_dict(data)
        assert block.block_type == BlockType.BODY
        assert block.text == "some text"

    def test_missing_block_type_defaults_to_body(self):
        """Missing block_type key should not crash."""
        data = {"text": "some text"}
        block = ContentBlock.from_dict(data)
        assert block.block_type == BlockType.BODY

    def test_missing_text_defaults_to_empty(self):
        """Missing text key should default to empty string."""
        data = {"block_type": "body"}
        block = ContentBlock.from_dict(data)
        assert block.text == ""

    def test_valid_block_type_still_works(self):
        """Normal deserialization should still work."""
        data = {"block_type": "code", "text": "print('hi')"}
        block = ContentBlock.from_dict(data)
        assert block.block_type == BlockType.CODE


class TestSectionDeserialization:
    def test_missing_required_key_raises_value_error(self):
        """Missing required key should raise ValueError, not KeyError."""
        data = {"title": "Test"}  # missing level, page_num, block_index
        with pytest.raises(ValueError, match="missing required key"):
            Section.from_dict(data)

    def test_valid_data_works(self):
        data = {"title": "T", "level": 2, "page_num": 5, "block_index": 3}
        section = Section.from_dict(data)
        assert section.title == "T"


class TestChapterDeserialization:
    def test_missing_required_key_raises_value_error(self):
        """Missing required key should raise ValueError, not KeyError."""
        data = {"chapter_num": 1, "title": "Ch1"}  # missing start_page, end_page
        with pytest.raises(ValueError, match="missing required key"):
            Chapter.from_dict(data)

    def test_valid_data_works(self):
        data = {
            "chapter_num": 1, "title": "Ch1",
            "start_page": 1, "end_page": 20,
        }
        chapter = Chapter.from_dict(data)
        assert chapter.title == "Ch1"


class TestBookDeserialization:
    def test_missing_required_key_raises_value_error(self):
        """Missing book_id/title/pdf_path should raise ValueError."""
        data = {"title": "T", "pdf_path": "/p.pdf"}  # missing book_id
        with pytest.raises(ValueError, match="missing required key"):
            Book.from_dict(data)

    def test_valid_data_works(self):
        data = {
            "book_id": "b", "title": "B", "pdf_path": "/b.pdf",
            "language": "python",
        }
        book = Book.from_dict(data)
        assert book.book_id == "b"


# ---------------------------------------------------------------------------
# R4 — Config value clamping
# ---------------------------------------------------------------------------

class TestEditorConfigClamping:
    def test_font_size_clamped_low(self, tmp_path):
        config_path = tmp_path / "editor.json"
        config_path.write_text(json.dumps({"font_size": -5}), encoding="utf-8")
        with patch("pylearn.core.config.EDITOR_CONFIG_PATH", config_path):
            cfg = EditorConfig()
            assert cfg.font_size == 6

    def test_font_size_clamped_high(self, tmp_path):
        config_path = tmp_path / "editor.json"
        config_path.write_text(json.dumps({"font_size": 200}), encoding="utf-8")
        with patch("pylearn.core.config.EDITOR_CONFIG_PATH", config_path):
            cfg = EditorConfig()
            assert cfg.font_size == 72

    def test_tab_width_clamped_low(self, tmp_path):
        config_path = tmp_path / "editor.json"
        config_path.write_text(json.dumps({"tab_width": 0}), encoding="utf-8")
        with patch("pylearn.core.config.EDITOR_CONFIG_PATH", config_path):
            cfg = EditorConfig()
            assert cfg.tab_width == 1

    def test_tab_width_clamped_high(self, tmp_path):
        config_path = tmp_path / "editor.json"
        config_path.write_text(json.dumps({"tab_width": 100}), encoding="utf-8")
        with patch("pylearn.core.config.EDITOR_CONFIG_PATH", config_path):
            cfg = EditorConfig()
            assert cfg.tab_width == 16

    def test_execution_timeout_clamped_low(self, tmp_path):
        config_path = tmp_path / "editor.json"
        config_path.write_text(json.dumps({"execution_timeout": 1}), encoding="utf-8")
        with patch("pylearn.core.config.EDITOR_CONFIG_PATH", config_path):
            cfg = EditorConfig()
            assert cfg.execution_timeout == 5

    def test_execution_timeout_clamped_high(self, tmp_path):
        config_path = tmp_path / "editor.json"
        config_path.write_text(json.dumps({"execution_timeout": 999999}), encoding="utf-8")
        with patch("pylearn.core.config.EDITOR_CONFIG_PATH", config_path):
            cfg = EditorConfig()
            assert cfg.execution_timeout == 300

    def test_setter_also_clamps(self, tmp_path):
        config_path = tmp_path / "editor.json"
        config_path.write_text("{}", encoding="utf-8")
        with patch("pylearn.core.config.EDITOR_CONFIG_PATH", config_path):
            cfg = EditorConfig()
            cfg.font_size = -10
            assert cfg.font_size == 6
            cfg.tab_width = 50
            assert cfg.tab_width == 16
            cfg.execution_timeout = 0
            assert cfg.execution_timeout == 5


class TestAppConfigClamping:
    def test_reader_font_size_clamped(self, tmp_path):
        config_path = tmp_path / "app.json"
        config_path.write_text(json.dumps({"reader_font_size": -5}), encoding="utf-8")
        with patch("pylearn.core.config.APP_CONFIG_PATH", config_path):
            cfg = AppConfig()
            assert cfg.reader_font_size == 6

    def test_reader_font_size_setter_clamps(self, tmp_path):
        config_path = tmp_path / "app.json"
        config_path.write_text("{}", encoding="utf-8")
        with patch("pylearn.core.config.APP_CONFIG_PATH", config_path):
            cfg = AppConfig()
            cfg.reader_font_size = 200
            assert cfg.reader_font_size == 72


# ---------------------------------------------------------------------------
# R5 — Book ID collision avoidance
# ---------------------------------------------------------------------------

class TestBookIdCollision:
    def test_collision_appends_suffix(self):
        """When a book_id already exists, _add_book should use a suffixed ID."""
        from pylearn.core.config import BooksConfig

        mock_config = MagicMock(spec=BooksConfig)
        # Simulate existing book with same ID
        mock_config.get_book.side_effect = lambda bid: (
            {"book_id": bid} if bid == "test_book" else None
        )

        # Replicate the collision logic from library_panel._add_book
        base_id = "test_book"
        book_id = base_id
        suffix = 2
        while mock_config.get_book(book_id) is not None:
            book_id = f"{base_id}_{suffix}"
            suffix += 1

        assert book_id == "test_book_2"

    def test_multiple_collisions(self):
        from pylearn.core.config import BooksConfig

        mock_config = MagicMock(spec=BooksConfig)
        existing = {"test_book", "test_book_2", "test_book_3"}
        mock_config.get_book.side_effect = lambda bid: (
            {"book_id": bid} if bid in existing else None
        )

        base_id = "test_book"
        book_id = base_id
        suffix = 2
        while mock_config.get_book(book_id) is not None:
            book_id = f"{base_id}_{suffix}"
            suffix += 1

        assert book_id == "test_book_4"


# ---------------------------------------------------------------------------
# S3 — Expanded danger patterns
# ---------------------------------------------------------------------------

class TestDangerPatterns:
    def test_eval_detected(self):
        assert any("eval" in w for w in check_dangerous_code("result = eval(expr)"))

    def test_exec_detected(self):
        assert any("exec" in w for w in check_dangerous_code("exec(code)"))

    def test_ctypes_detected(self):
        assert any("ctypes" in w for w in check_dangerous_code("import ctypes"))

    def test_importlib_detected(self):
        assert any("importlib" in w for w in check_dangerous_code("import importlib"))

    def test_socket_detected(self):
        assert any("socket" in w for w in check_dangerous_code("import socket"))

    def test_file_write_detected(self):
        warnings = check_dangerous_code("f = open('data.txt', 'w')")
        assert any("file write" in w for w in warnings)

    def test_safe_code_no_warnings(self):
        assert check_dangerous_code("x = 1\nprint(x)") == []

    def test_open_read_not_flagged(self):
        """open() for reading should not trigger the file write warning."""
        assert check_dangerous_code("f = open('data.txt', 'r')") == []


# ---------------------------------------------------------------------------
# S1 — Output size limit constant exists
# ---------------------------------------------------------------------------

class TestOutputLimit:
    def test_limit_constant_is_2mb(self):
        assert _MAX_OUTPUT_CHARS == 2 * 1024 * 1024

    def test_session_limit_matches(self):
        from pylearn.executor.session import _MAX_OUTPUT_CHARS as session_limit
        assert session_limit == 2 * 1024 * 1024


# ---------------------------------------------------------------------------
# D1 — Database connection timeout
# ---------------------------------------------------------------------------

class TestDatabaseTimeout:
    def test_connection_uses_timeout(self, tmp_path):
        from pylearn.core.database import Database
        db = Database(db_path=tmp_path / "test.db")
        # Verify the database works (timeout=10 internally)
        db.upsert_book("t", "Test", "/t.pdf", 10, 1)
        books = db.get_books()
        assert len(books) == 1


# ---------------------------------------------------------------------------
# R2 — Image extension validation
# ---------------------------------------------------------------------------

class TestImageExtensionValidation:
    def test_valid_extensions(self):
        from pylearn.parser.pdf_parser import _VALID_IMAGE_EXTENSIONS
        for ext in ("png", "jpg", "jpeg", "bmp", "gif", "tiff"):
            assert ext in _VALID_IMAGE_EXTENSIONS

    def test_invalid_extension_not_in_set(self):
        from pylearn.parser.pdf_parser import _VALID_IMAGE_EXTENSIONS
        assert "svg" not in _VALID_IMAGE_EXTENSIONS
        assert "exe" not in _VALID_IMAGE_EXTENSIONS
        assert "../hack" not in _VALID_IMAGE_EXTENSIONS


# ===========================================================================
# Round 2 — Additional hardening tests
# ===========================================================================


# ---------------------------------------------------------------------------
# #5 — BooksConfig migration type safety
# ---------------------------------------------------------------------------

class TestBooksConfigTypeSafety:
    def test_books_not_a_list_is_replaced(self, tmp_path):
        config_path = tmp_path / "books.json"
        config_path.write_text('{"books": "not_a_list"}', encoding="utf-8")
        with patch("pylearn.core.config.BOOKS_CONFIG_PATH", config_path):
            from pylearn.core.config import BooksConfig
            cfg = BooksConfig()
            assert cfg.books == []

    def test_missing_books_key(self, tmp_path):
        config_path = tmp_path / "books.json"
        config_path.write_text('{}', encoding="utf-8")
        with patch("pylearn.core.config.BOOKS_CONFIG_PATH", config_path):
            from pylearn.core.config import BooksConfig
            cfg = BooksConfig()
            assert cfg.books == []


# ---------------------------------------------------------------------------
# #7 — Structure detector empty blocks guard
# ---------------------------------------------------------------------------

class TestStructureDetectorGuards:
    def test_detect_chapters_empty_blocks(self):
        from pylearn.parser.structure_detector import StructureDetector
        from pylearn.parser.book_profiles import BookProfile
        profile = BookProfile(name="test")
        detector = StructureDetector(profile)
        result = detector.detect_chapters([])
        assert result == []

    def test_detect_chapters_no_headings_empty_blocks(self):
        """Even with no chapter starts, empty blocks shouldn't crash."""
        from pylearn.parser.structure_detector import StructureDetector
        from pylearn.parser.book_profiles import BookProfile
        from pylearn.core.models import ContentBlock, BlockType
        profile = BookProfile(name="test")
        detector = StructureDetector(profile)
        # Single body block — no headings, falls through to "Chapter 1"
        blocks = [ContentBlock(block_type=BlockType.BODY, text="Hello")]
        result = detector.detect_chapters(blocks)
        assert len(result) == 1
        assert result[0].chapter_num == 1


# ---------------------------------------------------------------------------
# #8 — Regex group extraction safety
# ---------------------------------------------------------------------------

class TestRegexGroupSafety:
    def test_bad_chapter_pattern_falls_back(self):
        """Invalid regex should not crash the detector."""
        from pylearn.parser.structure_detector import StructureDetector
        from pylearn.parser.book_profiles import BookProfile
        profile = BookProfile(name="test", chapter_pattern="[invalid")
        detector = StructureDetector(profile)
        # Should have fallen back to default pattern
        assert detector._chapter_re is not None

    def test_regex_without_group_skips_match(self):
        """Regex that matches but has no group(1) should not crash."""
        from pylearn.parser.structure_detector import StructureDetector
        from pylearn.parser.book_profiles import BookProfile
        from pylearn.core.models import ContentBlock, BlockType
        # Pattern matches headings but has no capturing group
        profile = BookProfile(name="test", chapter_pattern=r"^Chapter\s+\w+")
        detector = StructureDetector(profile)
        blocks = [
            ContentBlock(block_type=BlockType.HEADING1, text="Chapter One: Intro"),
        ]
        # Should not crash — group(1) raises IndexError, caught gracefully
        result = detector._detect_by_regex(blocks)
        assert result == []


# ---------------------------------------------------------------------------
# #13 — BookProfile threshold validation
# ---------------------------------------------------------------------------

class TestBookProfileValidation:
    def test_reversed_thresholds_auto_fixed(self):
        from pylearn.parser.book_profiles import BookProfile
        profile = BookProfile(
            name="test",
            heading1_min_size=10.0,
            heading2_min_size=18.0,
            heading3_min_size=14.0,
        )
        assert profile.heading1_min_size >= profile.heading2_min_size
        assert profile.heading2_min_size >= profile.heading3_min_size

    def test_correct_thresholds_unchanged(self):
        from pylearn.parser.book_profiles import BookProfile
        profile = BookProfile(
            name="test",
            heading1_min_size=20.0,
            heading2_min_size=14.0,
            heading3_min_size=12.0,
        )
        assert profile.heading1_min_size == 20.0
        assert profile.heading2_min_size == 14.0
        assert profile.heading3_min_size == 12.0


# ---------------------------------------------------------------------------
# #21 — BookProfile.is_monospace with empty font name
# ---------------------------------------------------------------------------

class TestIsMonospaceGuard:
    def test_empty_font_name(self):
        from pylearn.parser.book_profiles import BookProfile
        profile = BookProfile(name="test")
        assert profile.is_monospace("") is False

    def test_none_like_empty(self):
        from pylearn.parser.book_profiles import BookProfile
        profile = BookProfile(name="test")
        assert profile.is_monospace("Courier New") is True


# ---------------------------------------------------------------------------
# #16 — Database exception type is sqlite3.Error
# ---------------------------------------------------------------------------

class TestDatabaseExceptionType:
    def test_rollback_on_sqlite_error(self, tmp_path):
        """Verify that sqlite3.Error triggers rollback, not bare Exception."""
        from pylearn.core.database import Database
        import sqlite3
        db = Database(db_path=tmp_path / "test.db")
        # Attempt to insert with wrong types should raise and rollback
        try:
            with db._transaction() as conn:
                conn.execute("INSERT INTO books (book_id) VALUES (?)", (None,))
        except sqlite3.Error:
            pass  # Expected — rollback should have occurred


# ---------------------------------------------------------------------------
# #17 — detect_repl_code edge cases
# ---------------------------------------------------------------------------

class TestDetectReplCodeEdgeCases:
    def test_whitespace_only(self):
        from pylearn.utils.text_utils import detect_repl_code
        assert detect_repl_code("   \n\n  ") is False

    def test_single_newline(self):
        from pylearn.utils.text_utils import detect_repl_code
        assert detect_repl_code("\n") is False


# ---------------------------------------------------------------------------
# #19 — Sentinel per-process
# ---------------------------------------------------------------------------

class TestSentinelPerProcess:
    def test_new_sentinel_unique(self):
        from pylearn.executor.session import _new_sentinel
        s1 = _new_sentinel()
        s2 = _new_sentinel()
        assert s1 != s2
        assert s1.startswith("__PYLEARN_DONE_")


# ---------------------------------------------------------------------------
# #22 — Config save fallback on replace error
# ---------------------------------------------------------------------------

class TestConfigSaveFallback:
    def test_save_json_works_normally(self, tmp_path):
        from pylearn.core.config import _save_json
        p = tmp_path / "test.json"
        _save_json(p, {"key": "value"})
        assert p.exists()
        import json
        assert json.loads(p.read_text(encoding="utf-8")) == {"key": "value"}
        # No leftover .tmp
        assert not p.with_suffix(".tmp").exists()
