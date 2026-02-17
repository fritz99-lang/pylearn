"""Code editor panel using QScintilla."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtGui import QColor, QFont
from PyQt6.Qsci import QsciScintilla, QsciLexerPython, QsciLexerCPP, QsciLexerHTML

from pylearn.ui.theme_registry import get_palette


class EditorPanel(QWidget):
    """Right-top panel: QScintilla-based Python code editor."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._editor = QsciScintilla(self)
        layout.addWidget(self._editor)

        self._setup_editor()

    def _setup_editor(self) -> None:
        """Configure the QScintilla editor with Python support."""
        editor = self._editor

        # Lexer
        lexer = QsciLexerPython(editor)
        font = QFont("Consolas", 12)
        lexer.setDefaultFont(font)
        lexer.setFont(font)
        editor.setLexer(lexer)

        # Line numbers
        editor.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        editor.setMarginWidth(0, "0000")
        editor.setMarginsForegroundColor(QColor("#888888"))
        editor.setMarginsBackgroundColor(QColor("#f0f0f0"))

        # Current line highlight
        editor.setCaretLineVisible(True)
        editor.setCaretLineBackgroundColor(QColor("#e8f4f8"))

        # Indentation
        editor.setIndentationsUseTabs(False)
        editor.setTabWidth(4)
        editor.setAutoIndent(True)
        editor.setIndentationGuides(True)

        # Bracket matching
        editor.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        editor.setMatchedBraceBackgroundColor(QColor("#b4d7ff"))
        editor.setMatchedBraceForegroundColor(QColor("#000000"))

        # Code folding
        editor.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle)

        # Edge column
        editor.setEdgeMode(QsciScintilla.EdgeMode.EdgeLine)
        editor.setEdgeColumn(88)
        editor.setEdgeColor(QColor("#e0e0e0"))

        # Auto-completion (basic)
        editor.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsDocument)
        editor.setAutoCompletionThreshold(3)

        # Wrap mode
        editor.setWrapMode(QsciScintilla.WrapMode.WrapNone)

        # Default content
        editor.setText("# Try your Python code here\n\n")

    def get_code(self) -> str:
        """Get the current editor text."""
        return self._editor.text()

    def set_code(self, code: str) -> None:
        """Set the editor text."""
        self._editor.setText(code)

    def append_code(self, code: str) -> None:
        """Append code to the editor."""
        current = self._editor.text()
        if current.strip():
            self._editor.setText(current.rstrip() + "\n\n" + code)
        else:
            self._editor.setText(code)
        # Move cursor to end
        self._editor.SendScintilla(
            self._editor.SCI_DOCUMENTEND
        )

    def clear(self) -> None:
        """Clear the editor."""
        self._editor.setText("")

    def set_font_size(self, size: int) -> None:
        """Update the editor font size."""
        font = QFont("Consolas", size)
        lexer = self._editor.lexer()
        if lexer:
            lexer.setDefaultFont(font)
            lexer.setFont(font)

    def set_tab_width(self, width: int) -> None:
        """Update tab width."""
        self._editor.setTabWidth(width)

    def set_theme(self, theme_name: str) -> None:
        """Switch editor theme between light, dark, and sepia."""
        editor = self._editor
        lexer = editor.lexer()

        p = get_palette(theme_name)
        editor.setMarginsBackgroundColor(QColor(p.bg_alt))
        editor.setMarginsForegroundColor(QColor(p.text_muted))
        editor.setCaretLineBackgroundColor(QColor(p.border))
        editor.setEdgeColor(QColor(p.border))
        editor.setPaper(QColor(p.bg))
        editor.setColor(QColor(p.text))
        if lexer:
            lexer.setPaper(QColor(p.bg))
            lexer.setColor(QColor(p.text))
            if isinstance(lexer, QsciLexerCPP):
                self._apply_cpp_theme(lexer, theme_name)
            elif isinstance(lexer, QsciLexerPython):
                self._apply_python_theme(lexer, theme_name)
            elif isinstance(lexer, QsciLexerHTML):
                self._apply_html_theme(lexer, theme_name)

    # --- Per-lexer theme helpers (correct style IDs for each lexer) ---

    def _apply_python_theme(self, lexer: QsciLexerPython, theme: str) -> None:
        p = get_palette(theme)
        lexer.setColor(QColor(p.syn_comment), QsciLexerPython.Comment)
        lexer.setColor(QColor(p.syn_keyword), QsciLexerPython.Keyword)
        lexer.setColor(QColor(p.syn_number), QsciLexerPython.Number)
        lexer.setColor(QColor(p.syn_string), QsciLexerPython.DoubleQuotedString)
        lexer.setColor(QColor(p.syn_string), QsciLexerPython.SingleQuotedString)
        lexer.setColor(QColor(p.syn_string), QsciLexerPython.TripleSingleQuotedString)
        lexer.setColor(QColor(p.syn_string), QsciLexerPython.TripleDoubleQuotedString)
        lexer.setColor(QColor(p.syn_class), QsciLexerPython.ClassName)
        lexer.setColor(QColor(p.syn_func), QsciLexerPython.FunctionMethodName)
        lexer.setColor(QColor(p.syn_decorator), QsciLexerPython.Decorator)

    def _apply_cpp_theme(self, lexer: QsciLexerCPP, theme: str) -> None:
        p = get_palette(theme)
        lexer.setColor(QColor(p.syn_comment), QsciLexerCPP.Comment)
        lexer.setColor(QColor(p.syn_comment), QsciLexerCPP.CommentLine)
        lexer.setColor(QColor(p.text_muted), QsciLexerCPP.CommentDoc)
        lexer.setColor(QColor(p.syn_keyword), QsciLexerCPP.Keyword)
        lexer.setColor(QColor(p.syn_number), QsciLexerCPP.Number)
        lexer.setColor(QColor(p.syn_string), QsciLexerCPP.DoubleQuotedString)
        lexer.setColor(QColor(p.syn_string), QsciLexerCPP.SingleQuotedString)
        lexer.setColor(QColor(p.syn_decorator), QsciLexerCPP.PreProcessor)
        lexer.setColor(QColor(p.syn_operator), QsciLexerCPP.Operator)
        lexer.setColor(QColor(p.syn_class), QsciLexerCPP.GlobalClass)

    def _apply_html_theme(self, lexer: QsciLexerHTML, theme: str) -> None:
        p = get_palette(theme)
        lexer.setColor(QColor(p.syn_class), QsciLexerHTML.Tag)
        lexer.setColor(QColor(p.syn_class), QsciLexerHTML.UnknownTag)
        lexer.setColor(QColor(p.syn_keyword), QsciLexerHTML.Attribute)
        lexer.setColor(QColor(p.syn_keyword), QsciLexerHTML.UnknownAttribute)
        lexer.setColor(QColor(p.syn_number), QsciLexerHTML.HTMLNumber)
        lexer.setColor(QColor(p.syn_string), QsciLexerHTML.HTMLDoubleQuotedString)
        lexer.setColor(QColor(p.syn_string), QsciLexerHTML.HTMLSingleQuotedString)
        lexer.setColor(QColor(p.syn_class), QsciLexerHTML.OtherInTag)
        lexer.setColor(QColor(p.syn_comment), QsciLexerHTML.HTMLComment)
        lexer.setColor(QColor(p.syn_decorator), QsciLexerHTML.Entity)

    def set_language(self, language: str) -> None:
        """Switch the editor lexer between Python and C++."""
        self._language = language
        editor = self._editor
        font = QFont("Consolas", 12)
        lexer = editor.lexer()

        # Get current font size from existing lexer if possible
        if lexer:
            font = lexer.defaultFont(0)

        if language in ("cpp", "c"):
            new_lexer = QsciLexerCPP(editor)
            placeholder = "// Try your C++ code here\n#include <iostream>\n\nint main() {\n    \n    return 0;\n}\n"
        elif language == "html":
            new_lexer = QsciLexerHTML(editor)
            placeholder = '<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <title>My Page</title>\n    <style>\n        body { font-family: sans-serif; }\n    </style>\n</head>\n<body>\n    <h1>Hello, World!</h1>\n</body>\n</html>\n'
        else:
            new_lexer = QsciLexerPython(editor)
            placeholder = "# Try your Python code here\n\n"

        new_lexer.setDefaultFont(font)
        new_lexer.setFont(font)
        editor.setLexer(new_lexer)

        # Only set placeholder if editor is empty or has old placeholder
        current = editor.text().strip()
        if not current or current.startswith("# Try your") or current.startswith("// Try your") or current.startswith("<!DOCTYPE html>"):
            editor.setText(placeholder)

    @property
    def language(self) -> str:
        return getattr(self, "_language", "python")

    @property
    def editor(self) -> QsciScintilla:
        return self._editor
