"""Code editor panel using QScintilla."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtGui import QColor, QFont
from PyQt6.Qsci import QsciScintilla, QsciLexerPython, QsciLexerCPP, QsciLexerHTML


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

        if theme_name == "dark":
            editor.setMarginsBackgroundColor(QColor("#1e1e2e"))
            editor.setMarginsForegroundColor(QColor("#6c7086"))
            editor.setCaretLineBackgroundColor(QColor("#313244"))
            editor.setEdgeColor(QColor("#45475a"))
            editor.setPaper(QColor("#1e1e2e"))
            editor.setColor(QColor("#cdd6f4"))
            if lexer:
                lexer.setPaper(QColor("#1e1e2e"))
                lexer.setColor(QColor("#cdd6f4"))  # Default
                if isinstance(lexer, (QsciLexerPython, QsciLexerCPP)):
                    lexer.setColor(QColor("#6c7086"), QsciLexerPython.Comment)
                    lexer.setColor(QColor("#a6e3a1"), QsciLexerPython.Keyword)
                    lexer.setColor(QColor("#f38ba8"), QsciLexerPython.Number)
                    lexer.setColor(QColor("#fab387"), QsciLexerPython.DoubleQuotedString)
                    lexer.setColor(QColor("#fab387"), QsciLexerPython.SingleQuotedString)
                    lexer.setColor(QColor("#fab387"), QsciLexerPython.TripleSingleQuotedString)
                    lexer.setColor(QColor("#fab387"), QsciLexerPython.TripleDoubleQuotedString)
                    lexer.setColor(QColor("#89b4fa"), QsciLexerPython.ClassName)
                    lexer.setColor(QColor("#89b4fa"), QsciLexerPython.FunctionMethodName)
                    lexer.setColor(QColor("#cba6f7"), QsciLexerPython.Decorator)
                elif isinstance(lexer, QsciLexerHTML):
                    lexer.setColor(QColor("#89b4fa"), QsciLexerHTML.Tag)
                    lexer.setColor(QColor("#89b4fa"), QsciLexerHTML.UnknownTag)
                    lexer.setColor(QColor("#a6e3a1"), QsciLexerHTML.Attribute)
                    lexer.setColor(QColor("#a6e3a1"), QsciLexerHTML.UnknownAttribute)
                    lexer.setColor(QColor("#f38ba8"), QsciLexerHTML.HTMLNumber)
                    lexer.setColor(QColor("#fab387"), QsciLexerHTML.HTMLDoubleQuotedString)
                    lexer.setColor(QColor("#fab387"), QsciLexerHTML.HTMLSingleQuotedString)
                    lexer.setColor(QColor("#89b4fa"), QsciLexerHTML.OtherInTag)
                    lexer.setColor(QColor("#6c7086"), QsciLexerHTML.HTMLComment)
                    lexer.setColor(QColor("#cba6f7"), QsciLexerHTML.Entity)
        elif theme_name == "sepia":
            editor.setMarginsBackgroundColor(QColor("#efe6d0"))
            editor.setMarginsForegroundColor(QColor("#9c8b74"))
            editor.setCaretLineBackgroundColor(QColor("#e8ddc4"))
            editor.setEdgeColor(QColor("#d4c5a9"))
            editor.setPaper(QColor("#f4ecd8"))
            editor.setColor(QColor("#5b4636"))
            if lexer:
                lexer.setPaper(QColor("#f4ecd8"))
                lexer.setColor(QColor("#5b4636"))  # Default
                if isinstance(lexer, (QsciLexerPython, QsciLexerCPP)):
                    lexer.setColor(QColor("#9c8b74"), QsciLexerPython.Comment)
                    lexer.setColor(QColor("#8b6914"), QsciLexerPython.Keyword)
                    lexer.setColor(QColor("#b85c3c"), QsciLexerPython.Number)
                    lexer.setColor(QColor("#a0522d"), QsciLexerPython.DoubleQuotedString)
                    lexer.setColor(QColor("#a0522d"), QsciLexerPython.SingleQuotedString)
                    lexer.setColor(QColor("#a0522d"), QsciLexerPython.TripleSingleQuotedString)
                    lexer.setColor(QColor("#a0522d"), QsciLexerPython.TripleDoubleQuotedString)
                    lexer.setColor(QColor("#6b3a2a"), QsciLexerPython.ClassName)
                    lexer.setColor(QColor("#6b3a2a"), QsciLexerPython.FunctionMethodName)
                    lexer.setColor(QColor("#7a5230"), QsciLexerPython.Decorator)
                elif isinstance(lexer, QsciLexerHTML):
                    lexer.setColor(QColor("#6b3a2a"), QsciLexerHTML.Tag)
                    lexer.setColor(QColor("#6b3a2a"), QsciLexerHTML.UnknownTag)
                    lexer.setColor(QColor("#8b6914"), QsciLexerHTML.Attribute)
                    lexer.setColor(QColor("#8b6914"), QsciLexerHTML.UnknownAttribute)
                    lexer.setColor(QColor("#b85c3c"), QsciLexerHTML.HTMLNumber)
                    lexer.setColor(QColor("#a0522d"), QsciLexerHTML.HTMLDoubleQuotedString)
                    lexer.setColor(QColor("#a0522d"), QsciLexerHTML.HTMLSingleQuotedString)
                    lexer.setColor(QColor("#6b3a2a"), QsciLexerHTML.OtherInTag)
                    lexer.setColor(QColor("#9c8b74"), QsciLexerHTML.HTMLComment)
                    lexer.setColor(QColor("#7a5230"), QsciLexerHTML.Entity)
        else:
            editor.setMarginsBackgroundColor(QColor("#f0f0f0"))
            editor.setMarginsForegroundColor(QColor("#888888"))
            editor.setCaretLineBackgroundColor(QColor("#e8f4f8"))
            editor.setEdgeColor(QColor("#e0e0e0"))
            editor.setPaper(QColor("#ffffff"))
            editor.setColor(QColor("#000000"))
            if lexer:
                lexer.setPaper(QColor("#ffffff"))
                lexer.setColor(QColor("#000000"))  # Default
                if isinstance(lexer, (QsciLexerPython, QsciLexerCPP)):
                    lexer.setColor(QColor("#008000"), QsciLexerPython.Comment)
                    lexer.setColor(QColor("#0000ff"), QsciLexerPython.Keyword)
                    lexer.setColor(QColor("#ff0000"), QsciLexerPython.Number)
                    lexer.setColor(QColor("#ba2121"), QsciLexerPython.DoubleQuotedString)
                    lexer.setColor(QColor("#ba2121"), QsciLexerPython.SingleQuotedString)
                    lexer.setColor(QColor("#ba2121"), QsciLexerPython.TripleSingleQuotedString)
                    lexer.setColor(QColor("#ba2121"), QsciLexerPython.TripleDoubleQuotedString)
                    lexer.setColor(QColor("#0000ff"), QsciLexerPython.ClassName)
                    lexer.setColor(QColor("#0000ff"), QsciLexerPython.FunctionMethodName)
                    lexer.setColor(QColor("#aa22ff"), QsciLexerPython.Decorator)
                elif isinstance(lexer, QsciLexerHTML):
                    lexer.setColor(QColor("#0000ff"), QsciLexerHTML.Tag)
                    lexer.setColor(QColor("#0000ff"), QsciLexerHTML.UnknownTag)
                    lexer.setColor(QColor("#008000"), QsciLexerHTML.Attribute)
                    lexer.setColor(QColor("#008000"), QsciLexerHTML.UnknownAttribute)
                    lexer.setColor(QColor("#ff0000"), QsciLexerHTML.HTMLNumber)
                    lexer.setColor(QColor("#ba2121"), QsciLexerHTML.HTMLDoubleQuotedString)
                    lexer.setColor(QColor("#ba2121"), QsciLexerHTML.HTMLSingleQuotedString)
                    lexer.setColor(QColor("#0000ff"), QsciLexerHTML.OtherInTag)
                    lexer.setColor(QColor("#008000"), QsciLexerHTML.HTMLComment)
                    lexer.setColor(QColor("#aa22ff"), QsciLexerHTML.Entity)

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
