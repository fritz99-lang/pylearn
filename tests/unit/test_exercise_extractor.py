# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Tests for the ExerciseExtractor — all four extraction strategies plus merge logic."""

from __future__ import annotations

import pytest

from pylearn.core.models import BlockType, Chapter, ContentBlock, Section
from pylearn.parser.exercise_extractor import ExerciseExtractor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_block(
    block_type: BlockType,
    text: str,
    page_num: int = 1,
) -> ContentBlock:
    """Create a ContentBlock with minimal boilerplate."""
    return ContentBlock(block_type=block_type, text=text, page_num=page_num)


def make_chapter(
    num: int,
    blocks: list[ContentBlock],
    start_page: int = 1,
    end_page: int = 10,
) -> Chapter:
    """Create a Chapter with sensible defaults."""
    return Chapter(
        chapter_num=num,
        title=f"Chapter {num}",
        start_page=start_page,
        end_page=end_page,
        sections=[Section(title=f"Section {num}.1", level=2, page_num=start_page, block_index=0)],
        content_blocks=blocks,
    )


# ---------------------------------------------------------------------------
# Fixture: shared extractor instance
# ---------------------------------------------------------------------------


@pytest.fixture
def extractor() -> ExerciseExtractor:
    return ExerciseExtractor()


BOOK_ID = "test_book"


# ===========================================================================
# extract_from_chapters — top-level integration
# ===========================================================================


class TestExtractFromChapters:
    """Tests for the public extract_from_chapters() entry point."""

    def test_empty_chapters_list(self, extractor: ExerciseExtractor) -> None:
        """Passing no chapters should return an empty list."""
        result = extractor.extract_from_chapters(BOOK_ID, [])
        assert result == []

    def test_chapters_with_no_exercise_content(self, extractor: ExerciseExtractor) -> None:
        """Chapters containing only body text should yield no exercises."""
        chapters = [
            make_chapter(
                1,
                [
                    make_block(BlockType.HEADING1, "Introduction"),
                    make_block(BlockType.BODY, "This is body text."),
                    make_block(BlockType.CODE, "x = 1"),
                ],
            ),
        ]
        result = extractor.extract_from_chapters(BOOK_ID, chapters)
        assert result == []

    def test_generic_exercise_detected(self, extractor: ExerciseExtractor) -> None:
        """A heading matching the generic pattern should produce an exercise."""
        chapters = [
            make_chapter(
                1,
                [
                    make_block(BlockType.HEADING2, "Exercise 1"),
                    make_block(BlockType.BODY, "Write a function."),
                ],
            ),
        ]
        result = extractor.extract_from_chapters(BOOK_ID, chapters)
        assert len(result) == 1
        ex = result[0]
        assert ex.book_id == BOOK_ID
        assert ex.chapter_num == 1
        assert ex.title == "Exercise 1"
        assert ex.exercise_type == "exercise"

    def test_exercise_id_contains_book_and_chapter(self, extractor: ExerciseExtractor) -> None:
        """Exercise IDs must encode book_id and chapter_num for uniqueness."""
        chapters = [
            make_chapter(5, [make_block(BlockType.HEADING3, "Problem 3")]),
        ]
        result = extractor.extract_from_chapters(BOOK_ID, chapters)
        assert len(result) == 1
        assert BOOK_ID in result[0].exercise_id
        assert "ch5" in result[0].exercise_id

    def test_specialized_overrides_generic_for_same_chapter(self, extractor: ExerciseExtractor) -> None:
        """When a specialized extractor finds exercises in a chapter, generic
        results for that same chapter are discarded."""
        # Build a chapter that triggers BOTH the Learning Python quiz extractor
        # AND the generic extractor (heading "Exercise 1").
        chapters = [
            make_chapter(
                1,
                [
                    make_block(BlockType.HEADING2, "Test Your Knowledge: Quiz"),
                    make_block(BlockType.BODY, "Q1: What is Python?"),
                    make_block(BlockType.HEADING2, "Test Your Knowledge: Answers"),
                    make_block(BlockType.BODY, "A1: A programming language."),
                    make_block(BlockType.HEADING1, "Next Section"),
                    # Also a generic exercise heading in the same chapter
                    make_block(BlockType.HEADING2, "Exercise 1"),
                ],
            ),
        ]
        result = extractor.extract_from_chapters(BOOK_ID, chapters)
        # Specialized quiz extractor finds chapter 1 -> generic chapter-1 results dropped
        types = {e.exercise_type for e in result}
        assert "quiz" in types
        # The generic "Exercise 1" for ch1 should be excluded
        generic_titles = [e.title for e in result if e.exercise_type == "exercise"]
        assert generic_titles == []

    def test_generic_kept_for_chapters_without_specialized(self, extractor: ExerciseExtractor) -> None:
        """Generic results are kept for chapters where no specialized extractor matched."""
        chapters = [
            # Chapter 1: quiz (specialized)
            make_chapter(
                1,
                [
                    make_block(BlockType.HEADING2, "Test Your Knowledge: Quiz"),
                    make_block(BlockType.BODY, "Q1: What is a list?"),
                    make_block(BlockType.HEADING1, "End"),
                ],
            ),
            # Chapter 2: generic exercise only
            make_chapter(
                2,
                [
                    make_block(BlockType.HEADING2, "Challenge 7"),
                ],
            ),
        ]
        result = extractor.extract_from_chapters(BOOK_ID, chapters)
        ch1 = [e for e in result if e.chapter_num == 1]
        ch2 = [e for e in result if e.chapter_num == 2]
        assert len(ch1) == 1 and ch1[0].exercise_type == "quiz"
        assert len(ch2) == 1 and ch2[0].exercise_type == "exercise"

    def test_multiple_chapters_accumulate(self, extractor: ExerciseExtractor) -> None:
        """Exercises across many chapters are collected together."""
        chapters = [make_chapter(i, [make_block(BlockType.HEADING2, f"Exercise {i}")]) for i in range(1, 6)]
        result = extractor.extract_from_chapters(BOOK_ID, chapters)
        assert len(result) == 5
        assert {e.chapter_num for e in result} == {1, 2, 3, 4, 5}


# ===========================================================================
# _extract_generic — pattern: "Exercise N", "Problem N", "Challenge N"
# ===========================================================================


class TestGenericExtractor:
    """Tests for the _extract_generic strategy."""

    def test_exercise_heading2(self, extractor: ExerciseExtractor) -> None:
        chapters = [make_chapter(1, [make_block(BlockType.HEADING2, "Exercise 1")])]
        result = extractor._extract_generic(BOOK_ID, chapters)
        assert len(result) == 1
        assert result[0].title == "Exercise 1"

    def test_problem_heading3(self, extractor: ExerciseExtractor) -> None:
        chapters = [make_chapter(1, [make_block(BlockType.HEADING3, "Problem 42")])]
        result = extractor._extract_generic(BOOK_ID, chapters)
        assert len(result) == 1
        assert result[0].title == "Problem 42"

    def test_challenge_heading(self, extractor: ExerciseExtractor) -> None:
        chapters = [make_chapter(1, [make_block(BlockType.HEADING2, "Challenge 99")])]
        result = extractor._extract_generic(BOOK_ID, chapters)
        assert len(result) == 1
        assert result[0].title == "Challenge 99"

    def test_case_insensitive(self, extractor: ExerciseExtractor) -> None:
        """The pattern uses re.IGNORECASE."""
        chapters = [make_chapter(1, [make_block(BlockType.HEADING2, "EXERCISE 5")])]
        result = extractor._extract_generic(BOOK_ID, chapters)
        assert len(result) == 1

    def test_body_block_type_ignored(self, extractor: ExerciseExtractor) -> None:
        """Only HEADING2 and HEADING3 block types trigger the generic extractor."""
        chapters = [make_chapter(1, [make_block(BlockType.BODY, "Exercise 1")])]
        result = extractor._extract_generic(BOOK_ID, chapters)
        assert result == []

    def test_heading1_ignored(self, extractor: ExerciseExtractor) -> None:
        """HEADING1 is not one of the checked block types."""
        chapters = [make_chapter(1, [make_block(BlockType.HEADING1, "Exercise 1")])]
        result = extractor._extract_generic(BOOK_ID, chapters)
        assert result == []

    def test_no_number_no_match(self, extractor: ExerciseExtractor) -> None:
        """The regex requires a number after the keyword."""
        chapters = [make_chapter(1, [make_block(BlockType.HEADING2, "Exercises")])]
        result = extractor._extract_generic(BOOK_ID, chapters)
        assert result == []

    def test_multiple_exercises_same_chapter(self, extractor: ExerciseExtractor) -> None:
        chapters = [
            make_chapter(
                3,
                [
                    make_block(BlockType.HEADING2, "Exercise 1"),
                    make_block(BlockType.BODY, "Do this."),
                    make_block(BlockType.HEADING2, "Exercise 2"),
                    make_block(BlockType.BODY, "Do that."),
                ],
            ),
        ]
        result = extractor._extract_generic(BOOK_ID, chapters)
        assert len(result) == 2
        assert result[0].exercise_id != result[1].exercise_id

    def test_exercise_page_num_from_block(self, extractor: ExerciseExtractor) -> None:
        """The generic extractor uses the block's page_num."""
        chapters = [
            make_chapter(1, [make_block(BlockType.HEADING2, "Exercise 1", page_num=77)]),
        ]
        result = extractor._extract_generic(BOOK_ID, chapters)
        assert result[0].page_num == 77


# ===========================================================================
# _extract_learning_python — "Test Your Knowledge: Quiz / Answers"
# ===========================================================================


class TestLearningPythonExtractor:
    """Tests for the quiz/answer Learning Python strategy."""

    def test_quiz_section_creates_exercise(self, extractor: ExerciseExtractor) -> None:
        chapters = [
            make_chapter(
                1,
                [
                    make_block(BlockType.HEADING2, "Test Your Knowledge: Quiz"),
                    make_block(BlockType.BODY, "Q1: What is a variable?"),
                    make_block(BlockType.BODY, "Q2: What is a loop?"),
                    make_block(BlockType.HEADING1, "Next Chapter"),
                ],
            ),
        ]
        result = extractor._extract_learning_python(BOOK_ID, chapters)
        assert len(result) == 1
        ex = result[0]
        assert ex.exercise_type == "quiz"
        assert "Q1: What is a variable?" in ex.description
        assert "Q2: What is a loop?" in ex.description
        assert ex.answer is None  # no answers section

    def test_quiz_with_answers(self, extractor: ExerciseExtractor) -> None:
        chapters = [
            make_chapter(
                2,
                [
                    make_block(BlockType.HEADING2, "Test Your Knowledge: Quiz"),
                    make_block(BlockType.BODY, "Q1: Name three data types."),
                    make_block(BlockType.HEADING2, "Test Your Knowledge: Answers"),
                    make_block(BlockType.BODY, "A1: int, str, list."),
                    make_block(BlockType.HEADING1, "Summary"),
                ],
            ),
        ]
        result = extractor._extract_learning_python(BOOK_ID, chapters)
        assert len(result) == 1
        assert result[0].answer is not None
        assert "int, str, list" in result[0].answer

    def test_quiz_flushed_at_end_of_chapter(self, extractor: ExerciseExtractor) -> None:
        """If the quiz is the last section in a chapter (no trailing heading),
        it should still be captured by the flush logic."""
        chapters = [
            make_chapter(
                3,
                [
                    make_block(BlockType.HEADING2, "Test Your Knowledge: Quiz"),
                    make_block(BlockType.BODY, "Q1: Explain scope."),
                ],
            ),
        ]
        result = extractor._extract_learning_python(BOOK_ID, chapters)
        assert len(result) == 1
        assert result[0].title == "Chapter 3 Quiz"

    def test_answers_flushed_at_end_of_chapter(self, extractor: ExerciseExtractor) -> None:
        """Quiz with answers at the very end of a chapter (no trailing heading)."""
        chapters = [
            make_chapter(
                4,
                [
                    make_block(BlockType.HEADING2, "Test Your Knowledge: Quiz"),
                    make_block(BlockType.BODY, "Q1: What is immutability?"),
                    make_block(BlockType.HEADING2, "Test Your Knowledge: Answers"),
                    make_block(BlockType.BODY, "A1: Objects that cannot change."),
                ],
            ),
        ]
        result = extractor._extract_learning_python(BOOK_ID, chapters)
        assert len(result) == 1
        assert "immutability" in result[0].description
        assert result[0].answer is not None

    def test_no_quiz_section_returns_empty(self, extractor: ExerciseExtractor) -> None:
        chapters = [
            make_chapter(
                1,
                [
                    make_block(BlockType.HEADING2, "Summary"),
                    make_block(BlockType.BODY, "This chapter covered..."),
                ],
            ),
        ]
        result = extractor._extract_learning_python(BOOK_ID, chapters)
        assert result == []

    def test_case_insensitive_quiz_header(self, extractor: ExerciseExtractor) -> None:
        """The regex uses re.IGNORECASE so mixed case should match."""
        chapters = [
            make_chapter(
                1,
                [
                    make_block(BlockType.HEADING2, "test your knowledge: quiz"),
                    make_block(BlockType.BODY, "Q1: Trivial."),
                    make_block(BlockType.HEADING1, "End"),
                ],
            ),
        ]
        result = extractor._extract_learning_python(BOOK_ID, chapters)
        assert len(result) == 1

    def test_page_num_uses_chapter_start_page(self, extractor: ExerciseExtractor) -> None:
        chapters = [
            make_chapter(
                1,
                [
                    make_block(BlockType.HEADING2, "Test Your Knowledge: Quiz"),
                    make_block(BlockType.BODY, "Q1"),
                    make_block(BlockType.HEADING1, "End"),
                ],
                start_page=55,
            ),
        ]
        result = extractor._extract_learning_python(BOOK_ID, chapters)
        assert result[0].page_num == 55


# ===========================================================================
# _extract_cookbook — recipe pattern "N.N. Title"
# ===========================================================================


class TestCookbookExtractor:
    """Tests for the Python Cookbook recipe strategy."""

    def test_recipe_heading2(self, extractor: ExerciseExtractor) -> None:
        chapters = [
            make_chapter(
                1,
                [
                    make_block(BlockType.HEADING2, "1.1. Unpacking a Sequence"),
                ],
            ),
        ]
        result = extractor._extract_cookbook(BOOK_ID, chapters)
        assert len(result) == 1
        assert result[0].exercise_type == "recipe"
        assert "Unpacking a Sequence" in result[0].title
        assert result[0].exercise_id == f"{BOOK_ID}_recipe_1.1"

    def test_recipe_heading3(self, extractor: ExerciseExtractor) -> None:
        chapters = [
            make_chapter(
                4,
                [
                    make_block(BlockType.HEADING3, "4.12. Iterating Over Multiple Sequences"),
                ],
            ),
        ]
        result = extractor._extract_cookbook(BOOK_ID, chapters)
        assert len(result) == 1
        assert "4.12" in result[0].exercise_id

    def test_non_recipe_heading_ignored(self, extractor: ExerciseExtractor) -> None:
        """A heading without the N.N. pattern should not match."""
        chapters = [
            make_chapter(
                1,
                [
                    make_block(BlockType.HEADING2, "Introduction to Recipes"),
                ],
            ),
        ]
        result = extractor._extract_cookbook(BOOK_ID, chapters)
        assert result == []

    def test_body_block_type_ignored(self, extractor: ExerciseExtractor) -> None:
        chapters = [
            make_chapter(
                1,
                [
                    make_block(BlockType.BODY, "1.1. This is body text, not heading"),
                ],
            ),
        ]
        result = extractor._extract_cookbook(BOOK_ID, chapters)
        assert result == []

    def test_multiple_recipes_in_chapter(self, extractor: ExerciseExtractor) -> None:
        chapters = [
            make_chapter(
                2,
                [
                    make_block(BlockType.HEADING2, "2.1. Splitting Strings"),
                    make_block(BlockType.BODY, "Discussion about splitting."),
                    make_block(BlockType.HEADING2, "2.2. Matching Text"),
                    make_block(BlockType.BODY, "Discussion about matching."),
                    make_block(BlockType.HEADING2, "2.3. Searching and Replacing"),
                ],
            ),
        ]
        result = extractor._extract_cookbook(BOOK_ID, chapters)
        assert len(result) == 3
        assert result[0].exercise_id != result[1].exercise_id

    def test_recipe_page_num_from_block(self, extractor: ExerciseExtractor) -> None:
        chapters = [
            make_chapter(
                1,
                [
                    make_block(BlockType.HEADING2, "5.9. Serializing Objects", page_num=120),
                ],
            ),
        ]
        result = extractor._extract_cookbook(BOOK_ID, chapters)
        assert result[0].page_num == 120

    def test_description_contains_title(self, extractor: ExerciseExtractor) -> None:
        chapters = [
            make_chapter(
                1,
                [
                    make_block(BlockType.HEADING2, "3.4. Working with Decimals"),
                ],
            ),
        ]
        result = extractor._extract_cookbook(BOOK_ID, chapters)
        assert "Working with Decimals" in result[0].description


# ===========================================================================
# _extract_programming_python — explicit "Exercises" heading section
# ===========================================================================


class TestProgrammingPythonExtractor:
    """Tests for the Programming Python exercise-section strategy."""

    def test_exercises_section_heading2(self, extractor: ExerciseExtractor) -> None:
        chapters = [
            make_chapter(
                1,
                [
                    make_block(BlockType.HEADING2, "Exercises"),
                    make_block(BlockType.BODY, "1. Write a script that..."),
                    make_block(BlockType.BODY, "2. Modify the program..."),
                    make_block(BlockType.HEADING1, "Chapter 2"),
                ],
            ),
        ]
        result = extractor._extract_programming_python(BOOK_ID, chapters)
        assert len(result) == 1
        assert result[0].exercise_type == "exercise"
        assert "Write a script" in result[0].description
        assert "Modify the program" in result[0].description

    def test_exercises_section_heading3(self, extractor: ExerciseExtractor) -> None:
        chapters = [
            make_chapter(
                1,
                [
                    make_block(BlockType.HEADING3, "Exercise"),
                    make_block(BlockType.BODY, "Try this at home."),
                    make_block(BlockType.HEADING2, "Summary"),
                ],
            ),
        ]
        result = extractor._extract_programming_python(BOOK_ID, chapters)
        assert len(result) == 1

    def test_exercises_flushed_at_end_of_chapter(self, extractor: ExerciseExtractor) -> None:
        """If exercises are the last section, they should still be captured."""
        chapters = [
            make_chapter(
                7,
                [
                    make_block(BlockType.HEADING2, "Exercises"),
                    make_block(BlockType.BODY, "1. Implement a class."),
                ],
            ),
        ]
        result = extractor._extract_programming_python(BOOK_ID, chapters)
        assert len(result) == 1
        assert result[0].title == "Chapter 7 Exercises"

    def test_body_text_excluded_from_trigger(self, extractor: ExerciseExtractor) -> None:
        """The word 'Exercises' in body text should NOT start capture."""
        chapters = [
            make_chapter(
                1,
                [
                    make_block(BlockType.BODY, "The following exercises are optional."),
                    make_block(BlockType.BODY, "1. Do something."),
                ],
            ),
        ]
        result = extractor._extract_programming_python(BOOK_ID, chapters)
        assert result == []

    def test_heading1_terminates_capture(self, extractor: ExerciseExtractor) -> None:
        """A HEADING1 block should end the exercise section."""
        chapters = [
            make_chapter(
                1,
                [
                    make_block(BlockType.HEADING3, "Exercises"),
                    make_block(BlockType.BODY, "Task 1."),
                    make_block(BlockType.HEADING1, "New Chapter"),
                    make_block(BlockType.BODY, "This should not be captured."),
                ],
            ),
        ]
        result = extractor._extract_programming_python(BOOK_ID, chapters)
        assert len(result) == 1
        assert "This should not be captured" not in result[0].description

    def test_heading2_terminates_capture(self, extractor: ExerciseExtractor) -> None:
        """A HEADING2 block should also end the exercise section."""
        chapters = [
            make_chapter(
                1,
                [
                    make_block(BlockType.HEADING3, "Exercises"),
                    make_block(BlockType.BODY, "Task A."),
                    make_block(BlockType.HEADING2, "Answers"),
                    make_block(BlockType.BODY, "Answer A."),
                ],
            ),
        ]
        result = extractor._extract_programming_python(BOOK_ID, chapters)
        assert len(result) == 1
        assert "Answer A" not in result[0].description

    def test_page_num_uses_chapter_start(self, extractor: ExerciseExtractor) -> None:
        chapters = [
            make_chapter(
                3,
                [
                    make_block(BlockType.HEADING2, "Exercises"),
                    make_block(BlockType.BODY, "Do it."),
                    make_block(BlockType.HEADING1, "End"),
                ],
                start_page=200,
            ),
        ]
        result = extractor._extract_programming_python(BOOK_ID, chapters)
        assert result[0].page_num == 200


# ===========================================================================
# Edge cases
# ===========================================================================


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_chapter_with_single_block(self, extractor: ExerciseExtractor) -> None:
        """Chapter with only one content block."""
        chapters = [make_chapter(1, [make_block(BlockType.HEADING2, "Exercise 1")])]
        result = extractor.extract_from_chapters(BOOK_ID, chapters)
        assert len(result) == 1

    def test_exercise_at_end_of_chapter_last_block(self, extractor: ExerciseExtractor) -> None:
        """An exercise heading as the very last block."""
        chapters = [
            make_chapter(
                1,
                [
                    make_block(BlockType.BODY, "Some content."),
                    make_block(BlockType.HEADING3, "Problem 10"),
                ],
            ),
        ]
        result = extractor.extract_from_chapters(BOOK_ID, chapters)
        assert len(result) == 1

    def test_very_long_exercise_description(self, extractor: ExerciseExtractor) -> None:
        """A quiz with a long description should be stored without truncation."""
        long_text = "Q1: " + "x" * 5000
        chapters = [
            make_chapter(
                1,
                [
                    make_block(BlockType.HEADING2, "Test Your Knowledge: Quiz"),
                    make_block(BlockType.BODY, long_text),
                    make_block(BlockType.HEADING1, "End"),
                ],
            ),
        ]
        result = extractor._extract_learning_python(BOOK_ID, chapters)
        assert len(result) == 1
        assert len(result[0].description) > 5000

    def test_empty_content_blocks(self, extractor: ExerciseExtractor) -> None:
        """A chapter with an empty content_blocks list."""
        chapters = [make_chapter(1, [])]
        result = extractor.extract_from_chapters(BOOK_ID, chapters)
        assert result == []

    def test_whitespace_only_text_in_block(self, extractor: ExerciseExtractor) -> None:
        """Blocks with whitespace-only text should not match patterns."""
        chapters = [
            make_chapter(
                1,
                [
                    make_block(BlockType.HEADING2, "   "),
                ],
            ),
        ]
        result = extractor.extract_from_chapters(BOOK_ID, chapters)
        assert result == []

    def test_all_three_specialized_extractors_merge(self, extractor: ExerciseExtractor) -> None:
        """All specialized extractors finding results in different chapters."""
        chapters = [
            # Ch1: quiz
            make_chapter(
                1,
                [
                    make_block(BlockType.HEADING2, "Test Your Knowledge: Quiz"),
                    make_block(BlockType.BODY, "Q1"),
                    make_block(BlockType.HEADING1, "End"),
                ],
            ),
            # Ch2: recipe
            make_chapter(
                2,
                [
                    make_block(BlockType.HEADING2, "2.1. Some Recipe"),
                ],
            ),
            # Ch3: programming python exercises
            make_chapter(
                3,
                [
                    make_block(BlockType.HEADING2, "Exercises"),
                    make_block(BlockType.BODY, "Do stuff."),
                    make_block(BlockType.HEADING1, "End"),
                ],
            ),
        ]
        result = extractor.extract_from_chapters(BOOK_ID, chapters)
        types = {e.exercise_type for e in result}
        assert "quiz" in types
        assert "recipe" in types
        assert "exercise" in types
        assert len(result) == 3
