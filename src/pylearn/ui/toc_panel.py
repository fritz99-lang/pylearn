"""Table of contents tree panel."""

from __future__ import annotations

from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

from pylearn.core.models import Chapter, Section, ReadStatus


class TOCPanel(QTreeWidget):
    """Collapsible table of contents tree for book navigation."""

    chapter_selected = pyqtSignal(int)   # chapter_num
    section_selected = pyqtSignal(int, int)  # chapter_num, block_index

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setIndentation(16)
        self.setAnimated(True)
        self.setMinimumWidth(180)
        self.itemClicked.connect(self._on_item_clicked)

        self._chapter_items: dict[int, QTreeWidgetItem] = {}

    def load_chapters(self, chapters: list[Chapter],
                      progress: dict[int, str] | None = None) -> None:
        """Populate the TOC tree from chapter data."""
        self.clear()
        self._chapter_items.clear()
        progress = progress or {}

        for chapter in chapters:
            status = progress.get(chapter.chapter_num, "not_started")
            icon = self._status_icon(status)

            item = QTreeWidgetItem(self)
            item.setText(0, f"{icon} Ch {chapter.chapter_num}: {chapter.title}")
            item.setData(0, Qt.ItemDataRole.UserRole, ("chapter", chapter.chapter_num))

            font = item.font(0)
            if status == "in_progress":
                font.setBold(True)
            item.setFont(0, font)

            self._chapter_items[chapter.chapter_num] = item

            # Add sections
            for section in chapter.sections:
                self._add_section_item(item, section, chapter.chapter_num)

    def _add_section_item(self, parent: QTreeWidgetItem, section: Section,
                          chapter_num: int) -> None:
        """Add a section (and its children) to the tree."""
        item = QTreeWidgetItem(parent)

        # Truncate long titles
        title = section.title
        if len(title) > 50:
            title = title[:47] + "..."
        item.setText(0, title)
        item.setData(0, Qt.ItemDataRole.UserRole,
                     ("section", chapter_num, section.block_index))

        for child in section.children:
            self._add_section_item(item, child, chapter_num)

    def update_chapter_status(self, chapter_num: int, status: str) -> None:
        """Update the icon/style for a chapter."""
        item = self._chapter_items.get(chapter_num)
        if item:
            icon = self._status_icon(status)
            text = item.text(0)
            # Replace the icon prefix
            parts = text.split(" ", 1)
            if len(parts) > 1:
                item.setText(0, f"{icon} {parts[1]}")
            font = item.font(0)
            font.setBold(status == "in_progress")
            item.setFont(0, font)

    def highlight_chapter(self, chapter_num: int) -> None:
        """Highlight the current chapter in the tree."""
        item = self._chapter_items.get(chapter_num)
        if item:
            self.setCurrentItem(item)
            self.scrollToItem(item)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle tree item clicks."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data[0] == "chapter":
            self.chapter_selected.emit(data[1])
        elif data[0] == "section":
            self.section_selected.emit(data[1], data[2])

    @staticmethod
    def _status_icon(status: str) -> str:
        if status == "completed":
            return "[done]"
        elif status == "in_progress":
            return "[>>]"
        return "[  ]"
