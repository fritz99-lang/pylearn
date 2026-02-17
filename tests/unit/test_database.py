"""Tests for database CRUD operations using in-memory SQLite."""

import pytest
from pylearn.core.database import Database


@pytest.fixture
def db(tmp_path):
    """Create an in-memory database for testing."""
    return Database(db_path=tmp_path / "test.db")


class TestBooks:
    def test_upsert_and_get(self, db):
        db.upsert_book("b1", "Book One", "/path/b1.pdf", 100, 10)
        books = db.get_books()
        assert len(books) == 1
        assert books[0]["book_id"] == "b1"
        assert books[0]["title"] == "Book One"
        assert books[0]["total_pages"] == 100

    def test_upsert_updates(self, db):
        db.upsert_book("b1", "Old Title", "/old.pdf", 50, 5)
        db.upsert_book("b1", "New Title", "/new.pdf", 100, 10)
        books = db.get_books()
        assert len(books) == 1
        assert books[0]["title"] == "New Title"
        assert books[0]["total_pages"] == 100


class TestChapters:
    def test_upsert_and_get(self, db):
        db.upsert_book("b1", "Book", "/b.pdf", 100, 2)
        db.upsert_chapter("b1", 1, "Chapter 1", 1, 50)
        db.upsert_chapter("b1", 2, "Chapter 2", 51, 100)
        chapters = db.get_chapters("b1")
        assert len(chapters) == 2
        assert chapters[0]["chapter_num"] == 1
        assert chapters[1]["chapter_num"] == 2

    def test_upsert_updates(self, db):
        db.upsert_book("b1", "Book", "/b.pdf", 100, 1)
        db.upsert_chapter("b1", 1, "Old Title", 1, 50)
        db.upsert_chapter("b1", 1, "New Title", 1, 60)
        chapters = db.get_chapters("b1")
        assert len(chapters) == 1
        assert chapters[0]["title"] == "New Title"
        assert chapters[0]["end_page"] == 60


class TestReadingProgress:
    def test_update_and_get(self, db):
        db.upsert_book("b1", "Book", "/b.pdf", 100, 2)
        db.update_reading_progress("b1", 1, "in_progress", 250)
        progress = db.get_reading_progress("b1", 1)
        assert progress is not None
        assert progress["status"] == "in_progress"
        assert progress["scroll_position"] == 250

    def test_nonexistent(self, db):
        assert db.get_reading_progress("nope", 1) is None

    def test_completion_stats(self, db):
        db.upsert_book("b1", "Book", "/b.pdf", 100, 3)
        db.upsert_chapter("b1", 1, "Ch1", 1, 30)
        db.upsert_chapter("b1", 2, "Ch2", 31, 60)
        db.upsert_chapter("b1", 3, "Ch3", 61, 100)
        db.update_reading_progress("b1", 1, "completed")
        db.update_reading_progress("b1", 2, "in_progress")
        stats = db.get_completion_stats("b1")
        assert stats["total"] == 3
        assert stats["completed"] == 1
        assert stats["in_progress"] == 1
        assert stats["not_started"] == 1
        assert stats["percent"] == 33

    def test_get_all_progress(self, db):
        db.upsert_book("b1", "Book", "/b.pdf", 100, 2)
        db.update_reading_progress("b1", 1, "completed")
        db.update_reading_progress("b1", 2, "in_progress")
        progress = db.get_all_progress("b1")
        assert len(progress) == 2


class TestLastPosition:
    def test_save_and_get(self, db):
        db.upsert_book("b1", "Book", "/b.pdf", 100, 1)
        db.save_last_position("b1", 3, 500)
        pos = db.get_last_position("b1")
        assert pos is not None
        assert pos["chapter_num"] == 3
        assert pos["scroll_position"] == 500

    def test_overwrite(self, db):
        db.upsert_book("b1", "Book", "/b.pdf", 100, 1)
        db.save_last_position("b1", 1, 100)
        db.save_last_position("b1", 5, 999)
        pos = db.get_last_position("b1")
        assert pos["chapter_num"] == 5
        assert pos["scroll_position"] == 999

    def test_nonexistent(self, db):
        assert db.get_last_position("nope") is None


class TestBookmarks:
    def test_add_and_get(self, db):
        db.upsert_book("b1", "Book", "/b.pdf", 100, 1)
        bm_id = db.add_bookmark("b1", 3, 250, "Important section")
        assert bm_id > 0
        bookmarks = db.get_bookmarks("b1")
        assert len(bookmarks) == 1
        assert bookmarks[0]["label"] == "Important section"
        assert bookmarks[0]["chapter_num"] == 3

    def test_delete(self, db):
        db.upsert_book("b1", "Book", "/b.pdf", 100, 1)
        bm_id = db.add_bookmark("b1", 1, 0, "Delete me")
        db.delete_bookmark(bm_id)
        assert len(db.get_bookmarks("b1")) == 0

    def test_get_all(self, db):
        db.upsert_book("b1", "Book", "/b.pdf", 100, 1)
        db.upsert_book("b2", "Book 2", "/b2.pdf", 50, 1)
        db.add_bookmark("b1", 1, 0, "BM1")
        db.add_bookmark("b2", 1, 0, "BM2")
        all_bm = db.get_bookmarks()
        assert len(all_bm) == 2


class TestNotes:
    def test_add_and_get(self, db):
        db.upsert_book("b1", "Book", "/b.pdf", 100, 1)
        note_id = db.add_note("b1", 2, "Variables", "Remember to use snake_case")
        assert note_id > 0
        notes = db.get_notes("b1", 2)
        assert len(notes) == 1
        assert notes[0]["content"] == "Remember to use snake_case"
        assert notes[0]["section_title"] == "Variables"

    def test_update(self, db):
        db.upsert_book("b1", "Book", "/b.pdf", 100, 1)
        note_id = db.add_note("b1", 1, "", "Original")
        db.update_note(note_id, "Updated content")
        notes = db.get_notes("b1", 1)
        assert notes[0]["content"] == "Updated content"

    def test_delete(self, db):
        db.upsert_book("b1", "Book", "/b.pdf", 100, 1)
        note_id = db.add_note("b1", 1, "", "To delete")
        db.delete_note(note_id)
        assert len(db.get_notes("b1", 1)) == 0

    def test_get_by_book(self, db):
        db.upsert_book("b1", "Book", "/b.pdf", 100, 1)
        db.add_note("b1", 1, "", "Note 1")
        db.add_note("b1", 2, "", "Note 2")
        notes = db.get_notes("b1")
        assert len(notes) == 2


class TestExercises:
    def test_upsert_and_get(self, db):
        db.upsert_book("b1", "Book", "/b.pdf", 100, 1)
        db.upsert_exercise("ex1", "b1", 1, "Exercise 1", "Do this", "exercise", "answer")
        exercises = db.get_exercises("b1")
        assert len(exercises) == 1
        assert exercises[0]["title"] == "Exercise 1"
        assert exercises[0]["answer"] == "answer"

    def test_get_by_chapter(self, db):
        db.upsert_book("b1", "Book", "/b.pdf", 100, 2)
        db.upsert_exercise("ex1", "b1", 1, "Ex1", "Desc1", "exercise")
        db.upsert_exercise("ex2", "b1", 2, "Ex2", "Desc2", "exercise")
        ch1 = db.get_exercises("b1", chapter_num=1)
        assert len(ch1) == 1
        assert ch1[0]["exercise_id"] == "ex1"

    def test_progress(self, db):
        db.upsert_book("b1", "Book", "/b.pdf", 100, 1)
        db.upsert_exercise("ex1", "b1", 1, "Ex1", "Desc", "exercise")
        db.update_exercise_progress("ex1", True, "my code")
        progress = db.get_exercise_progress("ex1")
        assert progress is not None
        assert progress["completed"] == 1
        assert progress["user_code"] == "my code"
        assert progress["attempts"] == 1

    def test_progress_increments_attempts(self, db):
        db.upsert_book("b1", "Book", "/b.pdf", 100, 1)
        db.upsert_exercise("ex1", "b1", 1, "Ex1", "Desc", "exercise")
        db.update_exercise_progress("ex1", False, "attempt 1")
        db.update_exercise_progress("ex1", True, "attempt 2")
        progress = db.get_exercise_progress("ex1")
        assert progress["attempts"] == 2
        assert progress["completed"] == 1


class TestSavedCode:
    def test_save_and_get(self, db):
        db.upsert_book("b1", "Book", "/b.pdf", 100, 1)
        code_id = db.save_code("b1", 1, "print('hello')", "my snippet")
        assert code_id > 0
        saved = db.get_saved_code("b1", 1)
        assert len(saved) == 1
        assert saved[0]["code"] == "print('hello')"
        assert saved[0]["label"] == "my snippet"

    def test_delete(self, db):
        db.upsert_book("b1", "Book", "/b.pdf", 100, 1)
        code_id = db.save_code("b1", 1, "x = 1", "")
        db.delete_saved_code(code_id)
        assert len(db.get_saved_code("b1", 1)) == 0
