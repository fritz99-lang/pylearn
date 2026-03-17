#!/usr/bin/env python3
# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Prompt templates for LLM-assisted content generation."""

from __future__ import annotations

SYSTEM_PROMPT = """\
You are an expert programming educator creating content for an interactive \
learning app called PyLearn. Users read technical books and complete quizzes, \
code challenges, and multi-step projects alongside them.

Rules:
- Output ONLY valid JSON — no markdown fences, no commentary, no explanation.
- Content must be directly based on the chapter material provided, not general knowledge.
- Write code in the language specified (Python, C++, HTML/CSS/JS, etc.).
- Ensure all code is syntactically correct and would run without errors.
"""

QUIZ_PROMPT = """\
Generate {count} quiz questions for Chapter {chapter_num}: "{chapter_title}" \
from the book "{book_title}" ({language}).

The chapter covers these topics:
{headings}

Key content:
{body_snippets}

Code examples from the chapter:
{code_examples}

Requirements:
- Mix of multiple_choice (~70%) and fill_in_blank (~30%)
- Multiple choice: exactly 4 choices, "correct" is a 0-based index (0-3)
- Multiple choice: distractors should be plausible (common misconceptions)
- Fill in blank: "correct" is a short string (1-3 words), question uses ___ for the blank
- Every question needs an "explanation" teaching WHY the answer is correct
- Every question needs "concepts" tags (lowercase, underscore_separated)
- Questions should span the chapter's topics evenly
- IDs follow the pattern: {id_prefix}_ch{chapter_num_padded}_q01, q02, etc.

Output this exact JSON structure:
{{
  "book_id": "{book_id}",
  "chapter_num": {chapter_num},
  "questions": [
    {{
      "id": "{id_prefix}_ch{chapter_num_padded}_q01",
      "type": "multiple_choice",
      "question": "What is...?",
      "choices": ["A", "B", "C", "D"],
      "correct": 1,
      "explanation": "Because...",
      "concepts": ["concept_one", "concept_two"]
    }},
    {{
      "id": "{id_prefix}_ch{chapter_num_padded}_q02",
      "type": "fill_in_blank",
      "question": "The ___ keyword is used to...",
      "correct": "keyword",
      "explanation": "Because...",
      "concepts": ["concept_one"]
    }}
  ]
}}

{example_section}
"""

CHALLENGE_PROMPT = """\
Generate {count} code challenges for Chapter {chapter_num}: "{chapter_title}" \
from the book "{book_title}" ({language}).

The chapter covers these topics:
{headings}

Key content:
{body_snippets}

Code examples from the chapter:
{code_examples}

Requirements:
- starter_code: clear comments with "# your code here" placeholders
- test_code: assert statements that verify the user's solution (run after user code)
- Each assert should have a descriptive f-string failure message
- hints: 2-3 progressive hints (first vague, last nearly the answer)
- concepts_new: concepts introduced in THIS chapter
- concepts_review: concepts from earlier chapters used here
- difficulty: {difficulty}
- IDs follow the pattern: {id_prefix}_ch{chapter_num_padded}_c01, c02, etc.

Output this exact JSON structure:
{{
  "book_id": "{book_id}",
  "chapter_num": {chapter_num},
  "challenges": [
    {{
      "id": "{id_prefix}_ch{chapter_num_padded}_c01",
      "title": "Short Title",
      "description": "Description of what to build...",
      "starter_code": "# Comment\\nvariable = # your code here\\n",
      "test_code": "assert variable == expected, f\\"Expected ..., got {{variable}}\\"",
      "difficulty": "easy",
      "concepts_new": ["concept"],
      "concepts_review": ["prior_concept"],
      "hints": ["Vague hint", "More specific", "Nearly the answer"]
    }}
  ]
}}

{example_section}
"""

PROJECT_STEP_PROMPT = """\
Generate a project step for Chapter {chapter_num}: "{chapter_title}" \
from the book "{book_title}" ({language}).

Project: "{project_title}" — {project_description}

The chapter covers these topics:
{headings}

Key content:
{body_snippets}

{previous_steps_section}

Requirements:
- This is step {step_number} of the project
- builds_on: "{builds_on}" (the previous step's step_id, empty for step 1)
- starter_code should scaffold the new feature with "# your code here" placeholders
- If this builds on a previous step, include essential code from prior steps as context
- test_code: assert statements that verify the new functionality
- acceptance_criteria: 2-4 human-readable bullet points
- hints: 2-3 progressive hints

Output this exact JSON structure:
{{
  "step_id": "{id_prefix}_proj_ch{chapter_num_padded}",
  "book_id": "{book_id}",
  "chapter_num": {chapter_num},
  "title": "Step Title — What You Build",
  "description": "What this step adds to the project...",
  "builds_on": "{builds_on}",
  "starter_code": "# Project step code\\n",
  "test_code": "assert condition, 'message'",
  "acceptance_criteria": ["Criterion 1", "Criterion 2"],
  "hints": ["Hint 1", "Hint 2"]
}}

{example_section}
"""


def format_quiz_example() -> str:
    """Return a formatted example quiz question for few-shot prompting."""
    return """\
Example from an existing Python book chapter:
{
  "id": "lp_ch01_q01",
  "type": "multiple_choice",
  "question": "What is the primary purpose of the Python interpreter?",
  "choices": [
    "To compile Python code into machine language",
    "To execute Python code line by line",
    "To convert Python to C++",
    "To check Python syntax only"
  ],
  "correct": 1,
  "explanation": "The Python interpreter reads and executes Python code line by line, making it an interpreted language rather than a compiled one.",
  "concepts": ["interpreter", "execution"]
}"""


def format_challenge_example() -> str:
    """Return a formatted example challenge for few-shot prompting."""
    return """\
Example from an existing Python book chapter:
{
  "id": "lp_ch04_c01",
  "title": "String Slicer",
  "description": "Given the string 'Learning Python', extract the word 'Python' using slicing and store it in a variable called 'word'.",
  "starter_code": "text = 'Learning Python'\\n# Extract 'Python' from text using slicing\\nword = # your code here\\n",
  "test_code": "assert word == 'Python', f\\"Expected 'Python', got '{word}'\\"",
  "difficulty": "easy",
  "concepts_new": ["slicing", "strings"],
  "concepts_review": ["variables"],
  "hints": ["Count the index where 'Python' starts (index 9)", "Use text[start:end] syntax", "text[9:] will work since Python goes to the end"]
}"""


def format_project_example() -> str:
    """Return a formatted example project step for few-shot prompting."""
    return """\
Example from an existing Python book project:
{
  "step_id": "lp_proj_ch01",
  "book_id": "learning_python_fifth_edition",
  "chapter_num": 1,
  "title": "Project Setup — Define the Data",
  "description": "Start the contact manager by creating a list of contacts. Each contact is a dictionary with 'name', 'phone', and 'email' keys.",
  "builds_on": "",
  "starter_code": "# Contact Manager — Step 1: Define the Data\\ncontacts = [\\n    # Add your contacts here\\n]\\nprint(f\\"{len(contacts)} contacts loaded\\")\\n",
  "test_code": "assert isinstance(contacts, list), 'contacts should be a list'\\nassert len(contacts) >= 3, f'Need at least 3 contacts, got {len(contacts)}'",
  "acceptance_criteria": ["contacts is a list of dictionaries", "At least 3 contacts defined", "Each contact has 'name', 'phone', and 'email' keys"],
  "hints": ["A contact looks like: {'name': 'Alice', 'phone': '555-0001', 'email': 'alice@example.com'}", "Use commas between dictionaries in the list"]
}"""
