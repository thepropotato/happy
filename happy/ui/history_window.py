"""The history window: every request, what Happy did about it, and what it answered, newest first."""

import html
from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QTextBrowser, QVBoxLayout, QWidget

from happy import history
from happy.ui import smile

HOW = {"wake": "said", "key": "held the key", "follow": "follow-up", "typed": "typed"}


class History(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Happy — History")
        self.setWindowIcon(smile.icon(128))
        self.resize(620, 720)
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search what you said or what Happy answered")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda: self.typing.start(250))
        top.addWidget(self.search)
        self.count = QLabel("")
        self.count.setStyleSheet("color: palette(placeholder-text);")
        top.addWidget(self.count)
        layout.addLayout(top)
        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(True)
        layout.addWidget(self.view)
        note = QLabel(f"Kept on this computer in {history.FILE}")
        note.setStyleSheet("color: palette(placeholder-text);")
        layout.addWidget(note)
        self.typing = QTimer(self)
        self.typing.setSingleShot(True)
        self.typing.timeout.connect(self.reload)

    def reload(self):
        turns = history.recent(limit=500, search=self.search.text().strip())
        self.count.setText(f"{len(turns)} shown")
        quiet = "color:#8e8e93"
        parts, day = [], None
        for turn in turns:
            when = datetime.fromtimestamp(turn["at"])
            label = when.strftime("%A %d %B %Y")
            if label != day:
                day = label
                parts.append(f'<h3 style="margin:18px 0 6px 0">{label}</h3>')
            meta = " · ".join(x for x in (when.strftime("%H:%M"), HOW.get(turn["how"], turn["how"]), turn["model"],
                                          f"{turn['seconds']:.1f}s" if turn["seconds"] else "") if x)
            parts.append(f'<p style="{quiet};margin:10px 0 2px 0;font-size:11px">{html.escape(meta)}</p>')
            parts.append(f'<p style="margin:0"><b>You:</b> {html.escape(turn["request"])}</p>')
            for step in turn["steps"]:
                mark = "✕" if step.get("ok") is False else "·"
                parts.append(f'<p style="{quiet};margin:0 0 0 14px;font-size:12px">{mark} {html.escape(step.get("label") or step.get("tool", ""))}</p>')
            reply = html.escape(turn["reply"] or ("(stopped)" if turn["failed"] else "")).replace("\n", "<br>")
            parts.append(f'<p style="margin:2px 0 0 0"><b>Happy:</b> {reply}</p>')
        if not turns:
            parts.append(f'<p style="{quiet}">Nothing yet. Every request you make shows up here.</p>')
        self.view.setHtml("".join(parts))
