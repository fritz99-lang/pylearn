# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Extract exercises, quizzes, and recipes from parsed content."""

from __future__ import annotations

import re
import logging

from pylearn.core.models import BlockType, ContentBlock, Exercise, Chapter

logger = logging.getLogger("pylearn.parser")


class ExerciseExtractor:
    """Extract exercises from different book formats."""

    def extract_from_chapters(self, book_id: str, chapters: list[Chapter]) -> list[Exercise]:
        """Extract exercises from all chapters by trying all extractors.

        Runs the generic extractor first, then tries specialized patterns
        (Learning Python quizzes, cookbook recipes, Programming Python exercises).
        Uses whichever finds results for each chapter.
        """
        # Try all extractors and merge results
        generic = self._extract_generic(book_id, chapters)
        quiz = self._extract_learning_python(book_id, chapters)
        recipes = self._extract_cookbook(book_id, chapters)
        prog_ex = self._extract_programming_python(book_id, chapters)

        # Collect chapters covered by each extractor
        generic_chapters = {e.chapter_num for e in generic}
        all_exercises: list[Exercise] = []

        # Prefer specialized results over generic when both find content
        specialized_chapters: set[int] = set()
        for specialized in (quiz, recipes, prog_ex):
            if specialized:
                all_exercises.extend(specialized)
                specialized_chapters.update(e.chapter_num for e in specialized)

        # Add generic results for chapters not covered by specialized extractors
        for e in generic:
            if e.chapter_num not in specialized_chapters:
                all_exercises.append(e)

        return all_exercises

    def _extract_learning_python(self, book_id: str, chapters: list[Chapter]) -> list[Exercise]:
        """Learning Python has 'Test Your Knowledge: Quiz' and 'Answers' sections."""
        exercises: list[Exercise] = []
        exercise_idx = 0

        for chapter in chapters:
            in_quiz = False
            in_answers = False
            quiz_text_parts: list[str] = []
            answer_text_parts: list[str] = []

            for block in chapter.content_blocks:
                text = block.text.strip()

                if re.search(r"Test Your Knowledge:\s*Quiz", text, re.IGNORECASE):
                    in_quiz = True
                    in_answers = False
                    continue
                elif re.search(r"Test Your Knowledge:\s*Answers", text, re.IGNORECASE):
                    in_answers = True
                    in_quiz = False
                    continue
                elif block.block_type in (BlockType.HEADING1, BlockType.HEADING2):
                    if in_quiz or in_answers:
                        # End of quiz/answer section
                        if quiz_text_parts:
                            exercise_id = f"{book_id}_ch{chapter.chapter_num}_q{exercise_idx}"
                            exercises.append(Exercise(
                                exercise_id=exercise_id,
                                book_id=book_id,
                                chapter_num=chapter.chapter_num,
                                title=f"Chapter {chapter.chapter_num} Quiz",
                                description="\n".join(quiz_text_parts),
                                exercise_type="quiz",
                                answer="\n".join(answer_text_parts) if answer_text_parts else None,
                                page_num=chapter.start_page,
                            ))
                            exercise_idx += 1
                            quiz_text_parts = []
                            answer_text_parts = []
                        in_quiz = False
                        in_answers = False

                if in_quiz:
                    quiz_text_parts.append(text)
                elif in_answers:
                    answer_text_parts.append(text)

            # Flush any remaining quiz
            if quiz_text_parts:
                exercise_id = f"{book_id}_ch{chapter.chapter_num}_q{exercise_idx}"
                exercises.append(Exercise(
                    exercise_id=exercise_id,
                    book_id=book_id,
                    chapter_num=chapter.chapter_num,
                    title=f"Chapter {chapter.chapter_num} Quiz",
                    description="\n".join(quiz_text_parts),
                    exercise_type="quiz",
                    answer="\n".join(answer_text_parts) if answer_text_parts else None,
                    page_num=chapter.start_page,
                ))
                exercise_idx += 1

        return exercises

    def _extract_cookbook(self, book_id: str, chapters: list[Chapter]) -> list[Exercise]:
        """Python Cookbook: each recipe (N.N. Title) is treated as an exercise."""
        exercises: list[Exercise] = []
        recipe_pattern = re.compile(r"^(\d+\.\d+)\.\s+(.+)")

        for chapter in chapters:
            for block in chapter.content_blocks:
                if block.block_type in (BlockType.HEADING2, BlockType.HEADING3):
                    match = recipe_pattern.match(block.text.strip())
                    if match:
                        recipe_num = match.group(1)
                        recipe_title = match.group(2)
                        exercise_id = f"{book_id}_recipe_{recipe_num}"
                        exercises.append(Exercise(
                            exercise_id=exercise_id,
                            book_id=book_id,
                            chapter_num=chapter.chapter_num,
                            title=f"Recipe {recipe_num}: {recipe_title}",
                            description=f"Implement the solution for: {recipe_title}",
                            exercise_type="recipe",
                            page_num=block.page_num,
                        ))

        return exercises

    def _extract_programming_python(self, book_id: str, chapters: list[Chapter]) -> list[Exercise]:
        """Programming Python: look for explicit exercise sections."""
        exercises: list[Exercise] = []
        exercise_idx = 0

        for chapter in chapters:
            in_exercises = False
            current_parts: list[str] = []

            for block in chapter.content_blocks:
                text = block.text.strip()

                if re.search(r"Exercise[s]?\s*$", text, re.IGNORECASE) and block.block_type in (BlockType.HEADING2, BlockType.HEADING3):
                    in_exercises = True
                    continue

                if in_exercises:
                    if block.block_type in (BlockType.HEADING1, BlockType.HEADING2):
                        # End of exercises
                        if current_parts:
                            exercise_id = f"{book_id}_ch{chapter.chapter_num}_ex{exercise_idx}"
                            exercises.append(Exercise(
                                exercise_id=exercise_id,
                                book_id=book_id,
                                chapter_num=chapter.chapter_num,
                                title=f"Chapter {chapter.chapter_num} Exercises",
                                description="\n".join(current_parts),
                                exercise_type="exercise",
                                page_num=chapter.start_page,
                            ))
                            exercise_idx += 1
                            current_parts = []
                        in_exercises = False
                    else:
                        current_parts.append(text)

            if current_parts:
                exercise_id = f"{book_id}_ch{chapter.chapter_num}_ex{exercise_idx}"
                exercises.append(Exercise(
                    exercise_id=exercise_id,
                    book_id=book_id,
                    chapter_num=chapter.chapter_num,
                    title=f"Chapter {chapter.chapter_num} Exercises",
                    description="\n".join(current_parts),
                    exercise_type="exercise",
                    page_num=chapter.start_page,
                ))
                exercise_idx += 1

        return exercises

    def _extract_generic(self, book_id: str, chapters: list[Chapter]) -> list[Exercise]:
        """Generic extraction: look for common exercise patterns."""
        exercises: list[Exercise] = []
        exercise_pattern = re.compile(r"(?:Exercise|Problem|Challenge)\s+(\d+)", re.IGNORECASE)
        exercise_idx = 0

        for chapter in chapters:
            for block in chapter.content_blocks:
                if block.block_type in (BlockType.HEADING2, BlockType.HEADING3):
                    match = exercise_pattern.search(block.text)
                    if match:
                        exercise_id = f"{book_id}_ch{chapter.chapter_num}_ex{exercise_idx}"
                        exercises.append(Exercise(
                            exercise_id=exercise_id,
                            book_id=book_id,
                            chapter_num=chapter.chapter_num,
                            title=block.text.strip(),
                            description="",
                            exercise_type="exercise",
                            page_num=block.page_num,
                        ))
                        exercise_idx += 1

        return exercises
