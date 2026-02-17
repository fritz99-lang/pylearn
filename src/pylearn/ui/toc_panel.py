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
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

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
            item.setData(0, Qt.ItemDataRole.UserRole + 1, {
                "status": status,
                "chapter_num": chapter.chapter_num,
                "title": chapter.title,
            })

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
            # Read stored metadata and rebuild text cleanly
            meta = item.data(0, Qt.ItemDataRole.UserRole + 1) or {}
            meta["status"] = status
            item.setData(0, Qt.ItemDataRole.UserRole + 1, meta)

            icon = self._status_icon(status)
            title = meta.get("title", "")
            ch_num = meta.get("chapter_num", chapter_num)
            item.setText(0, f"{icon} Ch {ch_num}: {title}")

            font = item.font(0)
            font.setBold(status == "in_progress")
            item.setFont(0, font)

    def highlight_chapter(self, chapter_num: int) -> None:
        """Highlight the current chapter in the tree."""
        item = self._chapter_items.get(chapter_num)
        if item:
            self.setCurrentItem(item)
            self.scrollToItem(item)
            item.setExpanded(True)

    def highlight_section(self, chapter_num: int, block_index: int) -> None:
        """Highlight the section closest to block_index as the user scrolls.

        Finds the section item with the largest block_index <= the given index,
        i.e. the section the reader is currently inside.
        """
        chapter_item = self._chapter_items.get(chapter_num)
        if not chapter_item:
            return

        best_item: QTreeWidgetItem | None = None

        def _search(parent: QTreeWidgetItem) -> None:
            nonlocal best_item
            for i in range(parent.childCount()):
                child = parent.child(i)
                data = child.data(0, Qt.ItemDataRole.UserRole)
                if data and data[0] == "section":
                    if data[2] <= block_index:
                        best_item = child
                        _search(child)

        _search(chapter_item)

        target = best_item or chapter_item
        if target != self.currentItem():
            # Avoid triggering navigation signals — this is just visual tracking
            self.blockSignals(True)
            self.setCurrentItem(target)
            self.scrollToItem(target)
            self.blockSignals(False)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle tree item single-clicks — navigate to chapters and sections."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data[0] == "chapter":
            self.chapter_selected.emit(data[1])
        elif data[0] == "section":
            self.section_selected.emit(data[1], data[2])

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle tree item double-clicks — scroll to sections."""
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
