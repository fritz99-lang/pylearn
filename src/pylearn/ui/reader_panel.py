"""Reader panel: displays book content as styled HTML."""

from __future__ import annotations

from PyQt6.QtWidgets import QTextBrowser
from PyQt6.QtCore import pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices

from pylearn.core.models import ContentBlock
from pylearn.renderer.html_renderer import HTMLRenderer


class ReaderPanel(QTextBrowser):
    """Left panel: displays parsed book content with syntax-highlighted code blocks."""

    code_copy_requested = pyqtSignal(str)   # block_id
    code_tryit_requested = pyqtSignal(str)  # block_id

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._renderer = HTMLRenderer()
        self._current_blocks: list[ContentBlock] = []
        self._block_map: dict[str, ContentBlock] = {}

        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.anchorClicked.connect(self._handle_link)

    def display_blocks(self, blocks: list[ContentBlock]) -> None:
        """Render and display a list of content blocks."""
        self._current_blocks = blocks
        self._block_map = {b.block_id: b for b in blocks if b.block_id}
        html_content = self._renderer.render_blocks(blocks)
        self.setHtml(html_content)

    def display_html(self, html_content: str) -> None:
        """Display raw HTML content."""
        self.setHtml(html_content)

    def display_welcome(self) -> None:
        """Show a welcome message when no book is loaded."""
        html = self._renderer._wrap_html("""
            <div style="text-align:center; margin-top:80px;">
                <h1 style="color:#3498db; font-size:36px; margin-bottom:10px;">
                    PyLearn
                </h1>
                <p style="font-size:18px; color:#666; margin-bottom:30px;">
                    Interactive Python Learning
                </p>
                <p style="font-size:15px; color:#888;">
                    Select a book from the library to get started,<br>
                    or add books via Book &gt; Manage Library.
                </p>
            </div>
        """)
        self.setHtml(html)

    def get_block(self, block_id: str) -> ContentBlock | None:
        """Get a content block by its ID."""
        return self._block_map.get(block_id)

    def scroll_to_block(self, block_id: str) -> None:
        """Scroll to a specific content block."""
        self.scrollToAnchor(block_id)

    def set_theme(self, theme_name: str) -> None:
        """Update the rendering theme."""
        self._renderer.update_theme(theme_name)
        if self._current_blocks:
            self.display_blocks(self._current_blocks)

    def set_font_size(self, size: int) -> None:
        """Update the reader font size."""
        self._renderer.update_font_size(size)
        if self._current_blocks:
            pos = self.verticalScrollBar().value()
            self.display_blocks(self._current_blocks)
            self.verticalScrollBar().setValue(pos)

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
