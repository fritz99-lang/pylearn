# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Load quiz, challenge, and project content from JSON files."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pylearn.core.constants import APP_DIR
from pylearn.core.models import ChallengeSet, ProjectMeta, ProjectStep, QuizSet

logger = logging.getLogger("pylearn.content")

CONTENT_DIR = APP_DIR / "content"


class ContentLoader:
    """Loads learning content (quizzes, challenges, projects) from JSON files.

    Content lives in content/{book_id}/quizzes/ch{NN}.json etc.
    """

    def __init__(self, content_dir: Path | None = None) -> None:
        self._content_dir = content_dir or CONTENT_DIR

    def load_quiz(self, book_id: str, chapter_num: int) -> QuizSet | None:
        """Load quiz questions for a specific chapter.

        Returns None if no quiz file exists for this chapter.
        """
        path = self._quiz_path(book_id, chapter_num)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return QuizSet.from_dict(data)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Failed to load quiz %s ch%d: %s", book_id, chapter_num, e)
            return None

    def list_quiz_chapters(self, book_id: str) -> list[int]:
        """Return sorted list of chapter numbers that have quizzes."""
        quiz_dir = self._content_dir / book_id / "quizzes"
        if not quiz_dir.exists():
            return []
        chapters = []
        for path in quiz_dir.glob("ch*.json"):
            stem = path.stem  # e.g., "ch01"
            try:
                chapters.append(int(stem[2:]))
            except ValueError:
                continue
        return sorted(chapters)

    def has_quiz(self, book_id: str, chapter_num: int) -> bool:
        """Check if a quiz exists for this chapter."""
        return self._quiz_path(book_id, chapter_num).exists()

    # --- Challenges ---

    def load_challenges(self, book_id: str, chapter_num: int) -> ChallengeSet | None:
        """Load code challenges for a specific chapter."""
        path = self._challenge_path(book_id, chapter_num)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ChallengeSet.from_dict(data)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Failed to load challenges %s ch%d: %s", book_id, chapter_num, e)
            return None

    def list_challenge_chapters(self, book_id: str) -> list[int]:
        """Return sorted list of chapter numbers that have challenges."""
        ch_dir = self._content_dir / book_id / "challenges"
        if not ch_dir.exists():
            return []
        chapters = []
        for path in ch_dir.glob("ch*.json"):
            try:
                chapters.append(int(path.stem[2:]))
            except ValueError:
                continue
        return sorted(chapters)

    def has_challenges(self, book_id: str, chapter_num: int) -> bool:
        """Check if challenges exist for this chapter."""
        return self._challenge_path(book_id, chapter_num).exists()

    # --- Project ---

    def load_project_meta(self, book_id: str) -> ProjectMeta | None:
        """Load project metadata (title, description)."""
        path = self._content_dir / book_id / "project" / "project.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ProjectMeta.from_dict(data)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Failed to load project meta %s: %s", book_id, e)
            return None

    def load_project_step(self, book_id: str, chapter_num: int) -> ProjectStep | None:
        """Load a project step for a specific chapter."""
        path = self._content_dir / book_id / "project" / f"ch{chapter_num:02d}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ProjectStep.from_dict(data)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Failed to load project step %s ch%d: %s", book_id, chapter_num, e)
            return None

    def list_project_steps(self, book_id: str) -> list[int]:
        """Return sorted chapter numbers that have project steps."""
        proj_dir = self._content_dir / book_id / "project"
        if not proj_dir.exists():
            return []
        chapters = []
        for path in proj_dir.glob("ch*.json"):
            try:
                chapters.append(int(path.stem[2:]))
            except ValueError:
                continue
        return sorted(chapters)

    def has_project(self, book_id: str) -> bool:
        """Check if a project exists for this book."""
        return (self._content_dir / book_id / "project" / "project.json").exists()

    # --- Paths ---

    def _quiz_path(self, book_id: str, chapter_num: int) -> Path:
        return self._content_dir / book_id / "quizzes" / f"ch{chapter_num:02d}.json"

    def _challenge_path(self, book_id: str, chapter_num: int) -> Path:
        return self._content_dir / book_id / "challenges" / f"ch{chapter_num:02d}.json"
