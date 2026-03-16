"""Tests for MainToolBar — run/stop/font/theme controls."""

from __future__ import annotations

# ===========================================================================
# MainToolBar
# ===========================================================================


class TestMainToolBar:
    def test_construction(self, qtbot):
        from pylearn.ui.toolbar import MainToolBar

        toolbar = MainToolBar()
        qtbot.addWidget(toolbar)
        assert toolbar.isMovable() is False

    def test_set_running_true(self, qtbot):
        from pylearn.ui.toolbar import MainToolBar

        toolbar = MainToolBar()
        qtbot.addWidget(toolbar)
        toolbar.set_running(True)
        assert toolbar._run_action.isEnabled() is False
        assert toolbar._stop_action.isEnabled() is True

    def test_set_running_false(self, qtbot):
        from pylearn.ui.toolbar import MainToolBar

        toolbar = MainToolBar()
        qtbot.addWidget(toolbar)
        toolbar.set_running(False)
        assert toolbar._run_action.isEnabled() is True
        assert toolbar._stop_action.isEnabled() is False

    def test_set_font_size(self, qtbot):
        from pylearn.ui.toolbar import MainToolBar

        toolbar = MainToolBar()
        qtbot.addWidget(toolbar)
        toolbar.set_font_size(16)
        assert toolbar._font_spin.value() == 16

    def test_set_font_size_no_signal(self, qtbot):
        """set_font_size should block signals to avoid feedback loops."""
        from pylearn.ui.toolbar import MainToolBar

        toolbar = MainToolBar()
        qtbot.addWidget(toolbar)
        signals = []
        toolbar.font_size_changed.connect(signals.append)
        toolbar.set_font_size(18)
        assert signals == []

    def test_set_theme(self, qtbot):
        from pylearn.ui.toolbar import MainToolBar

        toolbar = MainToolBar()
        qtbot.addWidget(toolbar)
        toolbar.set_theme("dark")
        assert toolbar._theme_combo.currentText() == "Dark"

    def test_set_theme_no_signal(self, qtbot):
        """set_theme should block signals to avoid feedback loops."""
        from pylearn.ui.toolbar import MainToolBar

        toolbar = MainToolBar()
        qtbot.addWidget(toolbar)
        signals = []
        toolbar.theme_changed.connect(signals.append)
        toolbar.set_theme("sepia")
        assert signals == []

    def test_run_signal(self, qtbot):
        from pylearn.ui.toolbar import MainToolBar

        toolbar = MainToolBar()
        qtbot.addWidget(toolbar)
        signals = []
        toolbar.run_requested.connect(lambda: signals.append("run"))
        toolbar._run_action.trigger()
        assert signals == ["run"]

    def test_stop_signal(self, qtbot):
        from pylearn.ui.toolbar import MainToolBar

        toolbar = MainToolBar()
        qtbot.addWidget(toolbar)
        toolbar.set_running(True)  # enable stop button
        signals = []
        toolbar.stop_requested.connect(lambda: signals.append("stop"))
        toolbar._stop_action.trigger()
        assert signals == ["stop"]

    def test_clear_signal(self, qtbot):
        from pylearn.ui.toolbar import MainToolBar

        toolbar = MainToolBar()
        qtbot.addWidget(toolbar)
        signals = []
        toolbar.clear_console_requested.connect(lambda: signals.append("clear"))
        toolbar._clear_action.trigger()
        assert signals == ["clear"]

    def test_theme_changed_signal(self, qtbot):
        from pylearn.ui.toolbar import MainToolBar

        toolbar = MainToolBar()
        qtbot.addWidget(toolbar)
        signals = []
        toolbar.theme_changed.connect(signals.append)
        toolbar._theme_combo.setCurrentText("Dark")
        assert signals == ["dark"]

    def test_font_size_changed_signal(self, qtbot):
        from pylearn.ui.toolbar import MainToolBar

        toolbar = MainToolBar()
        qtbot.addWidget(toolbar)
        signals = []
        toolbar.font_size_changed.connect(signals.append)
        toolbar._font_spin.setValue(14)
        assert 14 in signals

    def test_initial_font_size(self, qtbot):
        from pylearn.ui.toolbar import MainToolBar

        toolbar = MainToolBar()
        qtbot.addWidget(toolbar)
        assert toolbar._font_spin.value() == 12

    def test_font_range(self, qtbot):
        from pylearn.ui.toolbar import MainToolBar

        toolbar = MainToolBar()
        qtbot.addWidget(toolbar)
        assert toolbar._font_spin.minimum() == 8
        assert toolbar._font_spin.maximum() == 24
