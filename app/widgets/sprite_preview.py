# app/widgets/sprite_preview.py

from PyQt6.QtWidgets import QScrollArea, QWidget, QLabel, QStackedWidget
from PyQt6.QtCore import Qt, QTimer
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
        # 滚动位置保存/恢复支持（必须在 __init__ 内）
        self._saved_scroll_value = 0
        self._restore_timer = QTimer(self)
        self._restore_timer.setSingleShot(True)
        self._restore_timer.timeout.connect(self._restore_scroll_position)
        self._bulk_updates = 0  # >0 表示批量更新中，延迟恢复滚动

        self.show_placeholder()
        
        
    # clear_previews, add_sprite_preview, show_placeholder 方法保持不变
    def clear_previews(self):
        # 保存当前滚动位置供后续恢复
        self._saved_scroll_value = self.verticalScrollBar().value()
        while self.sprite_layout.count() > 0:
            item = self.sprite_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        # 触发延迟恢复（若不在批量更新，立即调度；在批量中由结束时统一恢复）
        if self._bulk_updates == 0:
            self._schedule_scroll_restore()
        
    def add_sprite_preview(self, widget: QWidget):
        # 若用户首次添加项目，保存滚动
        if self._bulk_updates == 0 and self._saved_scroll_value == 0:
            self._saved_scroll_value = self.verticalScrollBar().value()
        self._stack.setCurrentWidget(self._sprite_container)
        self.sprite_layout.addWidget(widget)
        # 仅在非批量模式下调度恢复；批量模式结束后统一恢复
        if self._bulk_updates == 0:
            self._schedule_scroll_restore()

    def show_placeholder(self):
        # 如果已经是占位符，避免重复清空导致滚动复位
        if self._stack.currentWidget() is self._placeholder_widget:
            return
        self._saved_scroll_value = self.verticalScrollBar().value()
        self.clear_previews()
        self._stack.setCurrentWidget(self._placeholder_widget)
        if self._bulk_updates == 0:
            self._schedule_scroll_restore()

    # =============================
    # 批量更新辅助 API
    # =============================
    def begin_bulk_update(self):
        """开始一次批量刷新，期间不立即恢复滚动条。"""
        self._bulk_updates += 1
        # 捕获进入批量时的滚动位置
        if self._bulk_updates == 1:
            self._saved_scroll_value = self.verticalScrollBar().value()

    def end_bulk_update(self):
        """结束一次批量刷新，统一恢复滚动条。"""
        if self._bulk_updates > 0:
            self._bulk_updates -= 1
        if self._bulk_updates == 0:
            self._schedule_scroll_restore()

    # =============================
    # 内部：调度与恢复滚动位置
    # =============================
    def _schedule_scroll_restore(self):
        # 防抖：重新启动定时器（延迟 0ms，放到事件循环尾部执行）
        if self._restore_timer.isActive():
            self._restore_timer.stop()
        self._restore_timer.start(0)

    def _restore_scroll_position(self):
        sb = self.verticalScrollBar()
        if not sb:
            return
        # clamp 保存值到当前范围
        target = max(sb.minimum(), min(self._saved_scroll_value, sb.maximum()))
        sb.setValue(target)