# app/widgets/help_panel.py

from PyQt6.QtWidgets import (
    QDockWidget, QLabel, QComboBox, QWidget, QVBoxLayout
)
from PyQt6.QtCore import Qt
from typing import Callable, List, Optional

class HelpPanel(QDockWidget):
    """
    一个可停靠的窗口，用于显示指令的帮助信息。
    """
    def __init__(self, title="帮助", parent=None):
        super().__init__(title, parent)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        # 文档获取回调（由 MainWindow 注入以适配不同脚本类型的规范化逻辑）
        self._get_doc_callback: Optional[Callable[[str], str]] = None

        # 顶部：可编辑下拉框（可输入或选择指令名/关键词）
        self._combo = QComboBox()
        self._combo.setEditable(True)
        self._combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._combo.setPlaceholderText("选择或输入指令名…")
        self._combo.setToolTip("选择或输入指令名以查看相应说明。支持大小写不敏感、别名（如 ins_数字）。")
        self._combo.currentTextChanged.connect(self._on_combo_text_changed)
        self._combo.editTextChanged.connect(self._on_combo_text_changed)

        # 内容：HTML 展示标签
        self._label = QLabel("将光标放在指令上以查看帮助。")
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._label.setContentsMargins(10, 10, 10, 10)

        # 容器布局
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._combo)
        layout.addWidget(self._label)
        container.setLayout(layout)
        self.setWidget(container)

    def update_content(self, html_content: str):
        """用新的HTML内容更新帮助文本。"""
        self._label.setText(html_content)
        #print(f"[DEBUG] 帮助面板内容已更新。{html_content[:60]}...")

    def show_default(self):
        """显示默认的提示信息。"""
        self.update_content("将光标放在指令上以查看帮助。")

    # ==========================
    # 新增：下拉与接口方法
    # ==========================
    def set_completion_words(self, words: List[str]):
        """更新下拉框的候选项（去重+排序）。"""
        # 去重并按不区分大小写排序
        unique_sorted = sorted(set(words or []), key=lambda s: s.lower())
        # 保留当前文本，避免闪烁
        current_text = self._combo.currentText()
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItems(unique_sorted)
        # 恢复当前文本
        if current_text:
            self._combo.setEditText(current_text)
        self._combo.blockSignals(False)

    def set_get_doc_callback(self, cb: Optional[Callable[[str], str]]):
        """设置用于获取 HTML 文档的回调函数。"""
        self._get_doc_callback = cb

    def set_current_word(self, word: str):
        """在不触发查询的情况下，同步下拉框的显示文本。"""
        self._combo.blockSignals(True)
        self._combo.setEditText(word or "")
        self._combo.blockSignals(False)

    def _on_combo_text_changed(self, text: str):
        """当用户在下拉框中选择或输入内容时，尝试查询并展示说明。"""
        w = (text or "").strip()
        if not w:
            self.show_default()
            return
        html = ""
        if callable(self._get_doc_callback):
            try:
                html = self._get_doc_callback(w) or ""
            except Exception:
                html = ""
        if html:
            self.update_content(html)
        else:
            # 未命中则显示默认提示（可改为保留上一次内容）
            self.show_default()