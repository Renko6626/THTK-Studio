# app/widgets/sprite_preview_item.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
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
    
    THUMBNAIL_SIZE = QSize(120, 120)  # 稍微增宽，留出多行文字空间

    def __init__(self, name: str, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.sprite_name = name

        # 仅固定宽度，让高度可随文字自动扩展
        self.setFixedWidth(self.THUMBNAIL_SIZE.width())
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

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
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        # 图像缩放逻辑会自动适应新的尺寸
        available_img_size = QSize(self.THUMBNAIL_SIZE.width() - 10, self.THUMBNAIL_SIZE.height() - 40)
        thumbnail = pixmap.scaled(
            available_img_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setPixmap(thumbnail)

        self.name_label = QLabel(name)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet("color: #ccc; border: none; background: transparent; font-size: 10pt;")
        self.name_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        layout.addWidget(self.image_label, 1)
        layout.addWidget(self.name_label, 0)

        self.setToolTip(f"名称: {name}\n原始尺寸: {pixmap.width()}x{pixmap.height()}\n(点击跳转到定义)")
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.sprite_name)
        super().mousePressEvent(event)

    # 已不再需要省略号，保留方法但直接返回原文本以兼容旧引用
    def _get_elided_text(self, text: str):
        return text