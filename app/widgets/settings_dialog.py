# app/widgets/settings_dialog.py

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QCheckBox, QSpinBox, QDialogButtonBox, QLabel
)

from typing import Optional

from ..core.settings import Settings


class SettingsDialog(QDialog):
    """
    简单的首选项对话框：提供自动保存与常用 UI 偏好设置。
    """
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("首选项")
        self.setModal(True)
        self._settings = settings
        self._build_ui()
        self._load_from_settings()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # 自动保存启用
        self.chk_autosave_enabled = QCheckBox("启用自动保存")
        form.addRow(self.chk_autosave_enabled)

        # 自动保存间隔（秒）
        self.spin_autosave_sec = QSpinBox()
        self.spin_autosave_sec.setRange(5, 600)
        self.spin_autosave_sec.setSingleStep(5)
        self.spin_autosave_sec.setSuffix(" 秒")
        form.addRow(QLabel("自动保存间隔"), self.spin_autosave_sec)

        # 失去焦点时自动保存
        self.chk_autosave_focusout = QCheckBox("窗口失去焦点时自动保存")
        form.addRow(self.chk_autosave_focusout)

        # 字体：仅等宽（默认）
        self.chk_monospaced_default = QCheckBox("字体下拉默认仅显示等宽")
        form.addRow(self.chk_monospaced_default)

        # 小地图设置
        self.chk_minimap_enabled = QCheckBox("显示小地图 (Minimap)")
        form.addRow(self.chk_minimap_enabled)

        self.spin_minimap_width = QSpinBox()
        self.spin_minimap_width.setRange(32, 200)
        self.spin_minimap_width.setSingleStep(8)
        self.spin_minimap_width.setSuffix(" px")
        form.addRow(QLabel("小地图宽度"), self.spin_minimap_width)

        layout.addLayout(form)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_from_settings(self):
        d = self._settings.data
        self.chk_autosave_enabled.setChecked(bool(d.get("autosave_enabled", True)))
        self.spin_autosave_sec.setValue(int(d.get("autosave_interval_sec", 30)))
        self.chk_autosave_focusout.setChecked(bool(d.get("autosave_on_focus_out", True)))
        self.chk_monospaced_default.setChecked(bool(d.get("ui_monospaced_only_default", False)))
        self.chk_minimap_enabled.setChecked(bool(d.get("ui_minimap_enabled", True)))
        self.spin_minimap_width.setValue(int(d.get("ui_minimap_width", 64)))

    def apply_to_settings(self):
        d = self._settings.data
        d["autosave_enabled"] = self.chk_autosave_enabled.isChecked()
        d["autosave_interval_sec"] = int(self.spin_autosave_sec.value())
        d["autosave_on_focus_out"] = self.chk_autosave_focusout.isChecked()
        d["ui_monospaced_only_default"] = self.chk_monospaced_default.isChecked()
        d["ui_minimap_enabled"] = self.chk_minimap_enabled.isChecked()
        d["ui_minimap_width"] = int(self.spin_minimap_width.value())
        self._settings.save()

    # 覆盖 accept 以在关闭前保存
    def accept(self):
        self.apply_to_settings()
        super().accept()
