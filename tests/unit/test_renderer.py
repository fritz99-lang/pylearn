# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Comprehensive unit tests for HTMLRenderer.

Tests cover all BlockType rendering, HTML escaping, code block actions,
figure path traversal rejection, welcome screen, font size scaling,
empty/mixed block rendering, and theme variations.
"""

from __future__ import annotations

import html

import pytest

from pylearn.core.models import BlockType, ContentBlock
from pylearn.renderer.html_renderer import HTMLRenderer
from pylearn.renderer.theme import get_theme

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def renderer() -> HTMLRenderer:
    """Default renderer with light theme."""
    return HTMLRenderer(theme=get_theme("light"), language="python")


@pytest.fixture
def renderer_with_images(tmp_path: object) -> HTMLRenderer:
    """Renderer configured with an image directory."""
    return HTMLRenderer(
        theme=get_theme("light"),
        language="python",
        image_dir=str(tmp_path),
    )


def _make_block(
    block_type: BlockType,
    text: str = "test content",
    block_id: str = "",
) -> ContentBlock:
    """Helper to build a ContentBlock with minimal boilerplate."""
    return ContentBlock(block_type=block_type, text=text, block_id=block_id)


# ---------------------------------------------------------------------------
# Individual BlockType rendering
# ---------------------------------------------------------------------------


class TestBodyRendering:
    def test_body_produces_paragraph(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.BODY, "Hello world")
        result = renderer._render_block(block)
        assert "<p>" in result
        assert "Hello world" in result
        assert "</p>" in result

    def test_body_escapes_html(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.BODY, "<b>bold</b>")
        result = renderer._render_block(block)
        assert "&lt;b&gt;bold&lt;/b&gt;" in result
        assert "<b>bold</b>" not in result


class TestHeadingRendering:
    def test_heading1_has_h1_tag(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.HEADING1, "Chapter Title")
        result = renderer._render_block(block)
        assert "<h1>" in result
        assert "</h1>" in result
        assert "<hr>" in result
        assert "Chapter Title" in result

    def test_heading1_uses_theme_color(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.HEADING1, "Title")
        result = renderer._render_block(block)
        assert renderer.theme.h1_color in result

    def test_heading2_has_h2_tag(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.HEADING2, "Section Title")
        result = renderer._render_block(block)
        assert "<h2>" in result
        assert "</h2>" in result
        assert "Section Title" in result

    def test_heading2_uses_theme_color(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.HEADING2, "Title")
        result = renderer._render_block(block)
        assert renderer.theme.h2_color in result

    def test_heading3_has_h3_tag(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.HEADING3, "Subsection")
        result = renderer._render_block(block)
        assert "<h3>" in result
        assert "</h3>" in result
        assert "Subsection" in result

    def test_heading3_uses_theme_color(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.HEADING3, "Title")
        result = renderer._render_block(block)
        assert renderer.theme.h3_color in result

    def test_heading_with_block_id_has_anchor(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.HEADING1, "Title", block_id="ch1_s1")
        result = renderer._render_block(block)
        assert '<a name="ch1_s1">' in result

    def test_heading_escapes_text(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.HEADING1, "A & B <C>")
        result = renderer._render_block(block)
        assert "A &amp; B &lt;C&gt;" in result


class TestCodeBlockRendering:
    def test_code_has_pre_and_table(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.CODE, "x = 1", block_id="code_0")
        result = renderer._render_block(block)
        assert "<pre>" in result
        assert "<table" in result
        assert renderer.theme.code_bg in result

    def test_code_has_copy_link(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.CODE, "x = 1", block_id="code_0")
        result = renderer._render_block(block)
        assert 'href="copy:code_0"' in result
        assert "Copy" in result

    def test_code_has_tryit_link(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.CODE, "x = 1", block_id="code_0")
        result = renderer._render_block(block)
        assert 'href="tryit:code_0"' in result
        assert "Try in Editor" in result

    def test_code_repl_renders_similarly(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.CODE_REPL, ">>> print(1)", block_id="repl_0")
        result = renderer._render_block(block)
        assert "<pre>" in result
        assert 'href="copy:repl_0"' in result

    def test_code_uses_theme_font(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.CODE, "pass", block_id="c1")
        result = renderer._render_block(block)
        assert renderer.theme.code_font in result

    def test_code_block_id_is_escaped(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.CODE, "pass", block_id='"><script>')
        result = renderer._render_block(block)
        assert '"><script>' not in result
        assert html.escape('"><script>') in result


class TestCalloutRendering:
    def test_note_has_label_and_bg(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.NOTE, "Remember this.")
        result = renderer._render_block(block)
        assert "<b>Note:</b>" in result
        assert renderer.theme.note_bg in result
        assert "Remember this." in result

    def test_warning_has_label_and_bg(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.WARNING, "Be careful.")
        result = renderer._render_block(block)
        assert "<b>Warning:</b>" in result
        assert renderer.theme.warning_bg in result
        assert "Be careful." in result

    def test_tip_has_label_and_bg(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.TIP, "Try this shortcut.")
        result = renderer._render_block(block)
        assert "<b>Tip:</b>" in result
        assert renderer.theme.tip_bg in result
        assert "Try this shortcut." in result

    def test_note_escapes_html(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.NOTE, "<script>alert('xss')</script>")
        result = renderer._render_block(block)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


class TestExerciseRendering:
    def test_exercise_has_label_and_border(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.EXERCISE, "Write a function.")
        result = renderer._render_block(block)
        assert "Exercise:" in result
        assert renderer.theme.tip_border in result
        assert "Write a function." in result

    def test_exercise_escapes_html(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.EXERCISE, "x < y && z > 0")
        result = renderer._render_block(block)
        assert "x &lt; y &amp;&amp; z &gt; 0" in result


class TestListItemRendering:
    def test_list_item_has_bullet(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.LIST_ITEM, "Item one")
        result = renderer._render_block(block)
        assert "&bull;" in result
        assert "Item one" in result
        assert "<p>" in result


class TestFigureRendering:
    def test_figure_with_image_dir(self, renderer_with_images: HTMLRenderer) -> None:
        block = _make_block(BlockType.FIGURE, "diagram.png")
        result = renderer_with_images._render_block(block)
        assert "<img" in result
        assert "diagram.png" in result
        assert 'width="90%"' in result

    def test_figure_without_image_dir(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.FIGURE, "diagram.png")
        result = renderer._render_block(block)
        assert result == ""

    def test_figure_rejects_path_traversal_dotdot(self, renderer_with_images: HTMLRenderer) -> None:
        block = _make_block(BlockType.FIGURE, "../../etc/passwd")
        result = renderer_with_images._render_block(block)
        assert result == ""

    def test_figure_rejects_forward_slash(self, renderer_with_images: HTMLRenderer) -> None:
        block = _make_block(BlockType.FIGURE, "images/hidden.png")
        result = renderer_with_images._render_block(block)
        assert result == ""

    def test_figure_rejects_backslash(self, renderer_with_images: HTMLRenderer) -> None:
        block = _make_block(BlockType.FIGURE, r"images\hidden.png")
        result = renderer_with_images._render_block(block)
        assert result == ""


class TestDefaultFallback:
    """Block types not handled by explicit branches fall through to <p> body."""

    def test_table_renders_as_body(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.TABLE, "col1 | col2")
        result = renderer._render_block(block)
        assert "<p>" in result
        assert "col1 | col2" in result

    def test_page_header_renders_as_body(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.PAGE_HEADER, "Page Header")
        result = renderer._render_block(block)
        assert "<p>" in result

    def test_page_footer_renders_as_body(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.PAGE_FOOTER, "Page Footer")
        result = renderer._render_block(block)
        assert "<p>" in result


# ---------------------------------------------------------------------------
# HTML escaping / XSS prevention
# ---------------------------------------------------------------------------


class TestHTMLEscaping:
    def test_script_tag_escaped_in_body(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.BODY, "<script>alert('xss')</script>")
        result = renderer._render_block(block)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_ampersand_escaped(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.BODY, "AT&T")
        result = renderer._render_block(block)
        assert "AT&amp;T" in result

    def test_angle_brackets_escaped(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.BODY, "a < b > c")
        result = renderer._render_block(block)
        assert "a &lt; b &gt; c" in result

    def test_script_in_heading_escaped(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.HEADING2, "<script>document.cookie</script>")
        result = renderer._render_block(block)
        assert "<script>" not in result

    def test_img_tag_in_note_escaped(self, renderer: HTMLRenderer) -> None:
        block = _make_block(BlockType.NOTE, "<img onerror=alert(1) src=x>")
        result = renderer._render_block(block)
        # The < and > must be escaped so the tag is not rendered as HTML
        assert "<img " not in result
        assert "&lt;img" in result
        assert "src=x&gt;" in result


# ---------------------------------------------------------------------------
# render_blocks (full document)
# ---------------------------------------------------------------------------


class TestRenderBlocks:
    def test_empty_list_returns_valid_html(self, renderer: HTMLRenderer) -> None:
        result = renderer.render_blocks([])
        assert "<!DOCTYPE html>" in result
        assert "<html>" in result
        assert "<body>" in result
        assert "</body>" in result

    def test_single_block(self, renderer: HTMLRenderer) -> None:
        blocks = [_make_block(BlockType.BODY, "Hello")]
        result = renderer.render_blocks(blocks)
        assert "Hello" in result
        assert "<p>" in result

    def test_mixed_block_types(self, renderer: HTMLRenderer) -> None:
        blocks = [
            _make_block(BlockType.HEADING1, "Title"),
            _make_block(BlockType.BODY, "Paragraph text."),
            _make_block(BlockType.CODE, "x = 1", block_id="code_0"),
            _make_block(BlockType.NOTE, "Take note."),
            _make_block(BlockType.LIST_ITEM, "Bullet point"),
        ]
        result = renderer.render_blocks(blocks)
        assert "<h1>" in result
        assert "Paragraph text." in result
        assert "<pre>" in result
        assert "<b>Note:</b>" in result
        assert "&bull;" in result

    def test_render_blocks_contains_css(self, renderer: HTMLRenderer) -> None:
        result = renderer.render_blocks([])
        assert "<style>" in result
        assert "font-family" in result


# ---------------------------------------------------------------------------
# render_welcome
# ---------------------------------------------------------------------------


class TestRenderWelcome:
    def test_welcome_returns_nonempty(self, renderer: HTMLRenderer) -> None:
        result = renderer.render_welcome()
        assert len(result) > 0

    def test_welcome_contains_pylearn(self, renderer: HTMLRenderer) -> None:
        result = renderer.render_welcome()
        assert "PyLearn" in result

    def test_welcome_is_full_html_doc(self, renderer: HTMLRenderer) -> None:
        result = renderer.render_welcome()
        assert "<!DOCTYPE html>" in result
        assert "<body>" in result


# ---------------------------------------------------------------------------
# update_font_size
# ---------------------------------------------------------------------------


class TestUpdateFontSize:
    def test_body_size_updated(self, renderer: HTMLRenderer) -> None:
        renderer.update_font_size(20)
        assert renderer.theme.body_font_size == 20

    def test_code_size_is_body_minus_two(self, renderer: HTMLRenderer) -> None:
        renderer.update_font_size(20)
        assert renderer.theme.code_font_size == 18

    def test_code_size_minimum_is_ten(self, renderer: HTMLRenderer) -> None:
        renderer.update_font_size(10)
        assert renderer.theme.code_font_size == 10

    def test_h1_scales_correctly(self, renderer: HTMLRenderer) -> None:
        renderer.update_font_size(18)
        assert renderer.theme.h1_font_size == 30  # 18 + 12

    def test_h2_scales_correctly(self, renderer: HTMLRenderer) -> None:
        renderer.update_font_size(18)
        assert renderer.theme.h2_font_size == 24  # 18 + 6

    def test_h3_scales_correctly(self, renderer: HTMLRenderer) -> None:
        renderer.update_font_size(18)
        assert renderer.theme.h3_font_size == 20  # 18 + 2


# ---------------------------------------------------------------------------
# Theme variations
# ---------------------------------------------------------------------------


class TestThemeVariations:
    @pytest.mark.parametrize("theme_name", ["light", "dark", "sepia"])
    def test_render_body_with_each_theme(self, theme_name: str) -> None:
        r = HTMLRenderer(theme=get_theme(theme_name))
        block = _make_block(BlockType.BODY, "Themed text")
        result = r.render_blocks([block])
        assert "Themed text" in result
        assert r.theme.bg_color in result

    def test_dark_and_light_have_different_bg(self) -> None:
        light = HTMLRenderer(theme=get_theme("light"))
        dark = HTMLRenderer(theme=get_theme("dark"))
        assert light.theme.bg_color != dark.theme.bg_color

    def test_sepia_and_light_have_different_bg(self) -> None:
        sepia = HTMLRenderer(theme=get_theme("sepia"))
        light = HTMLRenderer(theme=get_theme("light"))
        assert sepia.theme.bg_color != light.theme.bg_color

    @pytest.mark.parametrize("theme_name", ["light", "dark", "sepia"])
    def test_code_block_uses_theme_code_bg(self, theme_name: str) -> None:
        r = HTMLRenderer(theme=get_theme(theme_name))
        block = _make_block(BlockType.CODE, "pass", block_id="c1")
        result = r._render_block(block)
        assert r.theme.code_bg in result

    @pytest.mark.parametrize("theme_name", ["light", "dark", "sepia"])
    def test_note_uses_theme_colors(self, theme_name: str) -> None:
        r = HTMLRenderer(theme=get_theme(theme_name))
        block = _make_block(BlockType.NOTE, "themed note")
        result = r._render_block(block)
        assert r.theme.note_bg in result

    def test_update_theme_switches_colors(self) -> None:
        r = HTMLRenderer(theme=get_theme("light"))
        old_bg = r.theme.bg_color
        r.update_theme("dark")
        assert r.theme.bg_color != old_bg
