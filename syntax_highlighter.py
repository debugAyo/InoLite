import re 
from PyQt6.QtGui import  QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt6.QtCore  import QRegularExpression

class ArduinoHighlighter(QSyntaxHighlighter):
    """Provides C++ and Arduino syntax highlighting."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("569CD6"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            r"\bchar\b", r"\bclass\b", r"\bconst\b", r"\bdouble\b", r"\benum\b",
            r"\bexplicit\b", r"\bfloat\b", r"\bfor\b", r"\bif\b", r"\bint\b",
            r"\blong\b", r"\bnamespace\b", r"\boperator\b", r"\bprivate\b",
            r"\bprotected\b", r"\bpublic\b", r"\bshort\b", r"\bsigned\b",
            r"\bstatic\b", r"\bstruct\b", r"\btemplate\b", r"\btypedef\b",
            r"\btypename\b", r"\bunsigned\b", r"\bvirtual\b", r"\bvoid\b",
            r"\bvolatile\b", r"\bwhile\b", r"\belse\b", r"\breturn\b", r"\bbool\b"
        ]
        for pattern in keywords:
            self.highlighting_rules.append((QRegularExpression(pattern), keyword_format))
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8"))
        self.highlighting_rules.append((QRegularExpression(r"\b\d+b"), number_format))
        
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))
        self.highlighting_rules.append((QRegularExpression(r"\".*?\""), string_format))

        preproc_format = QTextCharFormat()
        preproc_format.setForeground(QColor("#9CDCFE"))
        self.highlighting_rules.append((QRegularExpression(r"#[a-zA-Z_]+"), preproc_format)) 

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))
        self.highlighting_rules.append((QRegularExpression(r"//[^\n]*"), comment_format))
    
    def highlightBlock(self, text):
        """Applies syntax formatting line by line."""
        for pattern, fmt in self.highlighting_rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

        