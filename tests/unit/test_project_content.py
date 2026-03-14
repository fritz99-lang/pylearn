# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Validate all Contact Manager project content files.

Tests real content in content/learning_python_fifth_edition/project/.
Checks structural validity, builds_on chain, and that test_code passes
with correct solutions.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from pylearn.core.content_loader import ContentLoader

BOOK_ID = "learning_python_fifth_edition"
CONTENT_DIR = Path(__file__).resolve().parents[2] / "content"
EXPECTED_CHAPTERS = [1, 4, 5, 7, 8, 9, 11, 12, 13, 14]

# Correct solutions for each step — used to verify test_code assertions work.
SOLUTIONS: dict[int, str] = {
    1: textwrap.dedent("""\
        contacts = [
            {'name': 'Alice', 'phone': '555-0001', 'email': 'alice@example.com'},
            {'name': 'Bob', 'phone': '555-0002', 'email': 'bob@example.com'},
            {'name': 'Charlie', 'phone': '555-0003', 'email': 'charlie@example.com'},
        ]
    """),
    4: textwrap.dedent("""\
        contacts = [
            {'name': 'Alice', 'phone': '555-0001', 'email': 'alice@example.com'},
            {'name': 'Bob', 'phone': '555-0002', 'email': 'bob@example.com'},
            {'name': 'Charlie', 'phone': '555-0003', 'email': 'charlie@example.com'},
        ]

        def display_contacts(contact_list):
            for c in contact_list:
                print(f"  {c['name']} | {c['phone']} | {c['email']}")

        def find_contact(contact_list, search_name):
            return [c for c in contact_list if search_name.lower() in c['name'].lower()]
    """),
    5: textwrap.dedent("""\
        contacts = [
            {'name': 'Alice', 'phone': '555-0001', 'email': 'alice@example.com'},
            {'name': 'Bob', 'phone': '555-0002', 'email': 'bob@example.com'},
            {'name': 'Charlie', 'phone': '555-0003', 'email': 'charlie@example.com'},
        ]

        def add_contact(contact_list, name, phone, email):
            contact_list.append({'name': name, 'phone': phone, 'email': email})

        def remove_contact(contact_list, name):
            for c in contact_list:
                if c['name'].lower() == name.lower():
                    contact_list.remove(c)
                    return True
            return False
    """),
    7: textwrap.dedent("""\
        def format_contact(contact):
            return f"{contact['name'].ljust(15)}{contact['phone'].ljust(15)}{contact['email']}"

        def validate_email(email):
            if email.count('@') != 1:
                return False
            parts = email.split('@')
            return len(parts[0]) > 0 and len(parts[1]) > 0
    """),
    8: textwrap.dedent("""\
        contacts = [
            {'name': 'Charlie', 'phone': '555-0003', 'email': 'charlie@example.com'},
            {'name': 'Alice', 'phone': '555-0001', 'email': 'alice@example.com'},
            {'name': 'Bob', 'phone': '555-0002', 'email': 'bob@example.com'},
        ]

        def sort_contacts(contact_list, field='name'):
            return sorted(contact_list, key=lambda c: c[field].lower())

        def search_contacts(contact_list, query):
            return [c for c in contact_list if any(query.lower() in v.lower() for v in c.values())]
    """),
    9: textwrap.dedent("""\
        import os

        def save_contacts(contact_list, filename):
            with open(filename, 'w') as f:
                for c in contact_list:
                    f.write(f"{c['name']}|{c['phone']}|{c['email']}\\n")

        def load_contacts(filename):
            try:
                with open(filename, 'r') as f:
                    contacts = []
                    for line in f:
                        parts = line.strip().split('|')
                        if len(parts) == 3:
                            contacts.append({'name': parts[0], 'phone': parts[1], 'email': parts[2]})
                    return contacts
            except FileNotFoundError:
                return []
    """),
    11: textwrap.dedent("""\
        contacts = [
            {'name': 'Alice', 'phone': '555-0001', 'email': 'alice@example.com'},
            {'name': 'Bob', 'phone': '555-0002', 'email': 'bob@example.com'},
        ]

        def update_contact(contact_list, contact_name, **updates):
            valid_fields = {'name', 'phone', 'email'}
            filtered = {k: v for k, v in updates.items() if k in valid_fields}
            for c in contact_list:
                if c['name'].lower() == contact_name.lower():
                    c.update(filtered)
                    return True
            return False
    """),
    12: textwrap.dedent("""\
        contacts = [
            {'name': 'Alice', 'phone': '555-0001', 'email': 'alice@example.com'},
        ]

        def show_menu():
            return "1. View all contacts\\n2. Search contacts\\n3. Add contact\\n4. Remove contact\\n5. Quit"

        def handle_choice(choice, contact_list):
            if choice == '1':
                return 'view'
            elif choice == '2':
                return 'search'
            elif choice == '3':
                return 'add'
            elif choice == '4':
                return 'remove'
            elif choice == '5':
                return 'quit'
            else:
                return 'invalid'
    """),
    13: textwrap.dedent("""\
        contacts = [
            {'name': 'Alice', 'phone': '555-0001', 'email': 'alice@example.com'},
            {'name': 'Bob', 'phone': '555-0002', 'email': 'bob@example.com'},
            {'name': 'Charlie', 'phone': '555-0003', 'email': 'charlie@example.com'},
        ]

        def show_menu():
            return "1. View\\n2. Search\\n3. Add\\n4. Remove\\n5. Quit"

        def run_app(contact_list, inputs=None):
            actions = []
            input_index = 0

            def get_input(prompt=''):
                nonlocal input_index
                if inputs is not None:
                    if input_index < len(inputs):
                        val = inputs[input_index]
                        input_index += 1
                        return val
                    return '5'
                return input(prompt)

            while True:
                show_menu()
                choice = get_input()
                if choice == '1':
                    actions.append('view')
                elif choice == '2':
                    actions.append('search')
                elif choice == '3':
                    actions.append('add')
                elif choice == '4':
                    actions.append('remove')
                elif choice == '5':
                    actions.append('quit')
                    break
                else:
                    actions.append('invalid')
            return actions
    """),
    14: textwrap.dedent("""\
        contacts = [
            {'name': 'Alice', 'phone': '555-0001', 'email': 'alice@example.com'},
            {'name': 'Bob', 'phone': '555-0002', 'email': 'bob@example.com'},
            {'name': 'Charlie', 'phone': '555-0003', 'email': 'charlie@work.org'},
        ]

        def contact_stats(contact_list):
            if not contact_list:
                return {'total': 0, 'domains': 0, 'avg_name_length': 0.0, 'longest_name': ''}
            domains = {c['email'].split('@')[1] for c in contact_list}
            avg = sum(len(c['name']) for c in contact_list) / len(contact_list)
            longest = max(contact_list, key=lambda c: len(c['name']))['name']
            return {
                'total': len(contact_list),
                'domains': len(domains),
                'avg_name_length': float(avg),
                'longest_name': longest,
            }

        def group_by_domain(contact_list):
            groups = {}
            for c in contact_list:
                domain = c['email'].split('@')[1]
                if domain not in groups:
                    groups[domain] = []
                groups[domain].append(c['name'])
            return groups
    """),
}


@pytest.fixture(scope="module")
def loader() -> ContentLoader:
    return ContentLoader(CONTENT_DIR)


class TestProjectContentStructure:
    """Validate structure of all project content files."""

    def test_all_expected_steps_exist(self, loader: ContentLoader) -> None:
        steps = loader.list_project_steps(BOOK_ID)
        assert steps == EXPECTED_CHAPTERS

    def test_project_meta_loads(self, loader: ContentLoader) -> None:
        meta = loader.load_project_meta(BOOK_ID)
        assert meta is not None
        assert meta.title == "Build a Personal Contact Manager"

    @pytest.mark.parametrize("chapter", EXPECTED_CHAPTERS)
    def test_step_loads(self, loader: ContentLoader, chapter: int) -> None:
        step = loader.load_project_step(BOOK_ID, chapter)
        assert step is not None
        assert step.chapter_num == chapter
        assert step.step_id == f"lp_proj_ch{chapter:02d}"
        assert step.book_id == BOOK_ID

    @pytest.mark.parametrize("chapter", EXPECTED_CHAPTERS)
    def test_step_has_required_content(self, loader: ContentLoader, chapter: int) -> None:
        step = loader.load_project_step(BOOK_ID, chapter)
        assert step is not None
        assert len(step.title) > 0, f"Ch {chapter}: title is empty"
        assert len(step.description) > 0, f"Ch {chapter}: description is empty"
        assert len(step.starter_code) > 0, f"Ch {chapter}: starter_code is empty"
        assert len(step.test_code) > 0, f"Ch {chapter}: test_code is empty"
        assert len(step.acceptance_criteria) >= 2, f"Ch {chapter}: need at least 2 criteria"
        assert len(step.hints) >= 2, f"Ch {chapter}: need at least 2 hints"

    def test_builds_on_chain_is_valid(self, loader: ContentLoader) -> None:
        """Verify the builds_on references form a valid chain."""
        step_ids = {}
        for ch in EXPECTED_CHAPTERS:
            step = loader.load_project_step(BOOK_ID, ch)
            assert step is not None
            step_ids[step.step_id] = ch

        for ch in EXPECTED_CHAPTERS:
            step = loader.load_project_step(BOOK_ID, ch)
            assert step is not None
            if step.builds_on:
                assert step.builds_on in step_ids, f"Ch {ch}: builds_on '{step.builds_on}' not found in steps"
                assert step_ids[step.builds_on] < ch, f"Ch {ch}: builds_on points to a later chapter"

    def test_first_step_has_no_builds_on(self, loader: ContentLoader) -> None:
        step = loader.load_project_step(BOOK_ID, EXPECTED_CHAPTERS[0])
        assert step is not None
        assert step.builds_on == ""

    def test_all_non_first_steps_have_builds_on(self, loader: ContentLoader) -> None:
        for ch in EXPECTED_CHAPTERS[1:]:
            step = loader.load_project_step(BOOK_ID, ch)
            assert step is not None
            assert step.builds_on != "", f"Ch {ch}: should have builds_on set"


class TestProjectTestCodeExecution:
    """Verify that test_code assertions pass with correct solutions."""

    @pytest.mark.parametrize("chapter", EXPECTED_CHAPTERS)
    def test_solution_passes(self, loader: ContentLoader, chapter: int) -> None:
        step = loader.load_project_step(BOOK_ID, chapter)
        assert step is not None
        assert chapter in SOLUTIONS, f"No solution provided for ch {chapter}"

        # Combine solution + test code
        code = SOLUTIONS[chapter] + "\n" + step.test_code
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (
            f"Ch {chapter} solution failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )
