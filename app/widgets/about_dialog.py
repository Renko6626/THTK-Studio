# app/widgets/about_dialog.py

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox
from PyQt6.QtCore import Qt
from pathlib import Path
from typing import Optional

class AboutDialog(QDialog):
    """
    一个“关于 / 项目整体说明”的弹窗。
    使用 QTextBrowser 展示 resources/project_overview.html 的内容。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于 - 项目整体说明")
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)  # 复用
        self.setMinimumSize(820, 600)

        layout = QVBoxLayout(self)

        self.viewer = QTextBrowser(self)
        self.viewer.setOpenExternalLinks(True)
        self.viewer.setOpenLinks(True)
        self.viewer.setStyleSheet("QTextBrowser { padding: 10px; }")
        layout.addWidget(self.viewer)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=self)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def set_overview_html(self, html: str):
        self.viewer.setHtml(html or "")

    def load_from_file(self, file_path: str) -> bool:
        try:
            p = Path(file_path)
            if p.is_file():
                self.viewer.setHtml(p.read_text(encoding="utf-8", errors="ignore"))
                return True
        except Exception:
            pass
        return False

    def load_default(self, base_dir: Optional[Path] = None) -> None:
        """尝试加载内置 resources/project_overview.html；失败则显示占位说明。"""
        try:
            if base_dir is None:
                base_dir = Path(__file__).parent.parent.parent  # 项目根目录
            res = base_dir / "resources" / "project_overview.html"
            if not self.load_from_file(str(res)):
                self.viewer.setHtml(
                    """
                    <h2>项目整体说明</h2>
                    <p>未找到内置概览文件 <code>resources/project_overview.html</code>。
                    你可以在该路径创建一个 HTML 文件来自定义此弹窗内容。</p>
                    <ul>
                        <li>右侧帮助面板可查看指令级说明，下拉框支持检索。</li>
                        <li>ECL 面板提供解包/打包、结构大纲与跳转。</li>
                        <li>支持悬浮提示、代码补全与基本语法检查。</li>
                    </ul>
                    """
                )
        except Exception:
            self.viewer.setHtml("<h2>项目整体说明</h2><p>加载默认说明失败。</p>")
