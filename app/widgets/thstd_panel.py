# app/widgets/thstd_panel.py

from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QPushButton, QLabel,
    QLineEdit, QHBoxLayout, QFileDialog, QGroupBox, QStyle, QComboBox, QCheckBox
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QIcon
from typing import Optional

# 游戏版本字典，可以从其他地方导入或在此处定义
GAME_VERSIONS = {
    "东方锦上京 (th20)": "20",
    "东方兽王园 (th19)": "19",
    "东方虹龙洞 (th18)": "18",
    "东方鬼形兽 (th17)": "17",
    "东方天空璋 (th16)": "16",
    "东方绀珠传 (th15)": "15",
    "东方辉针城 (th14)": "14",
    "东方神灵庙 (th13)": "13",
    "东方星莲船 (th12)": "12",
}

class ThstdPanel(QDockWidget):
    """一个用于 thstd 工作流的UI面板。"""
    # 定义信号
    pack_requested = pyqtSignal()
    unpack_requested = pyqtSignal()
    thstd_path_changed = pyqtSignal(str)
    ref_path_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("STD 工作流", parent)
        self.setFloating(False)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable)

        # 设置样式
        self.setStyleSheet("""
            QDockWidget { titlebar-close-icon: none; }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
            QLineEdit {
                background-color: #2b2b2b;
                border: 1px solid #555;
                color: #f0f0f0;
                padding: 4px;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #555;
                border: 1px solid #666;
                padding: 6px;
                border-radius: 3px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #666; }
            QPushButton:pressed { 
                background-color: #444; /* 按下时颜色变得更深一些 */
                border-color: #555;
            }
        """)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(15)

        # 创建内部控件
        self._thstd_path_input = QLineEdit()
        self._ref_path_input = QLineEdit()
        self._thstd_path_input.textChanged.connect(self.thstd_path_changed)
        self._ref_path_input.textChanged.connect(self.ref_path_changed)

        main_layout.addWidget(self._create_settings_group())
        main_layout.addWidget(self._create_actions_group())
        main_layout.addStretch()

        self.setWidget(container)

    # --- 公共方法 ---
    def get_thstd_path(self) -> str:
        return self._thstd_path_input.text()

    def set_thstd_path(self, path: str):
        self._thstd_path_input.setText(path)

    def get_ref_path(self) -> str:
        return self._ref_path_input.text()

    def set_ref_path(self, path: str):
        self._ref_path_input.setText(path)

    def get_selected_version(self) -> Optional[str]:
        """获取当前选择的游戏版本号，如果没有选择则返回 None。"""
        if self._version_combo.currentIndex() == -1:
            return None
        return self._version_combo.currentData()

    def get_unpack_mode(self) -> str:
        """获取解包模式: 'default' (包含注释) 或 'clean' (不包含注释)。"""
        if hasattr(self, "_include_comments_checkbox") and self._include_comments_checkbox.isChecked():
            return "default"
        return "clean"

    # --- UI 构建辅助方法 ---
    def _create_settings_group(self) -> QGroupBox:
        settings_group = QGroupBox("路径设置")
        layout = QVBoxLayout()
        thstd_row = self._create_path_row("Thstd:", self._thstd_path_input, self._browse_for_thstd)
        ref_row = self._create_path_row("指令文档(json):", self._ref_path_input, self._browse_for_ref)
        layout.addLayout(thstd_row)
        layout.addLayout(ref_row)
        settings_group.setLayout(layout)
        return settings_group

    def _create_actions_group(self) -> QGroupBox:
        actions_group = QGroupBox("核心操作")
        layout = QVBoxLayout()
        
        version_layout = QHBoxLayout()
        version_label = QLabel("游戏版本:")
        self._version_combo = QComboBox()
        for display_name, version_code in GAME_VERSIONS.items():
            self._version_combo.addItem(display_name, userData=version_code)
        
        version_layout.addWidget(version_label)
        version_layout.addWidget(self._version_combo)

        # 解包模式复选框：与 thmsg 面板保持一致
        self._include_comments_checkbox = QCheckBox("解包时包含注释")
        self._include_comments_checkbox.setChecked(True)
        self._include_comments_checkbox.setToolTip("勾选后，解包生成的 .txt 文件会包含指令的描述信息。")

        unpack_btn = QPushButton("解包 STD 并编辑...")
        unpack_btn.setToolTip("选择一个 .std 文件进行解包...")
        unpack_btn.clicked.connect(self.unpack_requested)

        pack_btn = QPushButton("打包当前脚本...")
        pack_btn.setToolTip("将当前打开的指令脚本打包成一个新的 .std 文件。")
        pack_btn.clicked.connect(self.pack_requested)

        layout.addLayout(version_layout)
        layout.addWidget(self._include_comments_checkbox)
        layout.addWidget(unpack_btn)
        layout.addWidget(pack_btn)
        actions_group.setLayout(layout)
        return actions_group

    def _create_path_row(self, label_text: str, line_edit: QLineEdit, browse_func) -> QHBoxLayout:
        row_layout = QHBoxLayout()
        line_edit.setPlaceholderText("自动检测或手动指定...")
        style = self.style()
        browse_icon = QIcon(style.standardPixmap(QStyle.StandardPixmap.SP_DirOpenIcon))
        browse_btn = QPushButton(browse_icon, "")
        browse_btn.setFixedSize(30, 30)
        browse_btn.clicked.connect(browse_func)
        label = QLabel(label_text)
        label.setFixedWidth(75)
        row_layout.addWidget(label)
        row_layout.addWidget(line_edit)
        row_layout.addWidget(browse_btn)
        return row_layout

    # --- 槽函数 ---
    def _browse_for_thstd(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 thstd.exe", "", "Executable Files (*.exe);;All Files (*)")
        if path:
            self._thstd_path_input.setText(path)
    def _browse_for_ref(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 thstd_ref.json", "", "JSON Files (*.json);;All Files (*)")
        if path:
            self._ref_path_input.setText(path)
