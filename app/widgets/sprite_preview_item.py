# app/widgets/sprite_preview_item.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap, QCursor
from PyQt6.QtCore import Qt, pyqtSignal, QSize

class SpritePreviewItem(QWidget):
    """
    一个经过美化的、可交互的单个精灵预览控件。
    - 固定大小，内部图像会等比缩放。
    - 拥有现代化的深色主题和鼠标悬浮效果。
    - 可点击，并发出带有自身名称的信号。
    """
    clicked = pyqtSignal(str)
    
    # <--- MODIFICATION 1: 将尺寸进一步缩小，使其更紧凑 ---
    THUMBNAIL_SIZE = QSize(90, 90)

    def __init__(self, name: str, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.sprite_name = name

        self.setFixedSize(self.THUMBNAIL_SIZE)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # <--- MODIFICATION 2: 修复样式表选择器，确保高亮生效 ---
        # 将 "SpritePreviewItem" 改为 "QWidget" 来直接指向这个实例
        self.setStyleSheet("""
            QWidget {
                background-color: #2c2c2e;
                border-radius: 5px;
                border: 1px solid #444;
            }
            QWidget:hover {
                background-color: #3a3a3c;
                border: 1px solid #888;
            }
        """)

        layout = QVBoxLayout(self)
        # 减小边距以适应更小的尺寸
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        # 图像缩放逻辑会自动适应新的尺寸
        thumbnail = pixmap.scaled(
            self.THUMBNAIL_SIZE - QSize(10, 25), # 调整内部边距
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setPixmap(thumbnail)
        
        self.name_label = QLabel(self._get_elided_text(name))
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet("color: #bbb; border: none; background: transparent;")

        layout.addWidget(self.image_label, 1)
        layout.addWidget(self.name_label, 0)
        
        self.setToolTip(f"名称: {name}\n原始尺寸: {pixmap.width()}x{pixmap.height()}\n(点击跳转到定义)")
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.sprite_name)
        super().mousePressEvent(event)

    def _get_elided_text(self, text: str):
        metrics = self.fontMetrics()
        return metrics.elidedText(text, Qt.TextElideMode.ElideRight, self.width() - 10)