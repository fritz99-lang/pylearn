"""Tests for the enhanced SearchDialog with block-level navigation.

Tests cover: SearchWorker result emission, _block_type_label helper,
SearchDialog construction, hierarchical grouping, scope filtering,
and navigation signals.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import Qt

from pylearn.core.models import BlockType, Book, Chapter, ContentBlock
from pylearn.ui.search_dialog import SearchDialog, SearchWorker, _block_type_label

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_book(book_id: str, chapters: list[Chapter] | None = None) -> Book:
    """Helper to create a minimal Book for testing."""
    if chapters is None:
        chapters = [
            Chapter(
                chapter_num=1,
                title="Getting Started",
                start_page=1,
                end_page=50,
                content_blocks=[
                    ContentBlock(
                        block_type=BlockType.HEADING1,
                        text="Getting Started",
                        block_id="h1_0",
                    ),
                    ContentBlock(
                        block_type=BlockType.BODY,
                        text="Python is a versatile programming language used worldwide.",
                        block_id="body_0",
                    ),
                    ContentBlock(
                        block_type=BlockType.CODE,
                        text="print('hello world')",
                        block_id="code_0",
                    ),
                ],
            ),
            Chapter(
                chapter_num=2,
                title="Variables",
                start_page=51,
                end_page=100,
                content_blocks=[
                    ContentBlock(
                        block_type=BlockType.HEADING1,
                        text="Variables and Types",
                        block_id="h1_1",
                    ),
                    ContentBlock(
                        block_type=BlockType.BODY,
                        text="Variables store data. Python is dynamically typed.",
                        block_id="body_1",
                    ),
                    ContentBlock(
                        block_type=BlockType.NOTE,
                        text="Note: Python variables don't need type declarations.",
                        block_id="note_0",
                    ),
                ],
            ),
        ]
    return Book(
        book_id=book_id,
        title=f"Book {book_id}",
        pdf_path=f"/tmp/{book_id}.pdf",
        chapters=chapters,
    )


@pytest.fixture
def two_books() -> list[Book]:
    """Two books for search tests."""
    return [_make_book("book1"), _make_book("book2")]


@pytest.fixture
def mock_cache(two_books):
    """A CacheManager mock that returns two_books on load()."""
    cache = MagicMock()
    book_map = {b.book_id: b for b in two_books}
    cache.load.side_effect = lambda bid: book_map.get(bid)
    return cache


# ===========================================================================
# _block_type_label tests
# ===========================================================================


class TestBlockTypeLabel:
    """Correct human-readable labels for each BlockType."""

    def test_heading_types(self):
        assert _block_type_label(BlockType.HEADING1) == "Heading"
        assert _block_type_label(BlockType.HEADING2) == "Heading"
        assert _block_type_label(BlockType.HEADING3) == "Heading"

    def test_body(self):
        assert _block_type_label(BlockType.BODY) == "Body"

    def test_code_types(self):
        assert _block_type_label(BlockType.CODE) == "Code"
        assert _block_type_label(BlockType.CODE_REPL) == "Code"

    def test_callout_types(self):
        assert _block_type_label(BlockType.NOTE) == "Note"
        assert _block_type_label(BlockType.WARNING) == "Warning"
        assert _block_type_label(BlockType.TIP) == "Tip"

    def test_exercise_types(self):
        assert _block_type_label(BlockType.EXERCISE) == "Exercise"
        assert _block_type_label(BlockType.EXERCISE_ANSWER) == "Exercise"

    def test_table(self):
        assert _block_type_label(BlockType.TABLE) == "Table"

    def test_list_item(self):
        assert _block_type_label(BlockType.LIST_ITEM) == "List"

    def test_figure_types(self):
        assert _block_type_label(BlockType.FIGURE) == "Figure"
        assert _block_type_label(BlockType.FIGURE_CAPTION) == "Figure"

    def test_page_header_footer(self):
        assert _block_type_label(BlockType.PAGE_HEADER) == "Header"
        assert _block_type_label(BlockType.PAGE_FOOTER) == "Footer"


# ===========================================================================
# SearchWorker tests
# ===========================================================================


class TestSearchWorkerResults:
    """SearchWorker emits results with block_id and block_type_label."""

    def test_emits_block_id_and_type(self, two_books):
        """Results include the block_id and a human-readable type label."""
        results: list[tuple] = []
        worker = SearchWorker("hello", [two_books[0]])
        worker.result_found.connect(lambda *args: results.append(args))
        worker.run()  # run synchronously (not .start())

        assert len(results) == 1
        book_id, chapter_num, _title, snippet, block_id, block_type = results[0]
        assert book_id == "book1"
        assert chapter_num == 1
        assert block_id == "code_0"
        assert block_type == "Code"
        assert "hello" in snippet

    def test_case_insensitive_match(self, two_books):
        """Search should be case-insensitive."""
        results: list[tuple] = []
        worker = SearchWorker("PYTHON", [two_books[0]])
        worker.result_found.connect(lambda *args: results.append(args))
        worker.run()

        # "Python" appears in body_0 (ch1), h1_1 (ch2), body_1 (ch2), note_0 (ch2)
        assert len(results) >= 3

    def test_snippet_context(self, two_books):
        """Snippet should contain text around the match."""
        results: list[tuple] = []
        worker = SearchWorker("versatile", [two_books[0]])
        worker.result_found.connect(lambda *args: results.append(args))
        worker.run()

        assert len(results) == 1
        snippet = results[0][3]
        assert "versatile" in snippet

    def test_result_cap_at_200(self):
        """Worker should stop after 200 results."""
        # Create a book with 210 matching blocks
        blocks = [
            ContentBlock(
                block_type=BlockType.BODY,
                text="match here",
                block_id=f"b_{i}",
            )
            for i in range(210)
        ]
        chapter = Chapter(
            chapter_num=1,
            title="Big Chapter",
            start_page=1,
            end_page=999,
            content_blocks=blocks,
        )
        book = _make_book("big", chapters=[chapter])

        finished_totals: list[int] = []
        worker = SearchWorker("match", [book])
        worker.finished.connect(lambda t: finished_totals.append(t))
        worker.run()

        assert finished_totals[0] == 200

    def test_finished_signal_emitted(self, two_books):
        """finished signal should emit total result count."""
        totals: list[int] = []
        worker = SearchWorker("hello", [two_books[0]])
        worker.finished.connect(lambda t: totals.append(t))
        worker.run()

        assert len(totals) == 1
        assert totals[0] == 1

    def test_no_results(self, two_books):
        """No results emitted for a non-matching query."""
        results: list[tuple] = []
        worker = SearchWorker("xyznonexistent", [two_books[0]])
        worker.result_found.connect(lambda *args: results.append(args))
        worker.run()

        assert len(results) == 0

    def test_stop_halts_search(self, two_books):
        """Calling stop() prevents further results."""
        results: list[tuple] = []
        worker = SearchWorker("python", two_books)

        def capture_and_stop(*args: object) -> None:
            results.append(args)
            worker.stop()

        worker.result_found.connect(capture_and_stop)
        worker.run()

        # Should have stopped after the first result
        assert len(results) == 1


# ===========================================================================
# SearchDialog construction tests
# ===========================================================================


class TestSearchDialogConstruction:
    """SearchDialog constructs correctly with various parameters."""

    def test_basic_construction(self, qtbot, mock_cache):
        dialog = SearchDialog(mock_cache, ["book1", "book2"])
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Search Books"

    def test_has_search_input(self, qtbot, mock_cache):
        dialog = SearchDialog(mock_cache, ["book1", "book2"])
        qtbot.addWidget(dialog)
        assert dialog._input is not None
        assert dialog._input.placeholderText() == "Search book content..."

    def test_has_results_tree(self, qtbot, mock_cache):
        dialog = SearchDialog(mock_cache, ["book1", "book2"])
        qtbot.addWidget(dialog)
        assert dialog._results is not None
        assert dialog._results.headerItem().text(0) == "Location"
        assert dialog._results.headerItem().text(1) == "Type"
        assert dialog._results.headerItem().text(2) == "Match"

    def test_scope_shows_current_book_when_set(self, qtbot, mock_cache):
        """When current_book_id is provided, scope combo has 'Current Book' option."""
        dialog = SearchDialog(
            mock_cache,
            ["book1", "book2"],
            current_book_id="book1",
        )
        qtbot.addWidget(dialog)
        assert dialog._scope.count() == 2
        assert dialog._scope.currentText() == "Current Book"

    def test_scope_all_books_only_when_no_current(self, qtbot, mock_cache):
        """When no current_book_id, scope only has 'All Books'."""
        dialog = SearchDialog(mock_cache, ["book1", "book2"])
        qtbot.addWidget(dialog)
        assert dialog._scope.count() == 1
        assert dialog._scope.currentText() == "All Books"


# ===========================================================================
# SearchDialog grouping tests
# ===========================================================================


class TestSearchDialogGrouping:
    """Results are grouped hierarchically by chapter."""

    def test_chapter_parent_items_created(self, qtbot, mock_cache):
        """Each chapter with results gets a bold parent item."""
        dialog = SearchDialog(
            mock_cache,
            ["book1"],
            current_book_id="book1",
        )
        qtbot.addWidget(dialog)

        # Simulate adding results from two chapters
        dialog._query = "python"
        dialog._add_result("book1", 1, "Getting Started", "...Python is...", "body_0", "Body")
        dialog._add_result("book1", 2, "Variables", "...Python is...", "body_1", "Body")

        # Two top-level chapter items
        assert dialog._results.topLevelItemCount() == 2

        # Chapter items are bold
        ch1 = dialog._results.topLevelItem(0)
        assert ch1.font(0).bold()

    def test_matches_nested_under_chapter(self, qtbot, mock_cache):
        """Individual matches are children of their chapter item."""
        dialog = SearchDialog(
            mock_cache,
            ["book1"],
            current_book_id="book1",
        )
        qtbot.addWidget(dialog)

        dialog._query = "test"
        dialog._add_result("book1", 1, "Getting Started", "test snippet", "code_0", "Code")
        dialog._add_result("book1", 1, "Getting Started", "another test", "body_0", "Body")

        # One chapter parent with two children
        assert dialog._results.topLevelItemCount() == 1
        parent = dialog._results.topLevelItem(0)
        assert parent.childCount() == 2

    def test_child_items_store_user_role_data(self, qtbot, mock_cache):
        """Child items store (book_id, chapter_num, block_id) in UserRole."""
        dialog = SearchDialog(
            mock_cache,
            ["book1"],
            current_book_id="book1",
        )
        qtbot.addWidget(dialog)

        dialog._query = "test"
        dialog._add_result("book1", 1, "Getting Started", "test snippet", "code_0", "Code")

        parent = dialog._results.topLevelItem(0)
        child = parent.child(0)
        data = child.data(0, Qt.ItemDataRole.UserRole)
        assert data == ("book1", 1, "code_0")

    def test_chapter_parent_has_no_user_role(self, qtbot, mock_cache):
        """Chapter parent items should not have UserRole data (not clickable)."""
        dialog = SearchDialog(
            mock_cache,
            ["book1"],
            current_book_id="book1",
        )
        qtbot.addWidget(dialog)

        dialog._query = "test"
        dialog._add_result("book1", 1, "Getting Started", "test snippet", "code_0", "Code")

        parent = dialog._results.topLevelItem(0)
        assert parent.data(0, Qt.ItemDataRole.UserRole) is None

    def test_block_type_shown_in_type_column(self, qtbot, mock_cache):
        """The type column shows the block type label."""
        dialog = SearchDialog(
            mock_cache,
            ["book1"],
            current_book_id="book1",
        )
        qtbot.addWidget(dialog)

        dialog._query = "test"
        dialog._add_result("book1", 1, "Getting Started", "test snippet", "code_0", "Code")

        parent = dialog._results.topLevelItem(0)
        child = parent.child(0)
        assert child.text(1) == "Code"


# ===========================================================================
# SearchDialog scope tests
# ===========================================================================


class TestSearchDialogScope:
    """Scope toggle filters books correctly."""

    def test_current_book_scope_filters(self, qtbot, mock_cache):
        """'Current Book' scope only returns the current book."""
        dialog = SearchDialog(
            mock_cache,
            ["book1", "book2"],
            current_book_id="book1",
        )
        qtbot.addWidget(dialog)

        dialog._scope.setCurrentText("Current Book")
        scoped = dialog._get_scoped_books()
        assert len(scoped) == 1
        assert scoped[0].book_id == "book1"

    def test_all_books_scope_returns_all(self, qtbot, mock_cache):
        """'All Books' scope returns all loaded books."""
        dialog = SearchDialog(
            mock_cache,
            ["book1", "book2"],
            current_book_id="book1",
        )
        qtbot.addWidget(dialog)

        dialog._scope.setCurrentText("All Books")
        scoped = dialog._get_scoped_books()
        assert len(scoped) == 2

    def test_all_books_default_when_no_current(self, qtbot, mock_cache):
        """Without current_book_id, scope defaults to all books."""
        dialog = SearchDialog(mock_cache, ["book1", "book2"])
        qtbot.addWidget(dialog)

        scoped = dialog._get_scoped_books()
        assert len(scoped) == 2


# ===========================================================================
# SearchDialog navigation tests
# ===========================================================================


class TestSearchDialogNavigation:
    """Double-click behavior and navigate_requested signal."""

    def test_double_click_child_emits_signal(self, qtbot, mock_cache):
        """Double-clicking a match item emits navigate_requested with block_id."""
        dialog = SearchDialog(
            mock_cache,
            ["book1"],
            current_book_id="book1",
        )
        qtbot.addWidget(dialog)

        signals: list[tuple] = []
        dialog.navigate_requested.connect(lambda *args: signals.append(args))

        dialog._query = "test"
        dialog._add_result("book1", 1, "Getting Started", "test snippet", "code_0", "Code")

        parent = dialog._results.topLevelItem(0)
        child = parent.child(0)
        dialog._on_result_clicked(child, 0)

        assert len(signals) == 1
        assert signals[0] == ("book1", 1, "code_0")

    def test_double_click_chapter_header_no_signal(self, qtbot, mock_cache):
        """Double-clicking a chapter header does not emit a signal."""
        dialog = SearchDialog(
            mock_cache,
            ["book1"],
            current_book_id="book1",
        )
        qtbot.addWidget(dialog)

        signals: list[tuple] = []
        dialog.navigate_requested.connect(lambda *args: signals.append(args))

        dialog._query = "test"
        dialog._add_result("book1", 1, "Getting Started", "test snippet", "code_0", "Code")

        parent = dialog._results.topLevelItem(0)
        dialog._on_result_clicked(parent, 0)

        assert len(signals) == 0

    def test_navigate_signal_has_three_args(self, qtbot, mock_cache):
        """navigate_requested emits (book_id, chapter_num, block_id)."""
        dialog = SearchDialog(
            mock_cache,
            ["book1"],
            current_book_id="book1",
        )
        qtbot.addWidget(dialog)

        signals: list[tuple] = []
        dialog.navigate_requested.connect(lambda *args: signals.append(args))

        dialog._query = "test"
        dialog._add_result("book1", 2, "Variables", "test data", "note_0", "Note")

        parent = dialog._results.topLevelItem(0)
        child = parent.child(0)
        dialog._on_result_clicked(child, 0)

        assert signals[0] == ("book1", 2, "note_0")


# ===========================================================================
# Highlight snippet tests
# ===========================================================================


class TestHighlightSnippet:
    """Match term is highlighted in the snippet HTML."""

    def test_match_is_bolded(self):
        result = SearchDialog._highlight_snippet("hello world", "world", "#3498db")
        assert "<b" in result
        assert "world" in result

    def test_accent_color_used(self):
        result = SearchDialog._highlight_snippet("hello world", "world", "#ff0000")
        assert "#ff0000" in result

    def test_no_match_returns_escaped(self):
        result = SearchDialog._highlight_snippet("hello world", "xyz", "#3498db")
        assert "<b" not in result
        assert "hello world" in result

    def test_html_entities_escaped(self):
        result = SearchDialog._highlight_snippet("a < b & c", "b", "#3498db")
        assert "&lt;" in result
        assert "&amp;" in result
