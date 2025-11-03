# app/widgets/project_info_panel.py

from PyQt6.QtWidgets import QDockWidget, QTextBrowser
from PyQt6.QtCore import Qt
from pathlib import Path
from typing import Optional

class ProjectInfoPanel(QDockWidget):
    """
    一个用于显示“项目整体说明”的可停靠面板。
    支持从内置资源或用户提供的 HTML 文本加载。
    """
    def __init__(self, title: str = "项目说明", parent=None):
        super().__init__(title, parent)
        self.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self._viewer = QTextBrowser(self)
        self._viewer.setOpenExternalLinks(True)
        self._viewer.setOpenLinks(True)
        self._viewer.setStyleSheet("QTextBrowser { padding: 10px; }")
        self.setWidget(self._viewer)

    def set_overview_html(self, html: str):
        """直接设置要展示的 HTML 内容。"""
        self._viewer.setHtml(html or "")

    def load_from_file(self, file_path: str) -> bool:
        """从给定路径加载 HTML；返回是否成功。"""
        try:
            p = Path(file_path)
            if p.is_file():
                self._viewer.setHtml(p.read_text(encoding="utf-8", errors="ignore"))
                return True
        except Exception:
            pass
        return False

    def load_default(self, base_dir: Optional[Path] = None) -> None:
        """尝试加载内置 resources/project_overview.html；失败则显示占位说明。"""
        # 基于运行目录推测资源路径（与 Settings 的资源规则保持一致约定）
        try:
            if base_dir is None:
                base_dir = Path(__file__).parent.parent.parent  # 项目根目录
            res = base_dir / "resources" / "project_overview.html"
            if not self.load_from_file(str(res)):
                self._viewer.setHtml("""
                    <h2>项目整体说明</h2>
                    <p>未找到内置概览文件 <code>resources/project_overview.html</code>。
                    你可以在该路径创建一个 HTML 文件来自定义此面板的内容。</p>
                    <ul>
                        <li>在右侧帮助面板中可查看指令级说明。</li>
                        <li>在 ECL 面板中可进行解包/打包与结构大纲浏览。</li>
                        <li>支持悬浮提示、代码补全与基本语法检查。</li>
                    </ul>
                """)
        except Exception:
            self._viewer.setHtml("<h2>项目整体说明</h2><p>加载默认说明失败。</p>")
