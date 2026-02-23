# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Reader panel: displays book content as styled HTML with inline find bar."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser,
    QLineEdit, QPushButton, QLabel,
)
from PyQt6.QtCore import pyqtSignal, QUrl, QTimer, Qt
from PyQt6.QtGui import QColor, QDesktopServices, QKeySequence, QPalette, QShortcut, QTextDocument

from pylearn.core.models import ContentBlock, BlockType
from pylearn.renderer.html_renderer import HTMLRenderer


class FindBar(QWidget):
    """Inline find bar for searching within the current chapter."""

    find_next = pyqtSignal(str, bool)   # (text, case_sensitive)
    find_prev = pyqtSignal(str, bool)   # (text, case_sensitive)
    closed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setVisible(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(4)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Find in chapter...")
        self._input.setMaximumHeight(26)
        self._input.returnPressed.connect(self._on_next)
        self._input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._input, 1)

        self._status = QLabel("")
        self._status.setStyleSheet("color: #888; font-size: 11px; min-width: 60px;")
        layout.addWidget(self._status)

        prev_btn = QPushButton("<")
        prev_btn.setFixedSize(28, 26)
        prev_btn.setToolTip("Previous match (Shift+Enter)")
        prev_btn.clicked.connect(self._on_prev)
        layout.addWidget(prev_btn)

        next_btn = QPushButton(">")
        next_btn.setFixedSize(28, 26)
        next_btn.setToolTip("Next match (Enter)")
        next_btn.clicked.connect(self._on_next)
        layout.addWidget(next_btn)

        close_btn = QPushButton("x")
        close_btn.setFixedSize(28, 26)
        close_btn.setToolTip("Close (Escape)")
        close_btn.clicked.connect(self.hide_bar)
        layout.addWidget(close_btn)

    def show_bar(self) -> None:
        self.setVisible(True)
        self._input.setFocus()
        self._input.selectAll()

    def hide_bar(self) -> None:
        self.setVisible(False)
        self._status.setText("")
        self.closed.emit()

    def set_status(self, text: str) -> None:
        self._status.setText(text)

    def text(self) -> str:
        return self._input.text()

    def _on_next(self) -> None:
        text = self._input.text()
        if text:
            self.find_next.emit(text, False)

    def _on_prev(self) -> None:
        text = self._input.text()
        if text:
            self.find_prev.emit(text, False)

    def _on_text_changed(self, text: str) -> None:
        if text:
            self.find_next.emit(text, False)
        else:
            self._status.setText("")

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide_bar()
        elif event.key() == Qt.Key.Key_Return and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self._on_prev()
        else:
            super().keyPressEvent(event)


class ReaderPanel(QWidget):
    """Left panel: displays parsed book content with syntax-highlighted code blocks."""

    code_copy_requested = pyqtSignal(str)   # block_id
    code_tryit_requested = pyqtSignal(str)  # block_id
    visible_heading_changed = pyqtSignal(int)  # block_index into current chapter blocks

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._renderer = HTMLRenderer()
        self._current_blocks: list[ContentBlock] = []
        self._block_map: dict[str, ContentBlock] = {}
        self._showing_welcome: bool = False

        # Heading scroll tracking: [(doc_y_position, block_index)]
        self._heading_positions: list[tuple[float, int]] = []
        self._last_heading_index: int = -1

        # Layout: find bar on top, browser below
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._find_bar = FindBar()
        self._find_bar.find_next.connect(self._find_next)
        self._find_bar.find_prev.connect(self._find_prev)
        self._find_bar.closed.connect(self._clear_find)
        layout.addWidget(self._find_bar)

        self._browser = QTextBrowser()
        self._browser.setOpenLinks(False)
        self._browser.setOpenExternalLinks(False)
        self._browser.anchorClicked.connect(self._handle_link)
        layout.addWidget(self._browser)

        # Debounce scroll events (150ms) to avoid excessive processing
        self._scroll_timer = QTimer()
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.setInterval(150)
        self._scroll_timer.timeout.connect(self._update_visible_heading)

        self._browser.verticalScrollBar().valueChanged.connect(self._on_scroll)

        # Keyboard shortcut for Ctrl+F
        shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut.activated.connect(self.show_find_bar)

    # --- Public API (delegate to browser where needed) ---

    def verticalScrollBar(self):
        return self._browser.verticalScrollBar()

    def display_blocks(self, blocks: list[ContentBlock]) -> None:
        """Render and display a list of content blocks."""
        self._showing_welcome = False
        self._current_blocks = blocks
        self._block_map = {b.block_id: b for b in blocks if b.block_id}
        self._last_heading_index = -1
        html_content = self._renderer.render_blocks(blocks)
        self._browser.setHtml(html_content)
        # Build heading position map after layout completes
        QTimer.singleShot(0, self._build_heading_map)

    def display_html(self, html_content: str) -> None:
        """Display raw HTML content."""
        self._browser.setHtml(html_content)

    def display_welcome(self) -> None:
        """Show a welcome message when no book is loaded."""
        self._showing_welcome = True
        html = self._renderer.render_welcome()
        self._browser.setHtml(html)

    def get_block(self, block_id: str) -> ContentBlock | None:
        """Get a content block by its ID."""
        return self._block_map.get(block_id)

    def scroll_to_block(self, block_id: str) -> None:
        """Scroll to a specific content block."""
        self._browser.scrollToAnchor(block_id)

    def set_theme(self, theme_name: str) -> None:
        """Update the rendering theme."""
        self._renderer.update_theme(theme_name)
        # Set palette link color so QTextBrowser doesn't default to system blue
        from pylearn.ui.theme_registry import get_palette
        palette = self._browser.palette()
        accent = QColor(get_palette(theme_name).accent)
        palette.setColor(QPalette.ColorRole.Link, accent)
        palette.setColor(QPalette.ColorRole.LinkVisited, accent)
        self._browser.setPalette(palette)
        if self._current_blocks:
            pos = self._browser.verticalScrollBar().value()
            self.display_blocks(self._current_blocks)
            self._browser.verticalScrollBar().setValue(pos)
        elif self._showing_welcome:
            self.display_welcome()

    def set_font_size(self, size: int) -> None:
        """Update the reader font size."""
        self._renderer.update_font_size(size)
        if self._current_blocks:
            pos = self._browser.verticalScrollBar().value()
            self.display_blocks(self._current_blocks)
            self._browser.verticalScrollBar().setValue(pos)

    def set_image_dir(self, image_dir: str) -> None:
        """Set the directory containing cached images for the current book."""
        self._renderer.image_dir = image_dir

    def set_language(self, language: str) -> None:
        """Set the language for syntax highlighting in code blocks."""
        self._renderer.language = language

    # --- Find bar ---

    def show_find_bar(self) -> None:
        """Show the inline find bar."""
        self._find_bar.show_bar()

    def _find_next(self, text: str, case_sensitive: bool) -> None:
        """Find the next occurrence of text in the browser."""
        flags = QTextDocument.FindFlag(0)
        if case_sensitive:
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        found = self._browser.find(text, flags)
        if not found:
            # Wrap around: move cursor to start and try again
            cursor = self._browser.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            self._browser.setTextCursor(cursor)
            found = self._browser.find(text, flags)
        self._update_find_status(text, found)

    def _find_prev(self, text: str, case_sensitive: bool) -> None:
        """Find the previous occurrence of text in the browser."""
        flags = QTextDocument.FindFlag.FindBackward
        if case_sensitive:
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        found = self._browser.find(text, flags)
        if not found:
            # Wrap around: move cursor to end and try again
            cursor = self._browser.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self._browser.setTextCursor(cursor)
            found = self._browser.find(text, flags)
        self._update_find_status(text, found)

    def _update_find_status(self, text: str, found: bool) -> None:
        if not text:
            self._find_bar.set_status("")
        elif found:
            self._find_bar.set_status("Found")
        else:
            self._find_bar.set_status("Not found")

    def _clear_find(self) -> None:
        """Clear find highlights when the find bar is closed."""
        cursor = self._browser.textCursor()
        cursor.clearSelection()
        self._browser.setTextCursor(cursor)

    # --- Scroll-based heading tracking ---

    def _build_heading_map(self) -> None:
        """Record y-positions of heading anchors in the rendered document."""
        self._heading_positions.clear()
        doc = self._browser.document()
        layout = doc.documentLayout()

        # Map block_id -> block_index for headings
        heading_ids: dict[str, int] = {}
        for i, block in enumerate(self._current_blocks):
            if block.block_type in (BlockType.HEADING1, BlockType.HEADING2, BlockType.HEADING3):
                if block.block_id:
                    heading_ids[block.block_id] = i

        if not heading_ids:
            return

        # Iterate document fragments to find <a name="heading_N"> anchors
        text_block = doc.begin()
        while text_block.isValid():
            it = text_block.begin()
            while not it.atEnd():
                frag = it.fragment()
                if frag.isValid():
                    fmt = frag.charFormat()
                    if fmt.isAnchor():
                        for name in fmt.anchorNames():
                            if name in heading_ids:
                                rect = layout.blockBoundingRect(text_block)
                                self._heading_positions.append(
                                    (rect.y(), heading_ids[name])
                                )
                it += 1
            text_block = text_block.next()

        # Sort by y-position (should already be in order, but ensure it)
        self._heading_positions.sort(key=lambda x: x[0])

    def _on_scroll(self, _value: int) -> None:
        """Debounce scroll events."""
        self._scroll_timer.start()

    def _update_visible_heading(self) -> None:
        """Find which heading is at the top of the viewport and emit signal."""
        if not self._heading_positions:
            return

        scroll_y = self._browser.verticalScrollBar().value()

        # Find the last heading at or above the current scroll position
        current_index = -1
        for y_pos, block_index in self._heading_positions:
            if y_pos <= scroll_y + 30:  # small offset for visual alignment
                current_index = block_index
            else:
                break

        if current_index >= 0 and current_index != self._last_heading_index:
            self._last_heading_index = current_index
            self.visible_heading_changed.emit(current_index)

    # --- Link handling ---

    def _handle_link(self, url: QUrl) -> None:
        """Handle clicks on internal links (copy, try in editor)."""
        scheme = url.scheme()
        block_id = url.path() if url.path() else url.host()
        # QUrl may parse "copy:code_0" as scheme=copy, path=code_0
        # or as scheme=copy, host=code_0 depending on format

        if scheme == "copy":
            self.code_copy_requested.emit(block_id)
        elif scheme == "tryit":
            self.code_tryit_requested.emit(block_id)
        elif scheme in ("http", "https"):
            QDesktopServices.openUrl(url)
