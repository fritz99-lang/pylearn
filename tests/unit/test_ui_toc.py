"""Tests for TOCPanel — table of contents tree widget."""

from __future__ import annotations

from pylearn.core.constants import STATUS_COMPLETED, STATUS_IN_PROGRESS, STATUS_NOT_STARTED
from pylearn.core.models import Chapter, Section


class TestTOCPanel:
    def test_construction(self, qtbot):
        from pylearn.ui.toc_panel import TOCPanel

        panel = TOCPanel()
        qtbot.addWidget(panel)
        assert panel.isHeaderHidden()
        assert panel.topLevelItemCount() == 0

    def test_load_chapters(self, qtbot):
        from pylearn.ui.toc_panel import TOCPanel

        panel = TOCPanel()
        qtbot.addWidget(panel)
        chapters = [
            Chapter(chapter_num=1, title="Intro", start_page=1, end_page=20),
            Chapter(chapter_num=2, title="Basics", start_page=21, end_page=40),
        ]
        panel.load_chapters(chapters)
        assert panel.topLevelItemCount() == 2

    def test_load_chapters_with_progress(self, qtbot):
        from pylearn.ui.toc_panel import TOCPanel

        panel = TOCPanel()
        qtbot.addWidget(panel)
        chapters = [
            Chapter(chapter_num=1, title="Intro", start_page=1, end_page=20),
            Chapter(chapter_num=2, title="Basics", start_page=21, end_page=40),
            Chapter(chapter_num=3, title="Advanced", start_page=41, end_page=60),
        ]
        progress = {1: STATUS_COMPLETED, 2: STATUS_IN_PROGRESS}
        panel.load_chapters(chapters, progress)

        item1 = panel.topLevelItem(0)
        assert "[done]" in item1.text(0)
        item2 = panel.topLevelItem(1)
        assert "[>>]" in item2.text(0)
        item3 = panel.topLevelItem(2)
        assert "[  ]" in item3.text(0)

    def test_load_chapters_with_sections(self, qtbot):
        from pylearn.ui.toc_panel import TOCPanel

        panel = TOCPanel()
        qtbot.addWidget(panel)
        chapters = [
            Chapter(
                chapter_num=1,
                title="Intro",
                start_page=1,
                end_page=20,
                sections=[
                    Section(title="Getting Started", level=2, page_num=1, block_index=0),
                    Section(title="Installation", level=2, page_num=3, block_index=5),
                ],
            ),
        ]
        panel.load_chapters(chapters)
        item = panel.topLevelItem(0)
        assert item.childCount() == 2

    def test_nested_sections(self, qtbot):
        from pylearn.ui.toc_panel import TOCPanel

        panel = TOCPanel()
        qtbot.addWidget(panel)
        chapters = [
            Chapter(
                chapter_num=1,
                title="Intro",
                start_page=1,
                end_page=20,
                sections=[
                    Section(
                        title="Getting Started",
                        level=2,
                        page_num=1,
                        block_index=0,
                        children=[
                            Section(title="Sub-section", level=3, page_num=2, block_index=3),
                        ],
                    ),
                ],
            ),
        ]
        panel.load_chapters(chapters)
        item = panel.topLevelItem(0)
        section_item = item.child(0)
        assert section_item.childCount() == 1

    def test_update_chapter_status(self, qtbot):
        from pylearn.ui.toc_panel import TOCPanel

        panel = TOCPanel()
        qtbot.addWidget(panel)
        chapters = [Chapter(chapter_num=1, title="Intro", start_page=1, end_page=20)]
        panel.load_chapters(chapters)

        panel.update_chapter_status(1, STATUS_COMPLETED)
        item = panel.topLevelItem(0)
        assert "[done]" in item.text(0)

    def test_update_nonexistent_chapter_is_noop(self, qtbot):
        from pylearn.ui.toc_panel import TOCPanel

        panel = TOCPanel()
        qtbot.addWidget(panel)
        panel.load_chapters([])
        panel.update_chapter_status(999, STATUS_COMPLETED)  # should not raise

    def test_highlight_chapter(self, qtbot):
        from pylearn.ui.toc_panel import TOCPanel

        panel = TOCPanel()
        qtbot.addWidget(panel)
        chapters = [
            Chapter(chapter_num=1, title="Intro", start_page=1, end_page=20),
            Chapter(chapter_num=2, title="Basics", start_page=21, end_page=40),
        ]
        panel.load_chapters(chapters)
        panel.highlight_chapter(2)
        assert panel.currentItem() is panel.topLevelItem(1)

    def test_chapter_selected_signal(self, qtbot):
        from pylearn.ui.toc_panel import TOCPanel

        panel = TOCPanel()
        qtbot.addWidget(panel)
        chapters = [Chapter(chapter_num=1, title="Intro", start_page=1, end_page=20)]
        panel.load_chapters(chapters)

        signals = []
        panel.chapter_selected.connect(signals.append)
        item = panel.topLevelItem(0)
        panel._on_item_clicked(item, 0)
        assert signals == [1]

    def test_section_selected_signal(self, qtbot):
        from pylearn.ui.toc_panel import TOCPanel

        panel = TOCPanel()
        qtbot.addWidget(panel)
        chapters = [
            Chapter(
                chapter_num=1,
                title="Intro",
                start_page=1,
                end_page=20,
                sections=[Section(title="Setup", level=2, page_num=1, block_index=5)],
            ),
        ]
        panel.load_chapters(chapters)

        signals = []
        panel.section_selected.connect(lambda ch, bi: signals.append((ch, bi)))
        section_item = panel.topLevelItem(0).child(0)
        panel._on_item_clicked(section_item, 0)
        assert signals == [(1, 5)]

    def test_status_icon_mapping(self):
        from pylearn.ui.toc_panel import TOCPanel

        assert TOCPanel._status_icon(STATUS_COMPLETED) == "[done]"
        assert TOCPanel._status_icon(STATUS_IN_PROGRESS) == "[>>]"
        assert TOCPanel._status_icon(STATUS_NOT_STARTED) == "[  ]"
        assert TOCPanel._status_icon("unknown") == "[  ]"

    def test_long_section_title_truncated(self, qtbot):
        from pylearn.ui.toc_panel import TOCPanel

        panel = TOCPanel()
        qtbot.addWidget(panel)
        long_title = "A" * 60
        chapters = [
            Chapter(
                chapter_num=1,
                title="Ch1",
                start_page=1,
                end_page=20,
                sections=[Section(title=long_title, level=2, page_num=1, block_index=0)],
            ),
        ]
        panel.load_chapters(chapters)
        section_item = panel.topLevelItem(0).child(0)
        assert len(section_item.text(0)) <= 50

    def test_load_chapters_clears_previous(self, qtbot):
        from pylearn.ui.toc_panel import TOCPanel

        panel = TOCPanel()
        qtbot.addWidget(panel)
        chapters1 = [Chapter(chapter_num=1, title="Old", start_page=1, end_page=20)]
        panel.load_chapters(chapters1)
        assert panel.topLevelItemCount() == 1

        chapters2 = [
            Chapter(chapter_num=1, title="New1", start_page=1, end_page=20),
            Chapter(chapter_num=2, title="New2", start_page=21, end_page=40),
        ]
        panel.load_chapters(chapters2)
        assert panel.topLevelItemCount() == 2

    def test_in_progress_chapter_is_bold(self, qtbot):
        from pylearn.ui.toc_panel import TOCPanel

        panel = TOCPanel()
        qtbot.addWidget(panel)
        chapters = [Chapter(chapter_num=1, title="Intro", start_page=1, end_page=20)]
        panel.load_chapters(chapters, {1: STATUS_IN_PROGRESS})

        item = panel.topLevelItem(0)
        assert item.font(0).bold() is True

    def test_highlight_section(self, qtbot):
        from pylearn.ui.toc_panel import TOCPanel

        panel = TOCPanel()
        qtbot.addWidget(panel)
        chapters = [
            Chapter(
                chapter_num=1,
                title="Intro",
                start_page=1,
                end_page=20,
                sections=[
                    Section(title="A", level=2, page_num=1, block_index=0),
                    Section(title="B", level=2, page_num=2, block_index=10),
                ],
            ),
        ]
        panel.load_chapters(chapters)
        panel.highlight_section(1, 5)
        # Should highlight section A (block_index 0 <= 5 < 10)
        current = panel.currentItem()
        assert current is not None
        assert current.text(0) == "A"
