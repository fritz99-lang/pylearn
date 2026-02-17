"""Tests for UI dialog widgets: NotesDialog, BookmarkDialog, ProgressDialog, ExercisePanel.

These tests verify that PyQt6 dialog widgets construct correctly, load data from the
database into their widget trees, and that CRUD operations (save, delete, update)
work through the dialog methods. We use pytest-qt's qtbot fixture for widget lifecycle
management and avoid calling .exec() (which blocks the event loop).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QTreeWidgetItem

from pylearn.core.database import Database
from pylearn.ui.bookmark_dialog import BookmarkDialog, add_bookmark_dialog
from pylearn.ui.exercise_panel import ExercisePanel
from pylearn.ui.notes_dialog import NotesDialog
from pylearn.ui.progress_dialog import ProgressDialog


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db(tmp_path):
    """Create a fresh database for each test."""
    return Database(db_path=tmp_path / "test.db")


@pytest.fixture
def seeded_db(db):
    """Database pre-populated with books, chapters, notes, bookmarks, and exercises."""
    db.upsert_book("b1", "Learning Python", "/books/lp.pdf", 500, 3)
    db.upsert_chapter("b1", 1, "Getting Started", 1, 50)
    db.upsert_chapter("b1", 2, "Variables", 51, 100)
    db.upsert_chapter("b1", 3, "Functions", 101, 150)

    db.upsert_book("b2", "Fluent Python", "/books/fp.pdf", 800, 2)
    db.upsert_chapter("b2", 1, "Data Model", 1, 40)
    db.upsert_chapter("b2", 2, "Sequences", 41, 80)

    # Notes
    db.add_note("b1", 1, "Installation", "Install Python 3.12 from python.org")
    db.add_note("b1", 1, "Setup", "Create a virtual environment with venv")
    db.add_note("b1", 2, "Naming", "Use snake_case for variable names")

    # Bookmarks
    db.add_bookmark("b1", 1, 100, "Start of chapter 1")
    db.add_bookmark("b1", 2, 300, "Variable assignment section")
    db.add_bookmark("b2", 1, 0, "Data model intro")

    # Reading progress
    db.update_reading_progress("b1", 1, "completed")
    db.update_reading_progress("b1", 2, "in_progress")

    # Exercises
    db.upsert_exercise("ex1", "b1", 1, "Hello World", "Write a hello world program", "exercise")
    db.upsert_exercise("ex2", "b1", 1, "Name Input", "Ask user for their name", "exercise")
    db.upsert_exercise("ex3", "b1", 2, "Swap Variables", "Swap two variables", "exercise")
    db.update_exercise_progress("ex1", True, "print('hello world')")

    return db


# ===========================================================================
# NotesDialog Tests
# ===========================================================================


class TestNotesDialogConstruction:
    """Test that NotesDialog constructs without error in various configurations."""

    def test_construct_with_empty_db(self, qtbot, db):
        """Dialog should construct even when no notes exist."""
        dialog = NotesDialog(db)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Notes"
        assert dialog._tree.topLevelItemCount() == 0

    def test_construct_with_book_filter(self, qtbot, seeded_db):
        """Dialog filtered to a single book should only show that book's notes."""
        dialog = NotesDialog(seeded_db, book_id="b1")
        qtbot.addWidget(dialog)
        # b1 has 3 notes total (ch1: 2, ch2: 1)
        assert dialog._tree.topLevelItemCount() == 3

    def test_construct_with_book_and_chapter_filter(self, qtbot, seeded_db):
        """Dialog filtered to book + chapter should show only that chapter's notes."""
        dialog = NotesDialog(seeded_db, book_id="b1", chapter_num=1)
        qtbot.addWidget(dialog)
        assert dialog._tree.topLevelItemCount() == 2

    def test_construct_with_section_title(self, qtbot, seeded_db):
        """Section title is stored for use when creating new notes."""
        dialog = NotesDialog(seeded_db, book_id="b1", chapter_num=1,
                             section_title="My Section")
        qtbot.addWidget(dialog)
        assert dialog._section_title == "My Section"

    def test_minimum_size(self, qtbot, db):
        """Dialog has reasonable minimum dimensions."""
        dialog = NotesDialog(db)
        qtbot.addWidget(dialog)
        assert dialog.minimumWidth() == 700
        assert dialog.minimumHeight() == 500


class TestNotesDialogDataLoading:
    """Test that notes data loads correctly into the tree widget."""

    def test_note_tree_shows_section_titles(self, qtbot, seeded_db):
        """Tree items should display section titles in column 0."""
        dialog = NotesDialog(seeded_db, book_id="b1", chapter_num=1)
        qtbot.addWidget(dialog)

        sections = set()
        for i in range(dialog._tree.topLevelItemCount()):
            item = dialog._tree.topLevelItem(i)
            sections.add(item.text(0))
        assert "Installation" in sections
        assert "Setup" in sections

    def test_note_tree_shows_content_preview(self, qtbot, seeded_db):
        """Tree items should show a content preview in column 1."""
        dialog = NotesDialog(seeded_db, book_id="b1", chapter_num=1)
        qtbot.addWidget(dialog)

        previews = []
        for i in range(dialog._tree.topLevelItemCount()):
            item = dialog._tree.topLevelItem(i)
            previews.append(item.text(1))
        # At least one preview should contain text from the note content
        assert any("Install" in p or "Create" in p or "virtual" in p for p in previews)

    def test_note_tree_items_carry_note_data(self, qtbot, seeded_db):
        """Each tree item should carry the full note dict in UserRole data."""
        dialog = NotesDialog(seeded_db, book_id="b1", chapter_num=1)
        qtbot.addWidget(dialog)

        item = dialog._tree.topLevelItem(0)
        note_data = item.data(0, Qt.ItemDataRole.UserRole)
        assert isinstance(note_data, dict)
        assert "note_id" in note_data
        assert "content" in note_data
        assert "section_title" in note_data

    def test_preview_truncated_to_50_chars(self, qtbot, db):
        """Long note content should be truncated to 50 chars in preview."""
        db.upsert_book("b1", "Book", "/b.pdf", 100, 1)
        long_content = "A" * 100
        db.add_note("b1", 1, "Long", long_content)

        dialog = NotesDialog(db, book_id="b1", chapter_num=1)
        qtbot.addWidget(dialog)

        item = dialog._tree.topLevelItem(0)
        preview = item.text(1)
        assert len(preview) == 50

    def test_preview_replaces_newlines(self, qtbot, db):
        """Newlines in note content should be replaced with spaces in preview."""
        db.upsert_book("b1", "Book", "/b.pdf", 100, 1)
        db.add_note("b1", 1, "Multi", "Line one\nLine two\nLine three")

        dialog = NotesDialog(db, book_id="b1", chapter_num=1)
        qtbot.addWidget(dialog)

        item = dialog._tree.topLevelItem(0)
        preview = item.text(1)
        assert "\n" not in preview
        assert "Line one Line two" in preview


class TestNotesDialogNoteSelection:
    """Test clicking a note in the tree loads it into the editor."""

    def test_selecting_note_loads_editor(self, qtbot, seeded_db):
        """Clicking a note should populate the editor and set current_note_id."""
        dialog = NotesDialog(seeded_db, book_id="b1", chapter_num=1)
        qtbot.addWidget(dialog)

        item = dialog._tree.topLevelItem(0)
        note_data = item.data(0, Qt.ItemDataRole.UserRole)

        # Simulate the click handler directly
        dialog._on_note_selected(item, 0)

        assert dialog._current_note_id == note_data["note_id"]
        assert dialog._editor.toPlainText() == note_data["content"]


class TestNotesDialogSave:
    """Test saving notes through the dialog."""

    def test_save_new_note(self, qtbot, seeded_db):
        """Saving with no current note creates a new note in the database."""
        dialog = NotesDialog(seeded_db, book_id="b1", chapter_num=1,
                             section_title="New Section")
        qtbot.addWidget(dialog)

        # Clear current note and type new content
        dialog._new_note()
        dialog._editor.setText("Brand new note content")
        dialog._save_note()

        # Verify in database
        notes = seeded_db.get_notes("b1", 1)
        contents = [n["content"] for n in notes]
        assert "Brand new note content" in contents

    def test_save_updates_existing_note(self, qtbot, seeded_db):
        """Saving with a current note updates the existing note."""
        dialog = NotesDialog(seeded_db, book_id="b1", chapter_num=1)
        qtbot.addWidget(dialog)

        # Select the first note
        item = dialog._tree.topLevelItem(0)
        dialog._on_note_selected(item, 0)
        note_id = dialog._current_note_id

        # Modify and save
        dialog._editor.setText("Updated content here")
        dialog._save_note()

        # Verify in database
        notes = seeded_db.get_notes("b1", 1)
        updated = [n for n in notes if n["note_id"] == note_id]
        assert len(updated) == 1
        assert updated[0]["content"] == "Updated content here"

    def test_save_empty_content_is_ignored(self, qtbot, seeded_db):
        """Saving with empty content should not create or update anything."""
        initial_notes = seeded_db.get_notes("b1", 1)
        initial_count = len(initial_notes)

        dialog = NotesDialog(seeded_db, book_id="b1", chapter_num=1)
        qtbot.addWidget(dialog)

        dialog._new_note()
        dialog._editor.setText("   ")  # Whitespace only
        dialog._save_note()

        assert len(seeded_db.get_notes("b1", 1)) == initial_count

    def test_save_refreshes_tree(self, qtbot, seeded_db):
        """After saving, the tree should reload and reflect the new data."""
        dialog = NotesDialog(seeded_db, book_id="b1", chapter_num=1)
        qtbot.addWidget(dialog)
        initial_count = dialog._tree.topLevelItemCount()

        dialog._new_note()
        dialog._editor.setText("Another note for testing")
        dialog._save_note()

        assert dialog._tree.topLevelItemCount() == initial_count + 1

    def test_save_without_book_id_does_nothing(self, qtbot, db):
        """When book_id is None, saving a new note should not crash."""
        dialog = NotesDialog(db, book_id=None)
        qtbot.addWidget(dialog)

        dialog._new_note()
        dialog._editor.setText("Orphan note")
        dialog._save_note()

        # No crash; current_note_id still None because no book to save to
        assert dialog._current_note_id is None


class TestNotesDialogNewNote:
    """Test the 'New Note' button behavior."""

    def test_new_note_clears_editor(self, qtbot, seeded_db):
        """New Note should clear the editor and reset current_note_id."""
        dialog = NotesDialog(seeded_db, book_id="b1", chapter_num=1)
        qtbot.addWidget(dialog)

        # First select a note
        item = dialog._tree.topLevelItem(0)
        dialog._on_note_selected(item, 0)
        assert dialog._current_note_id is not None

        # Now create a new note
        dialog._new_note()
        assert dialog._current_note_id is None
        assert dialog._editor.toPlainText() == ""


class TestNotesDialogDelete:
    """Test deleting notes through the dialog."""

    def test_delete_with_no_selection_does_nothing(self, qtbot, seeded_db):
        """Calling delete with no current note should not crash."""
        dialog = NotesDialog(seeded_db, book_id="b1", chapter_num=1)
        qtbot.addWidget(dialog)

        dialog._current_note_id = None
        dialog._delete_note()  # Should return immediately without error

    @patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes)
    def test_delete_confirmed_removes_note(self, mock_question, qtbot, seeded_db):
        """Confirming delete should remove the note from the database."""
        dialog = NotesDialog(seeded_db, book_id="b1", chapter_num=1)
        qtbot.addWidget(dialog)
        initial_count = dialog._tree.topLevelItemCount()

        # Select first note
        item = dialog._tree.topLevelItem(0)
        dialog._on_note_selected(item, 0)
        deleted_id = dialog._current_note_id

        # Delete it
        dialog._delete_note()

        # Verify removal
        assert dialog._current_note_id is None
        assert dialog._editor.toPlainText() == ""
        assert dialog._tree.topLevelItemCount() == initial_count - 1

        # Verify in database
        notes = seeded_db.get_notes("b1", 1)
        assert all(n["note_id"] != deleted_id for n in notes)

    @patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No)
    def test_delete_cancelled_keeps_note(self, mock_question, qtbot, seeded_db):
        """Cancelling delete should keep the note in the database."""
        dialog = NotesDialog(seeded_db, book_id="b1", chapter_num=1)
        qtbot.addWidget(dialog)
        initial_count = dialog._tree.topLevelItemCount()

        item = dialog._tree.topLevelItem(0)
        dialog._on_note_selected(item, 0)

        dialog._delete_note()

        # Nothing changed
        assert dialog._tree.topLevelItemCount() == initial_count


# ===========================================================================
# BookmarkDialog Tests
# ===========================================================================


class TestBookmarkDialogConstruction:
    """Test that BookmarkDialog constructs without error."""

    def test_construct_with_empty_db(self, qtbot, db):
        """Dialog should construct even when no bookmarks exist."""
        dialog = BookmarkDialog(db)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Bookmarks"
        assert dialog._tree.topLevelItemCount() == 0

    def test_construct_with_book_filter(self, qtbot, seeded_db):
        """Dialog filtered to a book shows only that book's bookmarks."""
        dialog = BookmarkDialog(seeded_db, book_id="b1")
        qtbot.addWidget(dialog)
        # b1 has 2 bookmarks
        assert dialog._tree.topLevelItemCount() == 2

    def test_construct_shows_all_bookmarks(self, qtbot, seeded_db):
        """Dialog with no book filter shows all bookmarks across all books."""
        dialog = BookmarkDialog(seeded_db, book_id=None)
        qtbot.addWidget(dialog)
        # b1: 2, b2: 1 = 3 total
        assert dialog._tree.topLevelItemCount() == 3

    def test_minimum_size(self, qtbot, db):
        """Dialog has reasonable minimum dimensions."""
        dialog = BookmarkDialog(db)
        qtbot.addWidget(dialog)
        assert dialog.minimumWidth() == 500
        assert dialog.minimumHeight() == 400


class TestBookmarkDialogDataLoading:
    """Test that bookmark data loads correctly into the tree."""

    def test_tree_columns_populated(self, qtbot, seeded_db):
        """Each tree item should have label, book_id, and chapter text."""
        dialog = BookmarkDialog(seeded_db, book_id="b1")
        qtbot.addWidget(dialog)

        item = dialog._tree.topLevelItem(0)
        # Column 0 is label, column 1 is book_id, column 2 is chapter
        assert item.text(0) != ""  # label
        assert item.text(1) == "b1"  # book_id
        assert "Chapter" in item.text(2)  # formatted chapter string

    def test_tree_items_carry_bookmark_data(self, qtbot, seeded_db):
        """Each tree item should carry the full bookmark dict in UserRole data."""
        dialog = BookmarkDialog(seeded_db, book_id="b1")
        qtbot.addWidget(dialog)

        item = dialog._tree.topLevelItem(0)
        bm_data = item.data(0, Qt.ItemDataRole.UserRole)
        assert isinstance(bm_data, dict)
        assert "bookmark_id" in bm_data
        assert "book_id" in bm_data
        assert "chapter_num" in bm_data
        assert "scroll_position" in bm_data
        assert "label" in bm_data

    def test_bookmark_labels_match_database(self, qtbot, seeded_db):
        """The labels displayed in the tree should match what is in the database."""
        dialog = BookmarkDialog(seeded_db, book_id="b1")
        qtbot.addWidget(dialog)

        displayed_labels = set()
        for i in range(dialog._tree.topLevelItemCount()):
            item = dialog._tree.topLevelItem(i)
            displayed_labels.add(item.text(0))

        db_labels = {bm["label"] for bm in seeded_db.get_bookmarks("b1")}
        assert displayed_labels == db_labels


class TestBookmarkDialogNavigation:
    """Test the 'Go To' bookmark navigation."""

    def test_go_to_with_no_selection(self, qtbot, seeded_db):
        """Go To with no item selected should not crash or emit signal."""
        dialog = BookmarkDialog(seeded_db, book_id="b1")
        qtbot.addWidget(dialog)

        # Ensure nothing is selected
        dialog._tree.setCurrentItem(None)

        signals = []
        dialog.bookmark_selected.connect(lambda *args: signals.append(args))

        dialog._go_to_bookmark()
        assert len(signals) == 0

    def test_go_to_emits_signal(self, qtbot, seeded_db):
        """Selecting a bookmark and clicking Go To should emit bookmark_selected."""
        dialog = BookmarkDialog(seeded_db, book_id="b1")
        qtbot.addWidget(dialog)

        # Select first item
        item = dialog._tree.topLevelItem(0)
        dialog._tree.setCurrentItem(item)
        bm_data = item.data(0, Qt.ItemDataRole.UserRole)

        signals = []
        dialog.bookmark_selected.connect(lambda *args: signals.append(args))

        dialog._go_to_bookmark()
        assert len(signals) == 1
        book_id, chapter_num, scroll_pos = signals[0]
        assert book_id == bm_data["book_id"]
        assert chapter_num == bm_data["chapter_num"]
        assert scroll_pos == bm_data["scroll_position"]

    def test_double_click_triggers_go_to(self, qtbot, seeded_db):
        """Double-clicking an item should call _go_to_bookmark."""
        dialog = BookmarkDialog(seeded_db, book_id="b1")
        qtbot.addWidget(dialog)

        item = dialog._tree.topLevelItem(0)
        dialog._tree.setCurrentItem(item)

        signals = []
        dialog.bookmark_selected.connect(lambda *args: signals.append(args))

        # Simulate the double-click handler directly
        dialog._on_double_click(item, 0)
        assert len(signals) == 1


class TestBookmarkDialogDelete:
    """Test deleting bookmarks through the dialog."""

    def test_delete_with_no_selection(self, qtbot, seeded_db):
        """Delete with no selection should not crash."""
        dialog = BookmarkDialog(seeded_db, book_id="b1")
        qtbot.addWidget(dialog)
        dialog._tree.setCurrentItem(None)
        dialog._delete_bookmark()  # Should not raise

    @patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes)
    def test_delete_confirmed_removes_bookmark(self, mock_question, qtbot, seeded_db):
        """Confirming delete should remove the bookmark from the database."""
        dialog = BookmarkDialog(seeded_db, book_id="b1")
        qtbot.addWidget(dialog)

        item = dialog._tree.topLevelItem(0)
        dialog._tree.setCurrentItem(item)
        bm_data = item.data(0, Qt.ItemDataRole.UserRole)
        deleted_id = bm_data["bookmark_id"]

        dialog._delete_bookmark()

        # Verify removal from database
        remaining = seeded_db.get_bookmarks("b1")
        assert all(bm["bookmark_id"] != deleted_id for bm in remaining)

        # Verify tree reloaded
        assert dialog._tree.topLevelItemCount() == 1

    @patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No)
    def test_delete_cancelled_keeps_bookmark(self, mock_question, qtbot, seeded_db):
        """Cancelling delete should keep the bookmark."""
        dialog = BookmarkDialog(seeded_db, book_id="b1")
        qtbot.addWidget(dialog)

        item = dialog._tree.topLevelItem(0)
        dialog._tree.setCurrentItem(item)

        dialog._delete_bookmark()
        assert dialog._tree.topLevelItemCount() == 2


class TestBookmarkDialogSignal:
    """Test the bookmark_selected signal type signature."""

    def test_signal_exists(self, qtbot, db):
        """BookmarkDialog should have a bookmark_selected signal."""
        dialog = BookmarkDialog(db)
        qtbot.addWidget(dialog)
        assert hasattr(dialog, "bookmark_selected")


class TestAddBookmarkDialog:
    """Test the add_bookmark_dialog standalone function."""

    @patch("pylearn.ui.bookmark_dialog.QInputDialog.getText",
           return_value=("My Bookmark", True))
    def test_add_bookmark_success(self, mock_input, qtbot, seeded_db):
        """When user enters a label and clicks OK, bookmark should be added."""
        result = add_bookmark_dialog(None, seeded_db, "b1", 2, 500)
        assert result is True

        bookmarks = seeded_db.get_bookmarks("b1")
        labels = [bm["label"] for bm in bookmarks]
        assert "My Bookmark" in labels

    @patch("pylearn.ui.bookmark_dialog.QInputDialog.getText",
           return_value=("", False))
    def test_add_bookmark_cancelled(self, mock_input, qtbot, seeded_db):
        """When user cancels the input dialog, no bookmark should be added."""
        initial_count = len(seeded_db.get_bookmarks("b1"))

        result = add_bookmark_dialog(None, seeded_db, "b1", 2, 500)
        assert result is False
        assert len(seeded_db.get_bookmarks("b1")) == initial_count

    @patch("pylearn.ui.bookmark_dialog.QInputDialog.getText",
           return_value=("", True))
    def test_add_bookmark_empty_label_ignored(self, mock_input, qtbot, seeded_db):
        """Pressing OK with empty label should not add a bookmark."""
        initial_count = len(seeded_db.get_bookmarks("b1"))

        result = add_bookmark_dialog(None, seeded_db, "b1", 2, 500)
        assert result is False
        assert len(seeded_db.get_bookmarks("b1")) == initial_count


# ===========================================================================
# ProgressDialog Tests
# ===========================================================================


class TestProgressDialogConstruction:
    """Test that ProgressDialog constructs without error."""

    def test_construct_with_empty_db(self, qtbot, db):
        """Dialog should construct even with no books registered."""
        dialog = ProgressDialog(db)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Reading Progress"

    def test_construct_with_seeded_db(self, qtbot, seeded_db):
        """Dialog should construct and display progress for registered books."""
        dialog = ProgressDialog(seeded_db)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Reading Progress"

    def test_minimum_size(self, qtbot, db):
        """Dialog has reasonable minimum dimensions."""
        dialog = ProgressDialog(db)
        qtbot.addWidget(dialog)
        assert dialog.minimumWidth() == 500
        assert dialog.minimumHeight() == 400


class TestProgressDialogContent:
    """Test that progress data renders correctly in the dialog."""

    def test_empty_db_shows_placeholder(self, qtbot, db):
        """When no books exist, a placeholder message should be visible."""
        dialog = ProgressDialog(db)
        qtbot.addWidget(dialog)

        # The dialog adds a QLabel with a message about no books
        layout = dialog.layout()
        found_placeholder = False
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget and hasattr(widget, "text"):
                if "No books registered" in widget.text():
                    found_placeholder = True
                    break
        assert found_placeholder

    def test_books_create_group_boxes(self, qtbot, seeded_db):
        """Each registered book should produce a QGroupBox in the layout."""
        dialog = ProgressDialog(seeded_db)
        qtbot.addWidget(dialog)

        from PyQt6.QtWidgets import QGroupBox
        group_boxes = dialog.findChildren(QGroupBox)
        # seeded_db has 2 books
        assert len(group_boxes) == 2

    def test_group_box_titles_match_books(self, qtbot, seeded_db):
        """Group box titles should match the book titles from the database."""
        dialog = ProgressDialog(seeded_db)
        qtbot.addWidget(dialog)

        from PyQt6.QtWidgets import QGroupBox
        group_boxes = dialog.findChildren(QGroupBox)
        titles = {gb.title() for gb in group_boxes}
        assert "Learning Python" in titles
        assert "Fluent Python" in titles

    def test_progress_bars_exist(self, qtbot, seeded_db):
        """Each book group should contain a progress bar."""
        dialog = ProgressDialog(seeded_db)
        qtbot.addWidget(dialog)

        from PyQt6.QtWidgets import QProgressBar
        progress_bars = dialog.findChildren(QProgressBar)
        assert len(progress_bars) == 2

    def test_progress_bar_value_reflects_completion(self, qtbot, seeded_db):
        """Progress bar values should match the completion stats from the database."""
        dialog = ProgressDialog(seeded_db)
        qtbot.addWidget(dialog)

        from PyQt6.QtWidgets import QProgressBar
        progress_bars = dialog.findChildren(QProgressBar)
        values = {pb.value() for pb in progress_bars}

        # b1: 1 of 3 completed = 33%, b2: 0 of 2 completed = 0%
        assert 33 in values
        assert 0 in values

    def test_completion_labels_present(self, qtbot, seeded_db):
        """Labels showing completed/total chapter counts should exist."""
        dialog = ProgressDialog(seeded_db)
        qtbot.addWidget(dialog)

        from PyQt6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        label_texts = [lbl.text() for lbl in labels]

        # b1 has 1 completed out of 3
        assert any("1 / 3" in t for t in label_texts)
        # b2 has 0 completed out of 2
        assert any("0 / 2" in t for t in label_texts)

    def test_in_progress_label_present(self, qtbot, seeded_db):
        """In Progress count should be shown."""
        dialog = ProgressDialog(seeded_db)
        qtbot.addWidget(dialog)

        from PyQt6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        label_texts = [lbl.text() for lbl in labels]

        # b1 has 1 in_progress chapter
        assert any("In Progress: 1" in t for t in label_texts)

    def test_exercise_stats_shown(self, qtbot, seeded_db):
        """Exercise completion stats should be displayed for books with exercises."""
        dialog = ProgressDialog(seeded_db)
        qtbot.addWidget(dialog)

        from PyQt6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        label_texts = [lbl.text() for lbl in labels]

        # b1 has 3 exercises, 1 completed
        assert any("1 / 3" in t and "Exercises" in t for t in label_texts)

    def test_no_exercise_stats_when_none_exist(self, qtbot, db):
        """Books with no exercises should not show exercise labels."""
        db.upsert_book("b1", "Book", "/b.pdf", 100, 1)
        db.upsert_chapter("b1", 1, "Ch1", 1, 100)

        dialog = ProgressDialog(db)
        qtbot.addWidget(dialog)

        from PyQt6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        label_texts = [lbl.text() for lbl in labels]
        assert not any("Exercises" in t for t in label_texts)


# ===========================================================================
# ExercisePanel Tests
# ===========================================================================


class TestExercisePanelConstruction:
    """Test that ExercisePanel constructs without error."""

    def test_construct(self, qtbot, db):
        """Panel should construct without error."""
        panel = ExercisePanel(db)
        qtbot.addWidget(panel)
        assert panel._tree.topLevelItemCount() == 0
        assert panel._current_exercise_id is None

    def test_buttons_initially_disabled(self, qtbot, db):
        """Mark Complete and Try in Editor buttons should start disabled."""
        panel = ExercisePanel(db)
        qtbot.addWidget(panel)
        assert panel._mark_done_btn.isEnabled() is False
        assert panel._try_btn.isEnabled() is False

    def test_has_signals(self, qtbot, db):
        """Panel should have exercise_selected and load_code_requested signals."""
        panel = ExercisePanel(db)
        qtbot.addWidget(panel)
        assert hasattr(panel, "exercise_selected")
        assert hasattr(panel, "load_code_requested")


class TestExercisePanelLoadExercises:
    """Test loading exercises into the panel."""

    def test_load_exercises_populates_tree(self, qtbot, seeded_db):
        """Loading exercises should populate the tree grouped by chapter."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)

        panel.load_exercises("b1")

        # b1 has exercises in chapters 1 and 2
        assert panel._tree.topLevelItemCount() == 2

    def test_chapter_grouping(self, qtbot, seeded_db):
        """Top-level items should be chapter headers."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)
        panel.load_exercises("b1")

        ch1_item = panel._tree.topLevelItem(0)
        assert ch1_item.text(0) == "Chapter 1"

        ch2_item = panel._tree.topLevelItem(1)
        assert ch2_item.text(0) == "Chapter 2"

    def test_exercises_under_chapters(self, qtbot, seeded_db):
        """Exercises should appear as children of their chapter item."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)
        panel.load_exercises("b1")

        ch1_item = panel._tree.topLevelItem(0)
        # Chapter 1 has 2 exercises (ex1, ex2)
        assert ch1_item.childCount() == 2

        ch2_item = panel._tree.topLevelItem(1)
        # Chapter 2 has 1 exercise (ex3)
        assert ch2_item.childCount() == 1

    def test_exercise_titles_displayed(self, qtbot, seeded_db):
        """Exercise items should show the exercise title."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)
        panel.load_exercises("b1")

        ch1_item = panel._tree.topLevelItem(0)
        titles = {ch1_item.child(i).text(0) for i in range(ch1_item.childCount())}
        assert "Hello World" in titles
        assert "Name Input" in titles

    def test_completed_exercise_shows_done(self, qtbot, seeded_db):
        """Completed exercises should show 'Done' in the status column."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)
        panel.load_exercises("b1")

        ch1_item = panel._tree.topLevelItem(0)
        statuses = {}
        for i in range(ch1_item.childCount()):
            child = ch1_item.child(i)
            statuses[child.text(0)] = child.text(1)

        # ex1 ("Hello World") was marked complete in seeded_db
        assert statuses["Hello World"] == "Done"
        # ex2 ("Name Input") has no progress
        assert statuses["Name Input"] == ""

    def test_exercise_items_carry_id(self, qtbot, seeded_db):
        """Exercise tree items should carry exercise_id in UserRole data."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)
        panel.load_exercises("b1")

        ch1_item = panel._tree.topLevelItem(0)
        child = ch1_item.child(0)
        exercise_id = child.data(0, Qt.ItemDataRole.UserRole)
        assert exercise_id in ("ex1", "ex2")

    def test_chapter_headers_not_selectable(self, qtbot, seeded_db):
        """Chapter header items should not be selectable."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)
        panel.load_exercises("b1")

        ch1_item = panel._tree.topLevelItem(0)
        assert not (ch1_item.flags() & Qt.ItemFlag.ItemIsSelectable)

    def test_load_exercises_clears_previous(self, qtbot, seeded_db):
        """Loading exercises for a different book should clear the previous tree."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)

        panel.load_exercises("b1")
        assert panel._tree.topLevelItemCount() == 2

        panel.load_exercises("b2")
        # b2 has no exercises
        assert panel._tree.topLevelItemCount() == 0

    def test_load_exercises_sets_book_id(self, qtbot, seeded_db):
        """Loading exercises should set the internal _book_id."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)

        panel.load_exercises("b1")
        assert panel._book_id == "b1"


class TestExercisePanelItemClick:
    """Test clicking an exercise item in the tree."""

    def test_clicking_exercise_enables_buttons(self, qtbot, seeded_db):
        """Clicking an exercise should enable the Mark Complete and Try buttons."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)
        panel.load_exercises("b1")

        ch1_item = panel._tree.topLevelItem(0)
        exercise_item = ch1_item.child(0)

        panel._on_item_clicked(exercise_item, 0)

        assert panel._mark_done_btn.isEnabled() is True
        assert panel._try_btn.isEnabled() is True

    def test_clicking_exercise_sets_current_id(self, qtbot, seeded_db):
        """Clicking an exercise should set _current_exercise_id."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)
        panel.load_exercises("b1")

        ch1_item = panel._tree.topLevelItem(0)
        exercise_item = ch1_item.child(0)
        expected_id = exercise_item.data(0, Qt.ItemDataRole.UserRole)

        panel._on_item_clicked(exercise_item, 0)

        assert panel._current_exercise_id == expected_id

    def test_clicking_exercise_shows_details(self, qtbot, seeded_db):
        """Clicking an exercise should populate the detail view with HTML."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)
        panel.load_exercises("b1")

        ch1_item = panel._tree.topLevelItem(0)
        exercise_item = ch1_item.child(0)

        panel._on_item_clicked(exercise_item, 0)

        detail_text = panel._detail.toPlainText()
        assert len(detail_text) > 0

    def test_clicking_exercise_emits_signal(self, qtbot, seeded_db):
        """Clicking an exercise should emit exercise_selected signal."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)
        panel.load_exercises("b1")

        ch1_item = panel._tree.topLevelItem(0)
        exercise_item = ch1_item.child(0)
        expected_id = exercise_item.data(0, Qt.ItemDataRole.UserRole)

        signals = []
        panel.exercise_selected.connect(lambda eid: signals.append(eid))

        panel._on_item_clicked(exercise_item, 0)

        assert len(signals) == 1
        assert signals[0] == expected_id

    def test_clicking_chapter_header_does_nothing(self, qtbot, seeded_db):
        """Clicking a chapter header (no UserRole data) should not crash."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)
        panel.load_exercises("b1")

        ch1_item = panel._tree.topLevelItem(0)

        panel._on_item_clicked(ch1_item, 0)

        # Buttons should remain in their previous state (disabled)
        assert panel._current_exercise_id is None

    def test_exercise_detail_shows_title_and_description(self, qtbot, seeded_db):
        """Detail HTML should include the exercise title and description."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)
        panel.load_exercises("b1")

        # Find the "Hello World" exercise
        ch1_item = panel._tree.topLevelItem(0)
        for i in range(ch1_item.childCount()):
            child = ch1_item.child(i)
            if child.data(0, Qt.ItemDataRole.UserRole) == "ex1":
                panel._on_item_clicked(child, 0)
                break

        html_content = panel._detail.toHtml()
        assert "Hello World" in html_content
        assert "Write a hello world program" in html_content


class TestExercisePanelMarkComplete:
    """Test the Mark Complete functionality."""

    def test_mark_complete_updates_database(self, qtbot, seeded_db):
        """Marking an exercise complete should update the database."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)
        panel.load_exercises("b1")

        # Select ex2 (Name Input) which is not completed
        ch1_item = panel._tree.topLevelItem(0)
        for i in range(ch1_item.childCount()):
            child = ch1_item.child(i)
            if child.data(0, Qt.ItemDataRole.UserRole) == "ex2":
                panel._on_item_clicked(child, 0)
                break

        panel._mark_complete()

        progress = seeded_db.get_exercise_progress("ex2")
        assert progress is not None
        assert progress["completed"] == 1

    def test_mark_complete_updates_tree_status(self, qtbot, seeded_db):
        """After marking complete, the tree item should show 'Done'."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)
        panel.load_exercises("b1")

        ch1_item = panel._tree.topLevelItem(0)
        for i in range(ch1_item.childCount()):
            child = ch1_item.child(i)
            if child.data(0, Qt.ItemDataRole.UserRole) == "ex2":
                panel._tree.setCurrentItem(child)
                panel._on_item_clicked(child, 0)
                panel._mark_complete()
                assert child.text(1) == "Done"
                break

    def test_mark_complete_with_no_selection(self, qtbot, seeded_db):
        """Calling mark complete with no exercise selected should not crash."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)
        panel._current_exercise_id = None
        panel._mark_complete()  # Should not raise


class TestExercisePanelTryExercise:
    """Test the 'Try in Editor' functionality."""

    def test_try_exercise_emits_code(self, qtbot, seeded_db):
        """Clicking Try in Editor should emit load_code_requested with starter code."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)
        panel.load_exercises("b1")

        # Select ex1
        ch1_item = panel._tree.topLevelItem(0)
        for i in range(ch1_item.childCount()):
            child = ch1_item.child(i)
            if child.data(0, Qt.ItemDataRole.UserRole) == "ex1":
                panel._on_item_clicked(child, 0)
                break

        signals = []
        panel.load_code_requested.connect(lambda code: signals.append(code))

        panel._try_exercise()

        assert len(signals) == 1
        code = signals[0]
        assert "# Exercise: ex1" in code
        assert "Write a hello world program" in code
        assert "# Write your solution below" in code

    def test_try_exercise_with_no_selection(self, qtbot, seeded_db):
        """Calling try exercise with nothing selected should not crash or emit."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)

        signals = []
        panel.load_code_requested.connect(lambda code: signals.append(code))

        panel._try_exercise()
        assert len(signals) == 0

    def test_try_exercise_no_book_id(self, qtbot, seeded_db):
        """Calling try exercise when _book_id is empty should not crash."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)
        panel._current_exercise_id = "ex1"
        panel._book_id = ""

        signals = []
        panel.load_code_requested.connect(lambda code: signals.append(code))

        panel._try_exercise()
        assert len(signals) == 0

    def test_try_exercise_description_as_comments(self, qtbot, seeded_db):
        """The starter code should include the exercise description as comments."""
        panel = ExercisePanel(seeded_db)
        qtbot.addWidget(panel)
        panel.load_exercises("b1")

        # Select ex3 (Swap Variables) which has description "Swap two variables"
        ch2_item = panel._tree.topLevelItem(1)
        for i in range(ch2_item.childCount()):
            child = ch2_item.child(i)
            if child.data(0, Qt.ItemDataRole.UserRole) == "ex3":
                panel._on_item_clicked(child, 0)
                break

        signals = []
        panel.load_code_requested.connect(lambda code: signals.append(code))

        panel._try_exercise()

        code = signals[0]
        assert "# Swap two variables" in code


# ===========================================================================
# Import Validation Tests
# ===========================================================================


class TestImports:
    """Verify that all dialog modules import without errors.

    This catches issues like missing imports (e.g., QWidget not imported)
    that would cause the entire module to fail on import.
    """

    def test_notes_dialog_imports(self):
        """notes_dialog module should import without error."""
        from pylearn.ui import notes_dialog
        assert hasattr(notes_dialog, "NotesDialog")

    def test_bookmark_dialog_imports(self):
        """bookmark_dialog module should import without error."""
        from pylearn.ui import bookmark_dialog
        assert hasattr(bookmark_dialog, "BookmarkDialog")
        assert hasattr(bookmark_dialog, "add_bookmark_dialog")

    def test_progress_dialog_imports(self):
        """progress_dialog module should import without error."""
        from pylearn.ui import progress_dialog
        assert hasattr(progress_dialog, "ProgressDialog")

    def test_exercise_panel_imports(self):
        """exercise_panel module should import without error."""
        from pylearn.ui import exercise_panel
        assert hasattr(exercise_panel, "ExercisePanel")

    def test_notes_dialog_uses_qwidget(self):
        """NotesDialog module should have QWidget available (regression test)."""
        from pylearn.ui.notes_dialog import QWidget  # noqa: F401

    def test_notes_dialog_is_qdialog_subclass(self):
        """NotesDialog should be a subclass of QDialog."""
        from PyQt6.QtWidgets import QDialog
        assert issubclass(NotesDialog, QDialog)

    def test_bookmark_dialog_is_qdialog_subclass(self):
        """BookmarkDialog should be a subclass of QDialog."""
        from PyQt6.QtWidgets import QDialog
        assert issubclass(BookmarkDialog, QDialog)

    def test_progress_dialog_is_qdialog_subclass(self):
        """ProgressDialog should be a subclass of QDialog."""
        from PyQt6.QtWidgets import QDialog
        assert issubclass(ProgressDialog, QDialog)

    def test_exercise_panel_is_qwidget_subclass(self):
        """ExercisePanel should be a subclass of QWidget."""
        from PyQt6.QtWidgets import QWidget
        assert issubclass(ExercisePanel, QWidget)
