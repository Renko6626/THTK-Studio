# app/widgets/sprite_preview.py

from PyQt6.QtWidgets import QScrollArea, QWidget, QLabel, QStackedWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor # <--- 新增导入

from .flow_layout import FlowLayout

class SpritePreviewPane(QScrollArea):
    """
    精灵预览面板。
    
    注意：此面板中的 SpritePreviewItem 会发出 'clicked(str)' 信号。
    需要在 MainWindow 中手动连接此信号以实现“点击跳转”功能。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        # 你的样式表很好，它负责滚动条和边框，保持它！
        self.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #222222;
            }
            QScrollBar:vertical {
                border: none;
                background: #2c2c2e;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #555;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self._stack = QStackedWidget()
        self.setWidget(self._stack)

        # --- vvv MODIFICATION START vvv ---

        # 创建一个深色的调色板，我们将复用它
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor("#222222"))

        # 1. 为占位符控件设置背景
        self._placeholder_widget = QWidget()
        self._placeholder_widget.setAutoFillBackground(True) # 必须启用此项
        self._placeholder_widget.setPalette(dark_palette)   # 应用深色调色板

        placeholder_label = QLabel("精灵预览区\n(加载脚本后将在此显示)", self._placeholder_widget)
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setStyleSheet("color: #888; font-size: 14pt;")

        layout_placeholder = FlowLayout(self._placeholder_widget)
        layout_placeholder.addWidget(placeholder_label)

        # 2. 为精灵容器控件设置背景
        self._sprite_container = QWidget()
        self._sprite_container.setAutoFillBackground(True) # 同样必须启用
        self._sprite_container.setPalette(dark_palette)   # 应用同一个深色调色板

        self.sprite_layout = FlowLayout(self._sprite_container, margin=6, spacing=6)

        # --- ^^^ MODIFICATION END ^^^ ---

        self._stack.addWidget(self._placeholder_widget)
        self._stack.addWidget(self._sprite_container)

        self.show_placeholder()
        
        
    # clear_previews, add_sprite_preview, show_placeholder 方法保持不变
    def clear_previews(self):
        while self.sprite_layout.count() > 0:
            item = self.sprite_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
    def add_sprite_preview(self, widget: QWidget):
        self._stack.setCurrentWidget(self._sprite_container)
        self.sprite_layout.addWidget(widget)

    def show_placeholder(self):
        self.clear_previews()
        self._stack.setCurrentWidget(self._placeholder_widget)