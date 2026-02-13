"""QSS themes for the application (light and dark)."""

LIGHT_THEME = """
QMainWindow {
    background-color: #f5f5f5;
}
QSplitter::handle {
    background-color: #ddd;
    width: 3px;
    height: 3px;
}
QSplitter::handle:hover {
    background-color: #3498db;
}
QTreeWidget {
    background-color: #ffffff;
    border: 1px solid #ddd;
    font-size: 13px;
    padding: 4px;
}
QTreeWidget::item {
    padding: 4px 6px;
    border-radius: 3px;
}
QTreeWidget::item:selected {
    background-color: #3498db;
    color: white;
}
QTreeWidget::item:hover {
    background-color: #e8f4f8;
}
QTextBrowser {
    background-color: #ffffff;
    border: 1px solid #ddd;
}
QMenuBar {
    background-color: #ffffff;
    border-bottom: 1px solid #ddd;
    padding: 2px;
}
QMenuBar::item:selected {
    background-color: #3498db;
    color: white;
    border-radius: 4px;
}
QMenu {
    background-color: #ffffff;
    border: 1px solid #ddd;
    padding: 4px;
}
QMenu::item:selected {
    background-color: #3498db;
    color: white;
    border-radius: 3px;
}
QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #ddd;
    spacing: 6px;
    padding: 3px;
}
QToolButton {
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 13px;
}
QToolButton:hover {
    background-color: #e8f4f8;
    border-color: #3498db;
}
QToolButton:pressed {
    background-color: #3498db;
    color: white;
}
QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #ddd;
    font-size: 12px;
    color: #666;
}
QComboBox {
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 4px 8px;
    background-color: #ffffff;
    min-width: 120px;
}
QComboBox:hover {
    border-color: #3498db;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QPushButton {
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 6px 16px;
    background-color: #ffffff;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #e8f4f8;
    border-color: #3498db;
}
QPushButton:pressed {
    background-color: #3498db;
    color: white;
}
QDialog {
    background-color: #f5f5f5;
}
QLineEdit, QTextEdit {
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 6px;
    background-color: #ffffff;
}
QLineEdit:focus, QTextEdit:focus {
    border-color: #3498db;
}
"""

DARK_THEME = """
QMainWindow {
    background-color: #1e1e2e;
}
QSplitter::handle {
    background-color: #45475a;
    width: 3px;
    height: 3px;
}
QSplitter::handle:hover {
    background-color: #89b4fa;
}
QTreeWidget {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    font-size: 13px;
    padding: 4px;
}
QTreeWidget::item {
    padding: 4px 6px;
    border-radius: 3px;
}
QTreeWidget::item:selected {
    background-color: #89b4fa;
    color: #1e1e2e;
}
QTreeWidget::item:hover {
    background-color: #313244;
}
QTextBrowser {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #45475a;
}
QMenuBar {
    background-color: #181825;
    color: #cdd6f4;
    border-bottom: 1px solid #45475a;
    padding: 2px;
}
QMenuBar::item:selected {
    background-color: #89b4fa;
    color: #1e1e2e;
    border-radius: 4px;
}
QMenu {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #45475a;
    padding: 4px;
}
QMenu::item:selected {
    background-color: #89b4fa;
    color: #1e1e2e;
    border-radius: 3px;
}
QToolBar {
    background-color: #181825;
    border-bottom: 1px solid #45475a;
    spacing: 6px;
    padding: 3px;
}
QToolButton {
    color: #cdd6f4;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 13px;
}
QToolButton:hover {
    background-color: #313244;
    border-color: #89b4fa;
}
QToolButton:pressed {
    background-color: #89b4fa;
    color: #1e1e2e;
}
QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #45475a;
    font-size: 12px;
}
QComboBox {
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
    background-color: #1e1e2e;
    color: #cdd6f4;
    min-width: 120px;
}
QComboBox:hover {
    border-color: #89b4fa;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #45475a;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
}
QPushButton {
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 6px 16px;
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #313244;
    border-color: #89b4fa;
}
QPushButton:pressed {
    background-color: #89b4fa;
    color: #1e1e2e;
}
QDialog {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QLineEdit, QTextEdit {
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 6px;
    background-color: #181825;
    color: #cdd6f4;
}
QLineEdit:focus, QTextEdit:focus {
    border-color: #89b4fa;
}
QLabel {
    color: #cdd6f4;
}
"""

THEMES = {
    "light": LIGHT_THEME,
    "dark": DARK_THEME,
}


def get_stylesheet(theme_name: str) -> str:
    """Get QSS stylesheet for a theme."""
    return THEMES.get(theme_name, LIGHT_THEME)
