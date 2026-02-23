# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Convert parsed content blocks to styled HTML for the reader panel.

QTextBrowser uses Qt's rich text engine, NOT a real browser engine.
Supported: <h1>-<h6>, <p>, <b>, <i>, <font>, <pre>, <table>, <br>, <hr>,
           <a>, <img>, <ul>/<ol>/<li>, basic CSS in <style> blocks.
Unsupported: border-bottom, border-radius, most CSS layout, flexbox, etc.
"""

from __future__ import annotations

import html

from pylearn.core.models import BlockType, ContentBlock
from pylearn.renderer.code_highlighter import highlight_code
from pylearn.renderer.theme import ReaderTheme, get_theme


class HTMLRenderer:
    """Render ContentBlocks as styled HTML for QTextBrowser."""

    def __init__(self, theme: ReaderTheme | None = None, language: str = "python",
                 image_dir: str = "") -> None:
        self.theme = theme or get_theme()
        self.language = language
        self.image_dir = image_dir  # absolute path to image cache directory

    def render_blocks(self, blocks: list[ContentBlock]) -> str:
        """Render a list of content blocks to a full HTML document."""
        body_parts = []
        for block in blocks:
            body_parts.append(self._render_block(block))

        return self._wrap_html("\n".join(body_parts))

    def _render_block(self, block: ContentBlock) -> str:
        """Render a single content block to HTML."""
        t = self.theme
        text = block.text
        escaped = html.escape(text)
        # Use <a name=""> anchors for headings so QTextDocument can discover them
        anchor_tag = f'<a name="{html.escape(block.block_id)}"></a>' if block.block_id else ""

        if block.block_type == BlockType.HEADING1:
            return (
                f'<br>{anchor_tag}<h1><font color="{t.h1_color}" size="6">'
                f'{escaped}</font></h1><hr>'
            )

        if block.block_type == BlockType.HEADING2:
            return (
                f'<br>{anchor_tag}<h2><font color="{t.h2_color}" size="5">'
                f'{escaped}</font></h2>'
            )

        if block.block_type == BlockType.HEADING3:
            return (
                f'{anchor_tag}<h3><font color="{t.h3_color}" size="4">'
                f'{escaped}</font></h3>'
            )

        if block.block_type in (BlockType.CODE, BlockType.CODE_REPL):
            is_repl = block.block_type == BlockType.CODE_REPL
            highlighted = highlight_code(text, language=self.language, is_repl=is_repl)
            block_id = html.escape(block.block_id) if block.block_id else ""
            return (
                f'<a name="{block_id}"></a>'
                f'<table width="100%" cellpadding="8" cellspacing="0" border="0">'
                f'<tr><td bgcolor="{t.code_bg}">'
                f'<pre><font face="{t.code_font}" color="{t.code_text}">'
                f'{highlighted}</font></pre>'
                f'</td></tr></table>'
                f'<p align="right">'
                f'<a href="copy:{block_id}"><font size="2" color="{t.button_bg}">Copy</font></a>'
                f'&nbsp;&nbsp;&nbsp;'
                f'<a href="tryit:{block_id}"><font size="2" color="{t.button_bg}">Try in Editor</font></a>'
                f'</p>'
            )

        if block.block_type == BlockType.NOTE:
            return (
                f'<table width="100%" cellpadding="8" cellspacing="0" border="0">'
                f'<tr><td bgcolor="{t.note_bg}" width="4" style="background:{t.note_border};"></td>'
                f'<td bgcolor="{t.note_bg}">'
                f'<b>Note:</b> {escaped}</td></tr></table>'
            )

        if block.block_type == BlockType.WARNING:
            return (
                f'<table width="100%" cellpadding="8" cellspacing="0" border="0">'
                f'<tr><td bgcolor="{t.warning_bg}" width="4" style="background:{t.warning_border};"></td>'
                f'<td bgcolor="{t.warning_bg}">'
                f'<b>Warning:</b> {escaped}</td></tr></table>'
            )

        if block.block_type == BlockType.TIP:
            return (
                f'<table width="100%" cellpadding="8" cellspacing="0" border="0">'
                f'<tr><td bgcolor="{t.tip_bg}" width="4" style="background:{t.tip_border};"></td>'
                f'<td bgcolor="{t.tip_bg}">'
                f'<b>Tip:</b> {escaped}</td></tr></table>'
            )

        if block.block_type == BlockType.FIGURE:
            if self.image_dir:
                # Validate filename contains no path separators (prevent path traversal)
                if '..' in text or '/' in text or '\\' in text:
                    return ''  # skip suspect filename
                # text field contains the image filename — escape for HTML attribute
                safe_name = html.escape(text)
                img_path = f"{self.image_dir}/{safe_name}".replace("\\", "/")
                return (
                    f'<p align="center">'
                    f'<img src="file:///{img_path}" width="90%">'
                    f'</p>'
                )
            return ""  # no image dir configured, skip

        if block.block_type == BlockType.LIST_ITEM:
            return f'<p>&nbsp;&nbsp;&nbsp;&bull;&nbsp;{escaped}</p>'

        if block.block_type == BlockType.EXERCISE:
            return (
                f'<table width="100%" cellpadding="10" cellspacing="0" border="1"'
                f' bordercolor="{t.tip_border}">'
                f'<tr><td bgcolor="{t.tip_bg}">'
                f'<b><font color="{t.tip_border}">Exercise:</font></b><br>'
                f'{escaped}</td></tr></table>'
            )

        # Default: body text
        return f'<p>{escaped}</p>'

    def _wrap_html(self, body: str) -> str:
        """Wrap content in a full HTML document with base styles."""
        t = self.theme
        return f"""<!DOCTYPE html>
<html>
<head>
<style>
body {{
    background-color: {t.bg_color};
    color: {t.text_color};
    font-family: {t.body_font};
    font-size: {t.body_font_size}px;
    line-height: {t.line_height};
    padding: 15px 25px;
    margin: 0;
}}
h1 {{
    color: {t.h1_color};
    font-size: {t.h1_font_size}px;
    margin-top: 24px;
    margin-bottom: 8px;
}}
h2 {{
    color: {t.h2_color};
    font-size: {t.h2_font_size}px;
    margin-top: 20px;
    margin-bottom: 6px;
}}
h3 {{
    color: {t.h3_color};
    font-size: {t.h3_font_size}px;
    margin-top: 16px;
    margin-bottom: 4px;
}}
hr {{
    color: {t.h1_color};
}}
pre {{
    font-family: {t.code_font};
    font-size: {t.code_font_size}px;
    white-space: pre-wrap;
    margin: 0;
}}
a {{
    color: {t.button_bg};
}}
p {{
    margin-top: 4px;
    margin-bottom: 4px;
}}
</style>
</head>
<body>
{body}
</body>
</html>"""

    def render_welcome(self) -> str:
        """Render the welcome screen HTML."""
        t = self.theme
        return self._wrap_html(f"""
            <div style="text-align:center; margin-top:80px;">
                <h1 style="color:{t.button_bg}; font-size:36px; margin-bottom:10px;">
                    PyLearn
                </h1>
                <p style="font-size:18px; color:{t.text_color}; margin-bottom:30px;">
                    Interactive Python Learning
                </p>
                <p style="font-size:15px; color:{t.text_muted};">
                    Select a book from the library to get started,<br>
                    or add books via Book &gt; Manage Library.
                </p>
            </div>
        """)

    def update_theme(self, theme_name: str) -> None:
        """Switch the rendering theme."""
        self.theme = get_theme(theme_name)

    def update_font_size(self, size: int) -> None:
        """Update base font size."""
        self.theme.body_font_size = size
        self.theme.code_font_size = max(size - 2, 10)
        self.theme.h1_font_size = size + 12
        self.theme.h2_font_size = size + 6
        self.theme.h3_font_size = size + 2
