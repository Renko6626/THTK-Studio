# app/widgets/help_panel.py

from PyQt6.QtWidgets import (
    QDockWidget, QTextBrowser, QComboBox, QWidget, QVBoxLayout
)
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import Qt, QUrl
from typing import Callable, List, Optional

class HelpPanel(QDockWidget):
    """
    一个外观现代化的、可停靠的窗口，用于美观地显示指令的帮助信息。
    它使用 QTextBrowser 来支持丰富的 HTML 内容渲染。
    """

    # --- QSS 样式定义 ---
    # 我们将所有样式集中在此，方便修改
    STYLESHEET = """
        /* 整个帮助面板容器的样式 */
        QWidget#HelpPanelContainer {
            background-color: #2c313a; /* 深灰蓝背景 */
            border-radius: 4px;
        }

        /* 下拉框样式 */
        QComboBox {
            background-color: #21252b; /* 更深的背景 */
            color: #dbe1ec; /* 浅色文字 */
            border: 1px solid #3c424d;
            border-radius: 4px;
            padding: 5px 8px;
            font-size: 14px;
        }
        QComboBox:hover {
            border-color: #5c677a;
        }
        /* 编辑框获取焦点时的样式 */
        QComboBox:focus {
            border-color: #61afef; /* 蓝色高亮 */
        }
        /* 下拉箭头样式 */
        QComboBox::down-arrow {
            image: url(app/assets/icons/chevron-down.svg); /* 需要一个向下的箭头图标 */
            width: 12px;
            height: 12px;
        }
        QComboBox::drop-down {
            border: none;
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
        }
        /* 下拉列表的样式 */
        QComboBox QAbstractItemView {
            background-color: #21252b;
            color: #dbe1ec;
            border: 1px solid #3c424d;
            selection-background-color: #3b4048; /* 选中项背景 */
            outline: 0px; /* 去除选中虚线框 */
        }

        /* 内容浏览器样式 */
        QTextBrowser {
            background-color: transparent; /* 透明背景，继承容器颜色 */
            color: #dbe1ec;
            border: none; /* 无边框 */
            font-size: 14px;
            padding: 8px;
        }
    """

    # --- HTML 内容的内部样式 ---
    # 定义 h1, p, code 等标签在 QTextBrowser 中如何显示
    HTML_DOCUMENT_STYLE = """
        h1 {
            color: #61afef; /* 蓝色标题 */
            font-size: 18px;
            font-weight: bold;
            border-bottom: 1px solid #3c424d;
            padding-bottom: 5px;
            margin-bottom: 10px;
        }
        p {
            line-height: 1.6;
        }
        code {
            background-color: #21252b;
            color: #e5c07b; /* 黄色代码 */
            border-radius: 4px;
            padding: 2px 5px;
            font-family: "Courier New", Courier, monospace;
        }
        b, strong {
            color: #c678dd; /* 紫色加粗 */
        }
    """

    def __init__(self, title="帮助", parent=None):
        super().__init__(title, parent)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        self._get_doc_callback: Optional[Callable[[str], str]] = None

        # --- UI 组件 ---
        # 1. 下拉框
        self._combo = QComboBox()
        self._combo.setEditable(True)
        self._combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._combo.setPlaceholderText("搜索指令...")
        self._combo.setToolTip("输入或选择指令以查看说明")
        self._combo.currentTextChanged.connect(self._on_combo_text_changed)

        # 2. 内容显示区 (使用 QTextBrowser)
        self._doc_browser = QTextBrowser()
        self._doc_browser.setReadOnly(True)
        self._doc_browser.setOpenExternalLinks(True) # 自动用系统浏览器打开 http:// 链接
        self._doc_browser.document().setDefaultStyleSheet(self.HTML_DOCUMENT_STYLE) # 应用HTML内部样式

        # --- 布局和样式 ---
        container = QWidget(self)
        container.setObjectName("HelpPanelContainer") # 为QSS选择器设置对象名
        container.setStyleSheet(self.STYLESHEET) # 应用组件样式

        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.addWidget(self._combo)
        layout.addWidget(self._doc_browser)
        
        self.setWidget(container)
        self.show_default()

    def update_content(self, html_content: str):
        """用新的HTML内容更新帮助文本。"""
        self._doc_browser.setHtml(html_content)

    def show_default(self):
        """显示默认的提示信息。"""
        self.update_content(
            """
            <h1>帮助面板</h1>
            <p>将光标悬停在代码中的指令或变量上，即可在此处查看详细说明。</p>
            <p>您也可以在<b>上方搜索框</b>中直接输入关键字进行查询。</p>
            """
        )
    
    def show_not_found(self, word: str):
        """当找不到文档时显示提示。"""
        self.update_content(f"<h1>未找到</h1><p>没有找到关于 <code>{word}</code> 的文档。</p>")

    def set_completion_words(self, words: List[str]):
        """更新下拉框的候选项。"""
        unique_sorted = sorted(set(words or []), key=str.lower)
        current_text = self._combo.currentText()
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItems(unique_sorted)
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
        # 同步显示内容
        self._on_combo_text_changed(word)

    def _on_combo_text_changed(self, text: str):
        """当用户在下拉框中选择或输入内容时，查询并展示说明。"""
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
            self.show_not_found(w)