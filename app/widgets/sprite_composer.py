# app/widgets/sprite_composer.py

from typing import Dict, Tuple
from PyQt6.QtWidgets import (
    QDialog, QWidget, QListWidget, QListWidgetItem, QPushButton,
    QHBoxLayout, QVBoxLayout, QGraphicsView, QGraphicsScene, QLabel, QSpinBox, QGroupBox
)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QBrush
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QGraphicsPixmapItem


class CheckeredGraphicsView(QGraphicsView):
    """
    带棋盘格透明背景的 QGraphicsView。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setBackgroundBrush(self._make_checker_brush())

    def _make_checker_brush(self) -> QBrush:
        tile_size = 16
        img = QImage(tile_size * 2, tile_size * 2, QImage.Format.Format_RGB32)
        img.fill(QColor("#aaaaaa"))
        painter = QPainter(img)
        painter.fillRect(0, 0, tile_size, tile_size, QColor("#dddddd"))
        painter.fillRect(tile_size, tile_size, tile_size, tile_size, QColor("#dddddd"))
        painter.end()
        pix = QPixmap.fromImage(img)
        return QBrush(pix)


class SpriteItem(QGraphicsPixmapItem):
    """可移动、可选择；移动后通知父窗口更新坐标控件。"""

    def __init__(self, name: str, pixmap: QPixmap, composer_window: 'SpriteComposerWindow'):
        super().__init__(pixmap)
        self.name = name
        self.composer_window = composer_window
        self.setFlags(
            QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable
        )

    def itemChange(self, change, value):
        # 当位置变化且该项目被选中时，刷新右侧坐标显示
        if change == QGraphicsPixmapItem.GraphicsItemChange.ItemPositionHasChanged:
            if self.isSelected():
                self.composer_window._update_coord_inputs_from_item(self)
        return super().itemChange(change, value)


class SpriteComposerWindow(QDialog):
    """
    组合预览窗口：
    - 左侧：所有可添加的精灵列表（来自当前解析数据）。
    - 右侧上方：QGraphicsView 场景，支持拖拽摆放。
    - 右侧下方：当前场景中的图层列表（可拖拽排序以改变 Z 值）。
    """

    def __init__(self, image_manager, parsed_data: Dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("组合预览（摆放与图层）")
        self.resize(900, 600)

        self.image_manager = image_manager
        self.parsed_data = parsed_data or {}

        # 名称 -> QPixmap 的缓存（避免重复生成）
        self._catalog_pixmaps: Dict[str, QPixmap] = {}

        # UI 组件
        self.catalog_list = QListWidget()
        self.catalog_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.btn_add = QPushButton("添加到场景")

        self.scene = QGraphicsScene(self)
        self.view = CheckeredGraphicsView(self.scene)
        self.view.setSceneRect(0, 0, 1024, 768)

        self.layer_label = QLabel("图层（顶部在上）：")
        self.layer_list = QListWidget()
        self.layer_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.layer_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)

        # 坐标输入区域
        coord_group = QGroupBox("选中精灵坐标")
        coord_layout = QHBoxLayout()
        self.spin_x = QSpinBox()
        self.spin_y = QSpinBox()
        for sp in (self.spin_x, self.spin_y):
            sp.setRange(-99999, 99999)
            sp.setAccelerated(True)
        self.spin_x.setPrefix("X: ")
        self.spin_y.setPrefix("Y: ")
        coord_layout.addWidget(self.spin_x)
        coord_layout.addWidget(self.spin_y)
        coord_group.setLayout(coord_layout)

        # 布局
        left = QVBoxLayout()
        left.addWidget(QLabel("可添加的精灵："))
        left.addWidget(self.catalog_list, 1)
        left.addWidget(self.btn_add)

        right = QVBoxLayout()
        right.addWidget(self.view, 4)
        right.addWidget(coord_group)
        right.addWidget(self.layer_label)
        right.addWidget(self.layer_list, 1)

        root = QHBoxLayout(self)
        left_panel = QWidget()
        left_panel.setLayout(left)
        right_panel = QWidget()
        right_panel.setLayout(right)

        root.addWidget(left_panel, 1)
        root.addWidget(right_panel, 3)

        # 信号连接
        self.btn_add.clicked.connect(self._on_add_clicked)
        self.layer_list.model().rowsMoved.connect(self._on_layers_reordered)
        self.scene.selectionChanged.connect(self._on_scene_selection_changed)
        self.spin_x.valueChanged.connect(self._on_coord_spin_changed)
        self.spin_y.valueChanged.connect(self._on_coord_spin_changed)

        # 初始化目录
        self._populate_catalog()

    # ------------------- 目录与加载 -------------------
    def _populate_catalog(self):
        """遍历 parsed_data，生成可添加精灵目录。"""
        self.catalog_list.clear()
        entries = self.parsed_data.get("entries", {})
        for entry_name, entry_data in entries.items():
            image_path = entry_data.get("image_path")
            if not image_path:
                continue
            x_off = entry_data.get('xOffset', entry_data.get('x_offset', 0))
            y_off = entry_data.get('yOffset', entry_data.get('y_offset', 0))
            base_w = entry_data.get('width')
            base_h = entry_data.get('height')

            for sprite_name, rect in entry_data.get("sprites", {}).items():
                full_name = f"{entry_name}/{sprite_name}"
                pixmap = self._get_pixmap(image_path, rect, x_off, y_off, base_w, base_h)
                if pixmap is None:
                    continue
                item = QListWidgetItem(full_name)
                self.catalog_list.addItem(item)

    def _get_pixmap(self, image_path: str, rect: Dict[str, int], x_off: int, y_off: int,
                    base_w, base_h) -> QPixmap | None:
        pil = self.image_manager.get_sprite_image_with_offset(
            image_path, rect, x_off, y_off, base_w, base_h
        )
        if pil is None:
            return None
        if pil.mode != "RGBA":
            pil = pil.convert("RGBA")
        qimg = QImage(pil.tobytes(), pil.width, pil.height, QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimg)

    # ------------------- 交互：添加与图层 -------------------
    def _on_add_clicked(self):
        item = self.catalog_list.currentItem()
        if not item:
            return
        name = item.text()
        pixmap = self._get_catalog_pixmap(name)
        if not pixmap:
            return

        sprite_item = SpriteItem(name, pixmap, self)
        # 默认放在场景中心附近
        center = self.view.sceneRect().center()
        sprite_item.setPos(center.x() - pixmap.width() / 2, center.y() - pixmap.height() / 2)
        # 设置到顶层
        top_z = self._top_z_value() + 1
        sprite_item.setZValue(top_z)
        self.scene.addItem(sprite_item)

        # 图层列表顶部添加（代表顶层）
        layer_item = QListWidgetItem(name)
        self.layer_list.insertItem(0, layer_item)
        self.layer_list.setCurrentRow(0)
        # 选择新添加的对象以显示坐标
        sprite_item.setSelected(True)
        self._update_coord_inputs_from_item(sprite_item)

    def _get_catalog_pixmap(self, full_name: str) -> QPixmap | None:
        if full_name in self._catalog_pixmaps:
            return self._catalog_pixmaps[full_name]
        # 如果未缓存，从 parsed_data 获取信息重新生成
        parts = full_name.split('/')
        if len(parts) < 2:
            return None
        entry_name, sprite_name = parts[0], '/'.join(parts[1:])
        entry = self.parsed_data.get("entries", {}).get(entry_name)
        if not entry:
            return None
        image_path = entry.get('image_path')
        rect = entry.get('sprites', {}).get(sprite_name)
        if not image_path or not rect:
            return None
        x_off = entry.get('xOffset', entry.get('x_offset', 0))
        y_off = entry.get('yOffset', entry.get('y_offset', 0))
        base_w = entry.get('width')
        base_h = entry.get('height')
        pixmap = self._get_pixmap(image_path, rect, x_off, y_off, base_w, base_h)
        if pixmap:
            self._catalog_pixmaps[full_name] = pixmap
        return pixmap

    def _top_z_value(self) -> float:
        max_z = 0.0
        for it in self.scene.items():
            z = it.zValue()
            if z > max_z:
                max_z = z
        return max_z

    def _on_layers_reordered(self, *args, **kwargs):
        """
        当图层列表拖拽排序后，根据新顺序更新场景中的 Z 值：
        列表顶部 -> 最大 Z；底部 -> 最小 Z。
        """
        names_in_order = [self.layer_list.item(i).text() for i in range(self.layer_list.count())]
        # 从底部开始赋值较小 Z，逐步增大
        z = 0
        for name in reversed(names_in_order):
            for it in self.scene.items():
                if isinstance(it, QGraphicsPixmapItem) and getattr(it, 'name', None) == name:
                    it.setZValue(z)
            z += 1

    # ------------------- 坐标同步 -------------------
    def _on_scene_selection_changed(self):
        selected = [it for it in self.scene.selectedItems() if isinstance(it, SpriteItem)]
        if not selected:
            # 无选择时禁用输入框
            self.spin_x.blockSignals(True)
            self.spin_y.blockSignals(True)
            self.spin_x.setValue(0)
            self.spin_y.setValue(0)
            self.spin_x.blockSignals(False)
            self.spin_y.blockSignals(False)
            self.spin_x.setEnabled(False)
            self.spin_y.setEnabled(False)
            return
        self.spin_x.setEnabled(True)
        self.spin_y.setEnabled(True)
        self._update_coord_inputs_from_item(selected[0])

    def _update_coord_inputs_from_item(self, item: SpriteItem):
        # 将图元的左上角坐标写入 spinbox
        self.spin_x.blockSignals(True)
        self.spin_y.blockSignals(True)
        self.spin_x.setValue(int(item.x()))
        self.spin_y.setValue(int(item.y()))
        self.spin_x.blockSignals(False)
        self.spin_y.blockSignals(False)

    def _on_coord_spin_changed(self):
        selected = [it for it in self.scene.selectedItems() if isinstance(it, SpriteItem)]
        if not selected:
            return
        item = selected[0]
        # 更新位置；保持左上角定位
        item.setPos(self.spin_x.value(), self.spin_y.value())
        # 不需要调用 _update_coord_inputs_from_item 以免循环；itemChange 会在拖动时更新但不是在这里
