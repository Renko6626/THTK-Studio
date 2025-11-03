# app/widgets/search_panel.py

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel, QStyle
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIcon # <--- FIXED: Added the missing QIcon import

class SearchPanel(QWidget):
    """一个显示在编辑器右上角的、更美观的搜索面板。"""
    find_next = pyqtSignal(str)
    find_previous = pyqtSignal(str)
    closed = pyqtSignal()
    search_text_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setMinimumWidth(300)
        self.setStyleSheet("""
            SearchPanel {
                background-color: #3c3f41;
                border: 1px solid #555;
                border-radius: 4px;
                color: #ffffff;
            }
            QLineEdit { 
                background-color: #2b2b2b; 
                border: 1px solid #555;
                color: #ffffff;
                padding: 4px;
            }
            QLineEdit::placeholder {
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton { 
                background-color: #555;
                border: none;
                padding: 4px;
                width: 24px;
                height: 24px;
                color: #ffffff;
            }
            QPushButton:hover { background-color: #666; }
            QPushButton:pressed { background-color: #777; }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("查找")
        self.search_input.returnPressed.connect(self._on_find_next)
        self.search_input.textChanged.connect(self.search_text_changed)

        self.match_label = QLabel("0 / 0")
        self.match_label.setFixedWidth(60)

        style = self.style()
        btn_prev = QPushButton(QIcon(style.standardPixmap(QStyle.StandardPixmap.SP_ArrowUp)), "")
        btn_next = QPushButton(QIcon(style.standardPixmap(QStyle.StandardPixmap.SP_ArrowDown)), "")
        btn_close = QPushButton(QIcon(style.standardPixmap(QStyle.StandardPixmap.SP_DialogCloseButton)), "")

        btn_prev.setToolTip("查找上一个 (Shift+Enter)")
        btn_next.setToolTip("查找下一个 (Enter)")
        btn_close.setToolTip("关闭 (Esc)")
        
        btn_next.clicked.connect(self._on_find_next)
        btn_prev.clicked.connect(self._on_find_previous)
        btn_close.clicked.connect(self.closed)
        
        layout.addWidget(self.search_input)
        layout.addWidget(self.match_label)
        layout.addWidget(btn_prev)
        layout.addWidget(btn_next)
        layout.addWidget(btn_close)

    def _on_find_next(self):
        self.find_next.emit(self.search_input.text())

    def _on_find_previous(self):
        self.find_previous.emit(self.search_input.text())
        
    def focus_input(self):
        self.search_input.setFocus()
        self.search_input.selectAll()

    def update_match_count(self, current, total):
        self.match_label.setText(f"{current} / {total}")

    def get_search_text(self):
        return self.search_input.text()