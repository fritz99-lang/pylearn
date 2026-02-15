"""External editor integration (Notepad++ or user-configured editor)."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from PyQt6.QtCore import QObject, QFileSystemWatcher, pyqtSignal

from pylearn.core.constants import DATA_DIR

logger = logging.getLogger("pylearn.ui.external_editor")

# Common Notepad++ install locations on Windows
_NPP_PATHS = [
    Path(r"C:\Program Files\Notepad++\notepad++.exe"),
    Path(r"C:\Program Files (x86)\Notepad++\notepad++.exe"),
]

# Language → file extension for temp files
_LANG_EXT = {
    "python": ".py",
    "cpp": ".cpp",
    "c": ".c",
    "html": ".html",
}


def find_editor(configured_path: str) -> str | None:
    """Resolve the editor executable path.

    Tries in order:
    1. The configured path (if absolute and exists)
    2. shutil.which() on the configured name
    3. Common Notepad++ install paths
    """
    # If it's an absolute path that exists, use it directly
    p = Path(configured_path)
    if p.is_absolute() and p.exists():
        return str(p)

    # Try PATH lookup
    found = shutil.which(configured_path)
    if found:
        return found

    # Fall back to common install locations
    for npp in _NPP_PATHS:
        if npp.exists():
            return str(npp)

    return None


class ExternalEditorManager(QObject):
    """Manages launching an external editor and watching for file changes."""

    code_changed = pyqtSignal(str)  # emitted with new file contents on save

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_file_changed)
        self._current_file: Path | None = None
        self._process: subprocess.Popen | None = None

    def open(self, code: str, language: str, editor_path: str) -> str | None:
        """Write code to a temp file and open it in the external editor.

        Returns an error message string on failure, or None on success.
        """
        exe = find_editor(editor_path)
        if not exe:
            return (
                f"Could not find editor: {editor_path}\n\n"
                "Install Notepad++ and add it to PATH, or set the full path "
                "in editor_config.json (external_editor_path)."
            )

        ext = _LANG_EXT.get(language, ".py")
        temp_file = DATA_DIR / f"editor_scratch{ext}"

        # Write current code to the scratch file
        temp_file.write_text(code, encoding="utf-8")

        # Watch for changes (remove old watch first)
        if self._current_file:
            self._watcher.removePath(str(self._current_file))
        self._current_file = temp_file
        self._watcher.addPath(str(temp_file))

        # Launch the editor
        try:
            self._process = subprocess.Popen([exe, str(temp_file)])
        except OSError as e:
            logger.error("Failed to launch editor: %s", e)
            return f"Failed to launch editor: {e}"

        return None

    def _on_file_changed(self, path: str) -> None:
        """Called when the watched file is modified externally."""
        p = Path(path)
        if not p.exists():
            return

        try:
            new_code = p.read_text(encoding="utf-8")
        except OSError:
            return

        self.code_changed.emit(new_code)

        # Some editors delete+recreate — re-add the watch
        if not self._watcher.files() or path not in self._watcher.files():
            self._watcher.addPath(path)

    def cleanup(self) -> None:
        """Remove temp files and stop watching."""
        if self._current_file:
            self._watcher.removePath(str(self._current_file))
            try:
                self._current_file.unlink(missing_ok=True)
            except OSError:
                pass
            self._current_file = None
