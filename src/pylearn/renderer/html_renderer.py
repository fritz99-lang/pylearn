"""Convert parsed content blocks to styled HTML for the reader panel."""

from __future__ import annotations

import html

from pylearn.core.models import BlockType, ContentBlock
from pylearn.renderer.code_highlighter import highlight_python
from pylearn.renderer.theme import ReaderTheme, get_theme


class HTMLRenderer:
    """Render ContentBlocks as styled HTML for QTextBrowser."""

    def __init__(self, theme: ReaderTheme | None = None) -> None:
        self.theme = theme or get_theme()

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

        if block.block_type == BlockType.HEADING1:
            return (
                f'<h1 id="{html.escape(block.block_id)}" style="color:{t.h1_color}; '
                f'font-family:{t.heading_font}; font-size:{t.h1_font_size}px; '
                f'margin-top:30px; margin-bottom:15px; border-bottom:2px solid {t.h1_color}; '
                f'padding-bottom:8px;">{html.escape(text)}</h1>'
            )

        if block.block_type == BlockType.HEADING2:
            return (
                f'<h2 id="{html.escape(block.block_id)}" style="color:{t.h2_color}; '
                f'font-family:{t.heading_font}; font-size:{t.h2_font_size}px; '
                f'margin-top:25px; margin-bottom:10px;">{html.escape(text)}</h2>'
            )

        if block.block_type == BlockType.HEADING3:
            return (
                f'<h3 id="{html.escape(block.block_id)}" style="color:{t.h3_color}; '
                f'font-family:{t.heading_font}; font-size:{t.h3_font_size}px; '
                f'margin-top:20px; margin-bottom:8px;">{html.escape(text)}</h3>'
            )

        if block.block_type in (BlockType.CODE, BlockType.CODE_REPL):
            is_repl = block.block_type == BlockType.CODE_REPL
            highlighted = highlight_python(text, is_repl=is_repl)
            block_id = html.escape(block.block_id) if block.block_id else ""
            return (
                f'<div id="{block_id}" style="margin:15px 0; position:relative;">'
                f'<div style="background:{t.code_bg}; color:{t.code_text}; '
                f'border:1px solid {t.code_border}; border-radius:6px; '
                f'padding:12px 15px; font-family:{t.code_font}; '
                f'font-size:{t.code_font_size}px; line-height:1.5; '
                f'overflow-x:auto; white-space:pre;">{highlighted}</div>'
                f'<div style="margin-top:4px; text-align:right;">'
                f'<a href="copy:{block_id}" style="color:{t.button_bg}; text-decoration:none; '
                f'font-size:12px; margin-right:12px;">Copy</a>'
                f'<a href="tryit:{block_id}" style="color:{t.button_bg}; text-decoration:none; '
                f'font-size:12px;">Try in Editor &rarr;</a>'
                f'</div></div>'
            )

        if block.block_type == BlockType.NOTE:
            return (
                f'<div style="background:{t.note_bg}; border-left:4px solid {t.note_border}; '
                f'padding:12px 15px; margin:12px 0; border-radius:0 4px 4px 0; '
                f'font-family:{t.body_font}; font-size:{t.body_font_size - 1}px;">'
                f'<strong>Note:</strong> {html.escape(text)}</div>'
            )

        if block.block_type == BlockType.WARNING:
            return (
                f'<div style="background:{t.warning_bg}; border-left:4px solid {t.warning_border}; '
                f'padding:12px 15px; margin:12px 0; border-radius:0 4px 4px 0; '
                f'font-family:{t.body_font}; font-size:{t.body_font_size - 1}px;">'
                f'<strong>Warning:</strong> {html.escape(text)}</div>'
            )

        if block.block_type == BlockType.TIP:
            return (
                f'<div style="background:{t.tip_bg}; border-left:4px solid {t.tip_border}; '
                f'padding:12px 15px; margin:12px 0; border-radius:0 4px 4px 0; '
                f'font-family:{t.body_font}; font-size:{t.body_font_size - 1}px;">'
                f'<strong>Tip:</strong> {html.escape(text)}</div>'
            )

        if block.block_type == BlockType.LIST_ITEM:
            return (
                f'<div style="font-family:{t.body_font}; font-size:{t.body_font_size}px; '
                f'color:{t.text_color}; line-height:{t.line_height}; '
                f'margin:4px 0 4px 25px; padding-left:10px; '
                f'border-left:2px solid #ddd;">{html.escape(text)}</div>'
            )

        if block.block_type == BlockType.EXERCISE:
            return (
                f'<div style="background:{t.tip_bg}; border:2px solid {t.tip_border}; '
                f'padding:15px; margin:15px 0; border-radius:6px; '
                f'font-family:{t.body_font}; font-size:{t.body_font_size}px;">'
                f'<strong style="color:{t.tip_border};">Exercise:</strong><br>'
                f'{html.escape(text)}</div>'
            )

        # Default: body text
        return (
            f'<p style="font-family:{t.body_font}; font-size:{t.body_font_size}px; '
            f'color:{t.text_color}; line-height:{t.line_height}; '
            f'margin:8px 0;">{html.escape(text)}</p>'
        )

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
    padding: 20px 30px;
    margin: 0;
    max-width: 100%;
}}
a {{ color: {t.button_bg}; }}
a:hover {{ color: {t.button_hover}; }}
::selection {{
    background: {t.button_bg};
    color: white;
}}
</style>
</head>
<body>
{body}
</body>
</html>"""

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
