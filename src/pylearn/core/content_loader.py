# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Load quiz, challenge, and project content from JSON files."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pylearn.core.constants import APP_DIR, IS_FROZEN
from pylearn.core.models import ChallengeSet, ProjectMeta, ProjectStep, QuizSet

logger = logging.getLogger("pylearn.content")


def _resolve_content_dir() -> Path:
    """Return content directory, checking the PyInstaller bundle first."""
    if IS_FROZEN:
        import sys

        bundle_content = Path(sys._MEIPASS) / "content"  # type: ignore[attr-defined]
        if bundle_content.exists():
            return bundle_content
    return APP_DIR / "content"


CONTENT_DIR = _resolve_content_dir()


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

    def _project_dir(self, book_id: str, project_id: str | None = None) -> Path:
        """Return the directory for a project.

        Supports two layouts:
          - Single project: content/{book_id}/project/
          - Multiple projects: content/{book_id}/projects/{project_id}/
        When project_id is None, falls back to the single-project directory.
        """
        if project_id:
            return self._content_dir / book_id / "projects" / project_id
        return self._content_dir / book_id / "project"

    def list_projects(self, book_id: str) -> list[ProjectMeta]:
        """Return all available projects for a book.

        Checks both content/{book_id}/project/ and content/{book_id}/projects/*/.
        """
        projects: list[ProjectMeta] = []

        # Single-project directory
        single = self._content_dir / book_id / "project" / "project.json"
        if single.exists():
            meta = self._load_meta_from(single)
            if meta:
                projects.append(meta)

        # Multi-project directory
        multi_dir = self._content_dir / book_id / "projects"
        if multi_dir.exists():
            for sub in sorted(multi_dir.iterdir()):
                if sub.is_dir() and (sub / "project.json").exists():
                    meta = self._load_meta_from(sub / "project.json")
                    if meta:
                        projects.append(meta)

        return projects

    def _load_meta_from(self, path: Path) -> ProjectMeta | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            meta = ProjectMeta.from_dict(data)
            # Store the project_id for multi-project lookup
            if "projects" in path.parts:
                meta.project_id = path.parent.name
            return meta
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Failed to load project meta %s: %s", path, e)
            return None

    def load_project_meta(self, book_id: str, project_id: str | None = None) -> ProjectMeta | None:
        """Load project metadata (title, description)."""
        path = self._project_dir(book_id, project_id) / "project.json"
        if not path.exists():
            return None
        return self._load_meta_from(path)

    def load_project_step(self, book_id: str, chapter_num: int, project_id: str | None = None) -> ProjectStep | None:
        """Load a project step for a specific chapter."""
        path = self._project_dir(book_id, project_id) / f"ch{chapter_num:02d}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ProjectStep.from_dict(data)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Failed to load project step %s ch%d: %s", book_id, chapter_num, e)
            return None

    def list_project_steps(self, book_id: str, project_id: str | None = None) -> list[int]:
        """Return sorted chapter numbers that have project steps."""
        proj_dir = self._project_dir(book_id, project_id)
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
        """Check if at least one project exists for this book."""
        if (self._content_dir / book_id / "project" / "project.json").exists():
            return True
        multi_dir = self._content_dir / book_id / "projects"
        if multi_dir.exists():
            return any((sub / "project.json").exists() for sub in multi_dir.iterdir() if sub.is_dir())
        return False

    # --- Paths ---

    def _quiz_path(self, book_id: str, chapter_num: int) -> Path:
        return self._content_dir / book_id / "quizzes" / f"ch{chapter_num:02d}.json"

    def _challenge_path(self, book_id: str, chapter_num: int) -> Path:
        return self._content_dir / book_id / "challenges" / f"ch{chapter_num:02d}.json"
