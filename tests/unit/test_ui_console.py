"""Tests for ConsolePanel — code execution output display."""

from __future__ import annotations


class TestConsolePanel:
    def test_construction(self, qtbot):
        from pylearn.ui.console_panel import ConsolePanel

        panel = ConsolePanel()
        qtbot.addWidget(panel)
        # Should show "Ready." on construction
        assert "Ready" in panel.toHtml()

    def test_append_html(self, qtbot):
        from pylearn.ui.console_panel import ConsolePanel

        panel = ConsolePanel()
        qtbot.addWidget(panel)
        panel.append_html("<b>Output</b>")
        assert "Output" in panel.toHtml()

    def test_show_ready(self, qtbot):
        from pylearn.ui.console_panel import ConsolePanel

        panel = ConsolePanel()
        qtbot.addWidget(panel)
        panel.append_html("some output")
        panel.show_ready()
        html = panel.toHtml()
        assert "Ready" in html

    def test_show_running(self, qtbot):
        from pylearn.ui.console_panel import ConsolePanel

        panel = ConsolePanel()
        qtbot.addWidget(panel)
        panel.show_running()
        assert "Running" in panel.toHtml()

    def test_clear_console(self, qtbot):
        from pylearn.ui.console_panel import ConsolePanel

        panel = ConsolePanel()
        qtbot.addWidget(panel)
        panel.append_html("lots of output")
        panel.clear_console()
        html = panel.toHtml()
        # After clear, should show "Ready." again
        assert "Ready" in html

    def test_set_theme_dark(self, qtbot):
        from pylearn.ui.console_panel import ConsolePanel

        panel = ConsolePanel()
        qtbot.addWidget(panel)
        panel.set_theme("dark")
        assert panel._palette.name == "dark"

    def test_set_theme_sepia(self, qtbot):
        from pylearn.ui.console_panel import ConsolePanel

        panel = ConsolePanel()
        qtbot.addWidget(panel)
        panel.set_theme("sepia")
        assert panel._palette.name == "sepia"

    def test_set_theme_applies_stylesheet(self, qtbot):
        from pylearn.ui.console_panel import ConsolePanel

        panel = ConsolePanel()
        qtbot.addWidget(panel)
        panel.set_theme("dark")
        ss = panel.styleSheet()
        assert "background-color" in ss
