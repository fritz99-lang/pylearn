"""QSS themes for the application, generated from the centralized palette."""

from pylearn.ui.theme_registry import get_palette, ThemePalette


def _generate_qss(p: ThemePalette) -> str:
    """Generate a complete QSS stylesheet from a theme palette."""
    return f"""
QMainWindow {{
    background-color: {p.bg_alt};
    color: {p.text};
}}
QWidget {{
    color: {p.text};
}}
QSplitter::handle {{
    background-color: {p.border};
    width: 3px;
    height: 3px;
}}
QSplitter::handle:hover {{
    background-color: {p.accent};
}}
QTreeWidget {{
    background-color: {p.bg};
    color: {p.text};
    border: 1px solid {p.border};
    font-size: 13px;
    padding: 4px;
}}
QTreeWidget::item {{
    padding: 4px 6px;
    border-radius: 3px;
}}
QTreeWidget::item:selected {{
    background-color: {p.accent};
    color: {p.accent_text};
}}
QTreeWidget::item:hover {{
    background-color: {p.bg_alt};
}}
QTextBrowser {{
    background-color: {p.bg};
    color: {p.text};
    border: 1px solid {p.border};
}}
QMenuBar {{
    background-color: {p.bg_alt if p.name != 'light' else p.bg};
    color: {p.text};
    border-bottom: 1px solid {p.border};
    padding: 2px;
}}
QMenuBar::item:selected {{
    background-color: {p.accent};
    color: {p.accent_text};
    border-radius: 4px;
}}
QMenu {{
    background-color: {p.bg};
    color: {p.text};
    border: 1px solid {p.border};
    padding: 4px;
}}
QMenu::item:selected {{
    background-color: {p.accent};
    color: {p.accent_text};
    border-radius: 3px;
}}
QToolBar {{
    background-color: {p.bg_alt if p.name != 'light' else p.bg};
    border-bottom: 1px solid {p.border};
    spacing: 6px;
    padding: 3px;
}}
QToolButton {{
    color: {p.text};
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 13px;
}}
QToolButton:hover {{
    background-color: {p.bg_alt};
    border-color: {p.accent};
}}
QToolButton:pressed {{
    background-color: {p.accent};
    color: {p.accent_text};
}}
QStatusBar {{
    background-color: {p.bg_alt if p.name != 'light' else p.bg};
    color: {p.text_muted};
    border-top: 1px solid {p.border};
    font-size: 12px;
}}
QComboBox {{
    border: 1px solid {p.border};
    border-radius: 4px;
    padding: 4px 8px;
    background-color: {p.bg};
    color: {p.text};
    min-width: 120px;
}}
QComboBox:hover {{
    border-color: {p.accent};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {p.bg};
    color: {p.text};
    border: 1px solid {p.border};
    selection-background-color: {p.accent};
    selection-color: {p.accent_text};
}}
QPushButton {{
    border: 1px solid {p.border};
    border-radius: 4px;
    padding: 6px 16px;
    background-color: {p.bg};
    color: {p.text};
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {p.bg_alt};
    border-color: {p.accent};
}}
QPushButton:pressed {{
    background-color: {p.accent};
    color: {p.accent_text};
}}
QDialog {{
    background-color: {p.bg_alt if p.name != 'light' else p.bg_alt};
    color: {p.text};
}}
QLabel {{
    color: {p.text};
}}
QLineEdit, QTextEdit {{
    border: 1px solid {p.border};
    border-radius: 4px;
    padding: 6px;
    background-color: {p.bg_alt if p.name != 'light' else p.bg};
    color: {p.text};
}}
QLineEdit:focus, QTextEdit:focus {{
    border-color: {p.accent};
}}
"""


def get_stylesheet(theme_name: str) -> str:
    """Get QSS stylesheet for a theme, generated from the centralized palette."""
    return _generate_qss(get_palette(theme_name))
