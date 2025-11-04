# app/widgets/thanm_panel.py

from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QPushButton, QLabel,
    QLineEdit, QHBoxLayout, QFileDialog, QGroupBox, QStyle, QComboBox
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QIcon
from typing import Optional

# <--- 修正游戏名称以匹配版本号 ---
GAME_VERSIONS = {
    "东方锦上京 (th20)": "20",
    "东方兽王园 (th19)": "19",
    "弹幕狂的黑市 (th18.5)": "18.5",
    "东方虹龙洞 (th18)": "18",
    "东方鬼形兽 (th17)": "17",
    "秘封噩梦日记 (th16.5)": "16.5",
    "东方天空璋 (th16)": "16",
    "东方绀珠传 (th15)": "15",
    "弹幕天邪鬼 (th14.3)": "14.3",
    "东方辉针城 (th14)": "14",
    "东方神灵庙 (th13)": "13",
    "妖精大战争 (th12.8)": "12.8",
    "东方文花帖DS (th12.5)": "12.5",
    "东方星莲船 (th12)": "12",
    "东方地灵殿 (th11)": "11",
    "东方风神录 (th10)": "10",
    "东方文花帖 (th9.5)": "9.5",
    "东方花映塚 (th09)": "9",
    "东方永夜抄 (th08)": "8",
    "东方妖妖梦 (th07)": "7",
    "东方红魔乡 (th06)": "6",
}

class ThanmPanel(QDockWidget):
    """一个经过美化的、用于 thanm 工作流的UI面板。"""
    # --- 信号定义 (保持不变) ---
    pack_requested = pyqtSignal()
    unpack_requested = pyqtSignal()
    thanm_path_changed = pyqtSignal(str)
    anmm_path_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("Thanm 工作流", parent)
        self.setFloating(False)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        # 面板整体提示
        self.setToolTip("使用 thanm.exe 与 .anmm 映射进行 ANM 图像包的解包与打包。")

        # --- 样式表 (保持不变) ---
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
                background-color: #555; border: 1px solid #666; padding: 6px; border-radius: 3px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover { 
                background-color: #666; 
            }
            QPushButton:pressed { 
                background-color: #444; /* 按下时颜色变得更深一些 */
                border-color: #555;
            }
        """)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(15)

        # --- 内部控件 (保持不变) ---
        self._thanm_path_input = QLineEdit()
        self._anmm_path_input = QLineEdit()
        self._thanm_path_input.textChanged.connect(self.thanm_path_changed)
        self._anmm_path_input.textChanged.connect(self.anmm_path_changed)

        main_layout.addWidget(self._create_settings_group())
        main_layout.addWidget(self._create_actions_group())
        main_layout.addStretch()

        self.setWidget(container)

    # --- 公共方法 (保持不变) ---
    def get_thanm_path(self) -> str:
        return self._thanm_path_input.text()

    def set_thanm_path(self, path: str):
        self._thanm_path_input.setText(path)

    def get_anmm_path(self) -> str:
        return self._anmm_path_input.text()

    def set_anmm_path(self, path: str):
        self._anmm_path_input.setText(path)

    def get_selected_version(self) -> Optional[str]:
        """获取当前选择的游戏版本号，如果没有选择则返回 None。"""
        if self._version_combo.currentIndex() == -1:
            return None
        return self._version_combo.currentData()

    # --- UI 构建辅助方法 (保持不变) ---
    def _create_settings_group(self) -> QGroupBox:
        settings_group = QGroupBox("路径设置")
        settings_group.setToolTip("配置工具与映射路径：\n- Thanm: THTK 的 thanm.exe，可执行编解包\n- Anmm: 指令/资源映射文件（.anmm），影响反编译与重编译的符号名称")
        layout = QVBoxLayout()
        thanm_row = self._create_path_row("Thanm:", self._thanm_path_input, self._browse_for_thanm)
        anmm_row = self._create_path_row("Anmm:", self._anmm_path_input, self._browse_for_anmm)
        layout.addLayout(thanm_row)
        layout.addLayout(anmm_row)
        settings_group.setLayout(layout)
        return settings_group

    def _create_actions_group(self) -> QGroupBox:
        actions_group = QGroupBox("核心操作")
        actions_group.setToolTip("选择游戏版本后，可进行 ANM 的解包与当前脚本的打包。")
        layout = QVBoxLayout()
        
        version_layout = QHBoxLayout()
        version_label = QLabel("游戏版本:")
        version_label.setToolTip("选择需要操作的东方游戏版本，对应 thanm 的打包/解包参数。")
        self._version_combo = QComboBox()
        self._version_combo.setToolTip("不同版本的 ANM 格式略有差异，请与目标文件匹配。")
        for display_name, version_code in GAME_VERSIONS.items():
            self._version_combo.addItem(display_name, userData=version_code)
        
        version_layout.addWidget(version_label)
        version_layout.addWidget(self._version_combo)

        unpack_btn = QPushButton("解包 ANM 并编辑...")
        unpack_btn.setToolTip("从 .anm 文件提取脚本/图像等资源并转为可编辑文本。\n提示：请先设置 thanm.exe 与版本，以获得最佳兼容性。")
        unpack_btn.clicked.connect(self.unpack_requested)

        pack_btn = QPushButton("打包当前脚本...")
        pack_btn.setToolTip("把当前编辑的文本（指令/资源清单）重新打包为 .anm。\n提示：请确保与解包版本一致以避免不兼容。")
        pack_btn.clicked.connect(self.pack_requested)

        layout.addLayout(version_layout)
        layout.addWidget(unpack_btn)
        layout.addWidget(pack_btn)
        actions_group.setLayout(layout)
        return actions_group

    def _create_path_row(self, label_text: str, line_edit: QLineEdit, browse_func) -> QHBoxLayout:
        row_layout = QHBoxLayout()
        line_edit.setPlaceholderText("自动检测或手动指定...")
        # 根据行标签设置更具体的提示
        if label_text.startswith("Thanm"):
            line_edit.setToolTip("thanm.exe 的完整路径（THTK 工具）。用于 ANM 的解包/打包。")
        elif label_text.startswith("Anmm"):
            line_edit.setToolTip(".anmm 映射文件路径。用于映射指令/资源名称，影响反编译显示与打包解析。")
        style = self.style()
        browse_icon = QIcon(style.standardPixmap(QStyle.StandardPixmap.SP_DirOpenIcon))
        browse_btn = QPushButton(browse_icon, "")
        browse_btn.setFixedSize(30, 30)
        browse_btn.clicked.connect(browse_func)
        if label_text.startswith("Thanm"):
            browse_btn.setToolTip("选择 thanm.exe 可执行文件")
        elif label_text.startswith("Anmm"):
            browse_btn.setToolTip("选择 .anmm 映射文件")
        label = QLabel(label_text)
        if label_text.startswith("Thanm"):
            label.setToolTip("THTK 的 thanm 工具路径")
        elif label_text.startswith("Anmm"):
            label.setToolTip("ANMM 映射文件路径")
        label.setFixedWidth(50)
        row_layout.addWidget(label)
        row_layout.addWidget(line_edit)
        row_layout.addWidget(browse_btn)
        return row_layout

    # --- 槽函数 (保持不变) ---
    def _browse_for_thanm(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 thanm.exe", "", "Executable Files (*.exe);;All Files (*)")
        if path:
            self._thanm_path_input.setText(path)

    def _browse_for_anmm(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 .anmm 映射文件", "", "ANMM Files (*.anmm);;All Files (*)")
        if path:
            self._anmm_path_input.setText(path)