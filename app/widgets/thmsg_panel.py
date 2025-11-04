# app/widgets/msg_tool_panel.py

from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QPushButton, QLabel,
    QLineEdit, QHBoxLayout, QFileDialog, QGroupBox, QStyle, QComboBox, QCheckBox
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QIcon
from typing import Optional

# MSG 文件对应的游戏版本
MSG_GAME_VERSIONS = {
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
SUPPORTED_ENCODINGS = ["Shift-JIS", "UTF-8", "GBK"]

class MsgToolPanel(QDockWidget):
    """一个经过美化的、用于 thmsg 工作流的UI面板。"""
    # --- 信号定义 ---
    pack_requested = pyqtSignal()
    unpack_requested = pyqtSignal()
    thmsg_path_changed = pyqtSignal(str)
    ref_path_changed = pyqtSignal(str)
    insert_snippet_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("MSG 工作流", parent)
        self.setFloating(False)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable)

        # --- 统一的样式表 ---
        self.setStyleSheet("""
            QDockWidget { titlebar-close-icon: none; }
            QGroupBox {
                font-weight: bold; border: 1px solid #444; border-radius: 5px; margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px;
            }
            QLineEdit {
                background-color: #2b2b2b; border: 1px solid #555; color: #f0f0f0;
                padding: 4px; border-radius: 3px;
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

        # --- 内部控件 ---
        self._thmsg_path_input = QLineEdit()
        self._ref_path_input = QLineEdit()
        self._thmsg_path_input.textChanged.connect(self.thmsg_path_changed)
        self._ref_path_input.textChanged.connect(self.ref_path_changed)
        
        main_layout.addWidget(self._create_settings_group())
        main_layout.addWidget(self._create_actions_group())
        main_layout.addWidget(self._create_snippets_group()) # <--- 添加新的 snippets 组
        main_layout.addStretch()

        self.setWidget(container)

    # --- 公共方法 (用于外部设置和获取路径) ---
    def get_unpack_encoding(self) -> str:
        """获取解包时读取 .dmsg 文件所用的编码。"""
        return self._unpack_encoding_combo.currentText()

    def get_pack_encoding(self) -> str:
        """获取打包时写入 .dmsg 文件所用的编码。"""
        return self._pack_encoding_combo.currentText()
    # --- END NEW ---
    def get_thmsg_path(self) -> str:
        return self._thmsg_path_input.text()

    def set_thmsg_path(self, path: str):
        self._thmsg_path_input.setText(path)

    def get_ref_path(self) -> str:
        return self._ref_path_input.text()

    def set_ref_path(self, path: str):
        self._ref_path_input.setText(path)

    def get_selected_version(self) -> Optional[str]:
        if self._version_combo.currentIndex() == -1:
            return None
        return self._version_combo.currentData()
    def _create_snippets_group(self) -> QGroupBox:
        """创建包含常用指令快捷按钮的组。"""
        snippets_group = QGroupBox("快捷插入")
        layout = QVBoxLayout()

        # 定义按钮及其要插入的文本
        # \n 表示换行，{cursor} 是一个我们可以自定义的光标占位符
        snippets = {
            "玩家说话": "\tplayerFace({cursor})\n\tspeakerPlayer()\n\tbubblePos(112.0f;250.0f)\n\ttextAdd()",
            "Boss说话": "\tbossFace({cursor};0)\n\tspeakerBoss(0)\n\tbubblePos(356.0f;250.0f)\n\ttextAdd()",
            "添加对话": "\ttextAdd({cursor})",
            "清空文本": "\ttextClear()",
            "等待按键": "\ttextPause(600)",
        }

        for name, snippet in snippets.items():
            button = QPushButton(name)
            button.clicked.connect(lambda ch, s=snippet: self.insert_snippet_requested.emit(s))
            layout.addWidget(button)
            
        snippets_group.setLayout(layout)
        return snippets_group
    # --- END NEW ---
    # --- UI 构建辅助方法 ---
    def _create_settings_group(self) -> QGroupBox:
        settings_group = QGroupBox("路径设置")
        layout = QVBoxLayout()
        thmsg_row = self._create_path_row("Thmsg:", self._thmsg_path_input, self._browse_for_thmsg)
        ref_row = self._create_path_row("指令文档(json):", self._ref_path_input, self._browse_for_ref)
        layout.addLayout(thmsg_row)
        layout.addLayout(ref_row)
        
        settings_group.setLayout(layout)
        return settings_group
    # --- [NEW] 2. 新增获取解包模式的公共方法 ---
    def get_unpack_mode(self) -> str:
        """
        根据复选框的状态返回解包模式。
        :return: 'default' (带注释) 或 'clean' (不带注释)。
        """
        if self._include_comments_checkbox.isChecked():
            return "default"
        else:
            return "clean"
    # --- END NEW ---
    def _create_actions_group(self) -> QGroupBox:
        actions_group = QGroupBox("核心操作")
        layout = QVBoxLayout()
        
        # 版本选择 (保持不变)
        version_layout = QHBoxLayout()
        version_label = QLabel("游戏版本:")
        self._version_combo = QComboBox()
        for display_name, version_code in MSG_GAME_VERSIONS.items():
            self._version_combo.addItem(display_name, userData=version_code)
        version_layout.addWidget(version_label)
        version_layout.addWidget(self._version_combo)
        # --- [NEW] 1. 添加编码选择下拉框 ---
         # --- [NEW] 添加编码选择器 ---
        unpack_encoding_layout = QHBoxLayout()
        unpack_encoding_label = QLabel("解包编码:")
        self._unpack_encoding_combo = QComboBox()
        self._unpack_encoding_combo.addItems(SUPPORTED_ENCODINGS)
        self._unpack_encoding_combo.setToolTip("选择 .dmsg 文件的原始编码 (通常是 Shift-JIS)")
        unpack_encoding_layout.addWidget(unpack_encoding_label)
        unpack_encoding_layout.addWidget(self._unpack_encoding_combo)

        pack_encoding_layout = QHBoxLayout()
        pack_encoding_label = QLabel("打包编码:")
        self._pack_encoding_combo = QComboBox()
        self._pack_encoding_combo.addItems(SUPPORTED_ENCODINGS)
        self._pack_encoding_combo.setToolTip("选择要写入 .dmsg 文件的编码 (UTF-8 支持中文)")
        # 默认打包时选择 UTF-8
        utf8_index = self._pack_encoding_combo.findText("UTF-8")
        if utf8_index != -1:
            self._pack_encoding_combo.setCurrentIndex(utf8_index)
        pack_encoding_layout.addWidget(pack_encoding_label)
        pack_encoding_layout.addWidget(self._pack_encoding_combo)
        # --- END NEW ---
        # --- [NEW] 3. 添加模式选择复选框 ---
        self._include_comments_checkbox = QCheckBox("解包时包含注释")
        self._include_comments_checkbox.setChecked(True) # 默认勾选
        self._include_comments_checkbox.setToolTip("勾选后，解包生成的 .txt 文件会包含指令的描述信息。")
        # --- END NEW ---

        # 操作按钮 (保持不变)
        unpack_btn = QPushButton("解包 MSG 并编辑...")
        unpack_btn.setToolTip("选择一个 .msg 文件进行解包和翻译...")
        unpack_btn.clicked.connect(self.unpack_requested)

        pack_btn = QPushButton("打包当前脚本...")
        pack_btn.setToolTip("将当前打开的 .txt 脚本恢复并编译为 .msg 文件。")
        pack_btn.clicked.connect(self.pack_requested)

        # --- 将所有控件添加到布局中 ---
        layout.addLayout(version_layout)
        layout.addLayout(unpack_encoding_layout) # 添加解包编码UI
        layout.addLayout(pack_encoding_layout)   # 添加打包编码UI
        layout.addWidget(self._include_comments_checkbox) # 添加复选框
        
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
        label.setFixedWidth(75) # 稍微加宽以容纳 "Ref JSON:"
        row_layout.addWidget(label)
        row_layout.addWidget(line_edit)
        row_layout.addWidget(browse_btn)
        return row_layout

    # --- 槽函数 (文件浏览) ---
    def _browse_for_thmsg(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 thmsg.exe", "", "Executable Files (*.exe);;All Files (*)")
        if path:
            self._thmsg_path_input.setText(path)

    def _browse_for_ref(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择指令映射 JSON 文件", "", "JSON Files (*.json);;All Files (*)")
        if path:
            self._ref_path_input.setText(path)