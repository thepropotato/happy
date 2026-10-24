"""Happy's look: near-black surfaces with a green accent, shared by every window."""

INK = "#ECEFED"
QUIET = "#97A19B"
GREEN = "#22B162"
GREEN_SOFT = "#5BD48A"
WARN = "#F2A65A"
BASE = "#0E100F"
CARD = "#161917"
LINE = "#252B27"

STYLE = f"""
QWidget#happy {{ background: {BASE}; }}
QWidget {{ color: {INK}; font-size: 13px; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: {BASE}; border: none; }}
QLabel#title {{ font-size: 22px; font-weight: 600; }}
QLabel#quiet {{ color: {QUIET}; }}
QLabel#small {{ color: {QUIET}; font-size: 12px; }}
QLabel#heading {{ font-size: 14px; font-weight: 600; }}
QLabel#good {{ color: {GREEN_SOFT}; }}
QLabel#bad {{ color: {WARN}; }}
QFrame#card {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 12px; }}
QFrame#card QLabel {{ background: transparent; }}
QLineEdit, QComboBox, QTextBrowser {{ background: {BASE}; border: 1px solid {LINE}; border-radius: 8px; padding: 7px 9px; selection-background-color: {GREEN}; }}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {GREEN}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: {CARD}; border: 1px solid {LINE}; selection-background-color: #1F3A2A; }}
QPushButton {{ background: #1E2420; border: 1px solid {LINE}; border-radius: 8px; padding: 7px 14px; }}
QPushButton:hover {{ background: #26302A; }}
QPushButton#primary {{ background: {GREEN}; border: none; color: #04140A; font-weight: 600; padding: 10px 20px; font-size: 14px; }}
QPushButton#primary:hover {{ background: {GREEN_SOFT}; }}
QPushButton#primary:disabled {{ background: #1E2420; color: #5D6661; }}
QProgressBar {{ background: {BASE}; border: none; border-radius: 4px; height: 8px; }}
QProgressBar::chunk {{ background: {GREEN}; border-radius: 4px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {LINE}; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
"""
