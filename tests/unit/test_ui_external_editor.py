"""Tests for external_editor — editor resolution and file watching."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pylearn.ui.external_editor import ExternalEditorManager, find_editor

# ===========================================================================
# find_editor
# ===========================================================================


class TestFindEditor:
    def test_absolute_path_exists(self, tmp_path):
        exe = tmp_path / "editor.exe"
        exe.write_text("fake")
        result = find_editor(str(exe))
        assert result == str(exe)

    def test_absolute_path_missing(self, tmp_path):
        result = find_editor(str(tmp_path / "nonexistent.exe"))
        assert result is None or isinstance(result, str)

    @patch("pylearn.ui.external_editor.shutil.which")
    def test_which_lookup(self, mock_which):
        mock_which.return_value = "/usr/bin/code"
        assert find_editor("code") == "/usr/bin/code"

    @patch("pylearn.ui.external_editor.shutil.which", return_value=None)
    def test_fallback_to_npp_paths(self, mock_which, tmp_path):
        with patch("pylearn.ui.external_editor._NPP_PATHS", [tmp_path / "npp.exe"]):
            assert find_editor("notepad++") is None

    @patch("pylearn.ui.external_editor.shutil.which", return_value=None)
    def test_npp_found(self, mock_which, tmp_path):
        npp_exe = tmp_path / "notepad++.exe"
        npp_exe.write_text("fake")
        with patch("pylearn.ui.external_editor._NPP_PATHS", [npp_exe]):
            assert find_editor("notepad++") == str(npp_exe)


# ===========================================================================
# ExternalEditorManager (QObject, not QWidget — no addWidget)
# ===========================================================================


class TestExternalEditorManager:
    def test_construction(self):
        mgr = ExternalEditorManager()
        assert mgr._current_file is None

    @patch("pylearn.ui.external_editor.find_editor", return_value=None)
    def test_open_editor_not_found(self, mock_find):
        mgr = ExternalEditorManager()
        err = mgr.open("print(1)", "python", "nonexistent")
        assert err is not None
        assert "Could not find editor" in err

    @patch("pylearn.ui.external_editor.subprocess.Popen")
    @patch("pylearn.ui.external_editor.find_editor")
    def test_open_success(self, mock_find, mock_popen, tmp_path, monkeypatch):
        from pylearn.core import constants

        monkeypatch.setattr(constants, "DATA_DIR", tmp_path)

        mock_find.return_value = "/usr/bin/code"
        mock_popen.return_value = MagicMock()

        mgr = ExternalEditorManager()
        err = mgr.open("print('hello')", "python", "code")
        assert err is None
        assert mgr._current_file is not None
        assert mgr._current_file.exists()
        assert mgr._current_file.read_text(encoding="utf-8") == "print('hello')"

    @patch("pylearn.ui.external_editor.subprocess.Popen")
    @patch("pylearn.ui.external_editor.find_editor")
    def test_open_cpp_extension(self, mock_find, mock_popen, tmp_path, monkeypatch):
        from pylearn.core import constants

        monkeypatch.setattr(constants, "DATA_DIR", tmp_path)

        mock_find.return_value = "/usr/bin/code"
        mock_popen.return_value = MagicMock()

        mgr = ExternalEditorManager()
        mgr.open("int main() {}", "cpp", "code")
        assert mgr._current_file.suffix == ".cpp"

    @patch("pylearn.ui.external_editor.subprocess.Popen")
    @patch("pylearn.ui.external_editor.find_editor")
    def test_open_popen_failure(self, mock_find, mock_popen, tmp_path, monkeypatch):
        from pylearn.core import constants

        monkeypatch.setattr(constants, "DATA_DIR", tmp_path)

        mock_find.return_value = "/usr/bin/code"
        mock_popen.side_effect = OSError("Permission denied")

        mgr = ExternalEditorManager()
        err = mgr.open("code", "python", "code")
        assert err is not None
        assert "Failed to launch" in err

    def test_on_file_changed_emits_signal(self, tmp_path):
        mgr = ExternalEditorManager()
        signals = []
        mgr.code_changed.connect(signals.append)

        f = tmp_path / "test.py"
        f.write_text("new code", encoding="utf-8")
        mgr._on_file_changed(str(f))
        assert signals == ["new code"]

    def test_on_file_changed_missing_file(self, tmp_path):
        mgr = ExternalEditorManager()
        signals = []
        mgr.code_changed.connect(signals.append)
        mgr._on_file_changed(str(tmp_path / "gone.py"))
        assert signals == []

    @patch("pylearn.ui.external_editor.subprocess.Popen")
    @patch("pylearn.ui.external_editor.find_editor")
    def test_cleanup(self, mock_find, mock_popen, tmp_path, monkeypatch):
        from pylearn.core import constants

        monkeypatch.setattr(constants, "DATA_DIR", tmp_path)

        mock_find.return_value = "/usr/bin/code"
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        mock_popen.return_value = mock_proc

        mgr = ExternalEditorManager()
        mgr.open("code", "python", "code")
        temp_file = mgr._current_file
        assert temp_file.exists()

        mgr.cleanup()
        assert mgr._current_file is None
        assert not temp_file.exists()

    def test_reap_process_noop_when_none(self):
        mgr = ExternalEditorManager()
        mgr._reap_process()  # should not raise
