# app/widgets/thecl_panel.py

from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QPushButton, QLabel,
    QLineEdit, QHBoxLayout, QFileDialog, QGroupBox, QStyle, QComboBox, QCheckBox, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIcon
from typing import Optional, Dict

# 适用于ECL脚本的游戏版本字典
# 东方系列从TH06到TH18都使用了ECL
ECL_GAME_VERSIONS = {
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

class TheclPanel(QDockWidget):
    """一个用于 thecl 工作流的UI面板。"""
    # 定义信号
    pack_requested = pyqtSignal()
    unpack_requested = pyqtSignal()
    thecl_path_changed = pyqtSignal(str)
    eclmap_path_changed = pyqtSignal(str)
    thecl_ref_path_changed = pyqtSignal(str)
    outline_jump_requested = pyqtSignal(int)
    # 自定义数据Role：用于给条目存储稳定的key
    KEY_ROLE = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent=None):
        super().__init__("ECL 工作流", parent)
        self.setFloating(False)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        # 面板整体提示
        self.setToolTip("使用 thecl.exe 与 eclmap/thecl_ref.json 进行 ECL 脚本的解包与打包，并提供结构大纲/跳转/过滤等辅助功能。")

        # 样式与 thstd_panel 保持一致
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
                background-color: #444;
                border-color: #555;
            }
            QCheckBox { margin-top: 5px; }
            QTreeWidget {
                background-color: #1f1f1f;
                border: 1px solid #3a3a3a;
                color: #e0e0e0;
                selection-background-color: #2d5a9b;
                selection-color: white;
                outline: none;
                border-radius: 4px;
            }
            QTreeWidget::item {
                height: 22px;
            }
            QTreeWidget::item:selected {
                background: #2d5a9b;
                color: #ffffff;
            }
            QTreeWidget::item:hover {
                background: #2a2a2a;
            }
        """)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(15)

        # 创建内部控件
        self._thecl_path_input = QLineEdit()
        self._eclmap_path_input = QLineEdit()
        self._thecl_ref_path_input = QLineEdit()
        self._thecl_path_input.textChanged.connect(self.thecl_path_changed)
        self._eclmap_path_input.textChanged.connect(self.eclmap_path_changed)
        self._thecl_ref_path_input.textChanged.connect(self.thecl_ref_path_changed)

        # 大纲树
        self._outline_tree = QTreeWidget()
        self._outline_tree.setHeaderHidden(True) # 隐藏表头
        self._outline_tree.setAlternatingRowColors(True)
        self._outline_tree.setIndentation(18)
        self._outline_tree.setUniformRowHeights(True)
        self._outline_tree.setAnimated(True)
        self._outline_tree.setMinimumHeight(180)
        self._outline_tree.itemDoubleClicked.connect(self._on_outline_item_jump)
        self._outline_tree.setExpandsOnDoubleClick(True)

        # 过滤输入框
        self._outline_filter = QLineEdit()
        self._outline_filter.setPlaceholderText("过滤函数/标签...")
        self._outline_filter.textChanged.connect(self._filter_outline)

        # 创建选项复选框
        self._use_address_info_checkbox = QCheckBox("解包时添加地址信息 (-x)")
        self._raw_dump_checkbox = QCheckBox("原始转储，不进行代码转换 (-r)")
        self._simple_mode_checkbox = QCheckBox("简单打包模式 (-s)")

        main_layout.addWidget(self._create_settings_group())
        main_layout.addWidget(self._create_actions_group())
        # 大纲面板将作为单独的 Dock 放在主窗口右侧，这里不再加入左侧布局
        main_layout.addStretch()

        self.setWidget(container)

        # ---- 大纲树状态缓存（用于避免用户展开/折叠被刷新时重置）----
        self._outline_expanded_keys = set()
        self._outline_selected_key = None
        self._outline_scroll_value = 0
        self._outline_initialized = False

    # --- 公共方法 ---
    def get_thecl_path(self) -> str:
        return self._thecl_path_input.text()

    def set_thecl_path(self, path: str):
        self._thecl_path_input.setText(path)

    def get_eclmap_path(self) -> str:
        return self._eclmap_path_input.text()

    def set_eclmap_path(self, path: str):
        self._eclmap_path_input.setText(path)

    def get_ref_path(self) -> str:
        return self._thecl_ref_path_input.text()

    def set_ref_path(self, path: str):
        self._thecl_ref_path_input.setText(path)

    def get_selected_version(self) -> Optional[str]:
        """获取当前选择的游戏版本号，如果没有选择则返回 None。"""
        if self._version_combo.currentIndex() == -1:
            return None
        return self._version_combo.currentData()

    def get_unpack_options(self) -> Dict[str, bool]:
        """返回一个包含所有解包选项的字典。"""
        return {
            "use_address_info": self._use_address_info_checkbox.isChecked(),
            "raw_dump": self._raw_dump_checkbox.isChecked()
        }

    def get_pack_options(self) -> Dict[str, bool]:
        """返回一个包含所有打包选项的字典。"""
        return {
            "simple_mode": self._simple_mode_checkbox.isChecked()
        }
    def update_outline(self, symbols: list[Dict]):
        """用解析器提供的新数据更新大纲视图。
        规则：
        - 函数作为顶级节点。
        - 标签归属到其最近的函数之下作为子节点；若无函数，则作为顶级节点。
        """
        # 先快照当前展开/选择/滚动状态
        self._snapshot_outline_state()

        # 批量更新，避免闪烁
        self._outline_tree.setUpdatesEnabled(False)
        self._outline_tree.clear()

        function_icon = QIcon(self.style().standardPixmap(QStyle.StandardPixmap.SP_ArrowRight))
        label_icon = QIcon(self.style().standardPixmap(QStyle.StandardPixmap.SP_DialogYesButton))  # 用一个不同的图标

        current_function_item: QTreeWidgetItem | None = None
        current_function_key: Optional[str] = None

        for symbol in symbols:
            s_type = symbol.get("type")
            s_name = symbol.get("name", "?")
            s_line = int(symbol.get("line", 1))

            # 决定父节点：函数为顶级；标签优先挂到最近函数下
            if s_type == "function":
                parent = self._outline_tree
            elif s_type == "label" and current_function_item is not None:
                parent = current_function_item
            else:
                parent = self._outline_tree

            item = QTreeWidgetItem(parent)
            item.setText(0, s_name)
            item.setData(0, Qt.ItemDataRole.UserRole, s_line)
            # 生成并存储稳定key
            if s_type == "function":
                item_key = f"F:{s_name}@{s_line}"
                current_function_key = item_key
            elif s_type == "label" and current_function_key:
                item_key = f"{current_function_key}/L:{s_name}@{s_line}"
            else:
                item_key = f"L:{s_name}@{s_line}"
            item.setData(0, self.KEY_ROLE, item_key)

            if s_type == "function":
                item.setIcon(0, function_icon)
                item.setToolTip(0, f"函数定义 (第 {s_line} 行)")
                current_function_item = item
            elif s_type == "label":
                item.setIcon(0, label_icon)
                item.setToolTip(0, f"标签 (第 {s_line} 行)")

        # 更新完毕，恢复先前状态；如果是首次构建，则默认仅展开到顶层
        if self._outline_initialized:
            self._restore_outline_state()
        else:
            self._outline_tree.expandToDepth(0)
            self._outline_initialized = True

        # 保持当前过滤条件
        if self._outline_filter.text():
            self._filter_outline(self._outline_filter.text())

        self._outline_tree.setUpdatesEnabled(True)
    # --- UI 构建辅助方法 ---
    def _create_outline_group(self) -> QGroupBox:
        """创建一个包含大纲树的 GroupBox。"""
        outline_group = QGroupBox("结构大纲")
        outline_group.setToolTip("显示脚本中的函数与标签；可双击跳转、输入关键字过滤，并使用按钮展开/折叠。")
        layout = QVBoxLayout()

        # 顶部工具条：过滤 + 展开/折叠
        tools = QHBoxLayout()
        # 过滤框提示
        self._outline_filter.setToolTip("输入关键字以过滤函数/标签（大小写不敏感）。")
        tools.addWidget(self._outline_filter)
        expand_btn = QPushButton("展开")
        expand_btn.setFixedHeight(26)
        expand_btn.setToolTip("展开所有函数节点")
        expand_btn.clicked.connect(self._outline_tree.expandAll)
        collapse_btn = QPushButton("折叠")
        collapse_btn.setFixedHeight(26)
        collapse_btn.setToolTip("折叠所有函数节点")
        collapse_btn.clicked.connect(self._outline_tree.collapseAll)
        tools.addWidget(expand_btn)
        tools.addWidget(collapse_btn)
        layout.addLayout(tools)

        # 树控件提示
        self._outline_tree.setToolTip("脚本结构树：函数为父节点，标签为子节点。双击跳转到对应行。")
        layout.addWidget(self._outline_tree)
        outline_group.setLayout(layout)
        return outline_group

    # --- 公开：创建独立的大纲 Dock（放在窗口右侧） ---
    def create_outline_dock(self, parent=None) -> QDockWidget:
        dock = QDockWidget("ECL 结构大纲", parent)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)
        dock.setToolTip("结构大纲：可过滤/展开/折叠并双击跳转到源码位置。")

        container = QWidget(dock)
        layout = QVBoxLayout(container)

        # 顶部工具条：过滤 + 展开/折叠
        tools = QHBoxLayout()
        self._outline_filter.setToolTip("输入关键字以过滤函数/标签（大小写不敏感）。")
        tools.addWidget(self._outline_filter)
        expand_btn = QPushButton("展开")
        expand_btn.setFixedHeight(26)
        expand_btn.setToolTip("展开所有函数节点")
        expand_btn.clicked.connect(self._outline_tree.expandAll)
        collapse_btn = QPushButton("折叠")
        collapse_btn.setFixedHeight(26)
        collapse_btn.setToolTip("折叠所有函数节点")
        collapse_btn.clicked.connect(self._outline_tree.collapseAll)
        tools.addWidget(expand_btn)
        tools.addWidget(collapse_btn)
        layout.addLayout(tools)
        self._outline_tree.setToolTip("脚本结构树：函数为父节点，标签为子节点。双击跳转到对应行。")
        layout.addWidget(self._outline_tree)
        container.setLayout(layout)
        dock.setWidget(container)
        dock.setMinimumWidth(280)
        return dock
    def _on_outline_item_jump(self, item: QTreeWidgetItem, column: int):
        """当用户双击大纲中的一项时触发。"""
        line_number = item.data(0, Qt.ItemDataRole.UserRole)
        if line_number:
            self.outline_jump_requested.emit(line_number)

    # ---- 大纲状态：快照/恢复 ----
    def _snapshot_outline_state(self):
        """保存当前展开项、选择项和滚动位置。"""
        self._outline_expanded_keys.clear()
        # 记录展开状态
        def walk(item: QTreeWidgetItem):
            key = item.data(0, self.KEY_ROLE)
            if key and item.isExpanded():
                self._outline_expanded_keys.add(key)
            for i in range(item.childCount()):
                walk(item.child(i))

        for i in range(self._outline_tree.topLevelItemCount()):
            walk(self._outline_tree.topLevelItem(i))

        # 记录选择项
        current = self._outline_tree.currentItem()
        self._outline_selected_key = current.data(0, self.KEY_ROLE) if current else None

        # 记录滚动位置
        self._outline_scroll_value = self._outline_tree.verticalScrollBar().value()

    def _restore_outline_state(self):
        """根据快照恢复展开项、选择项和滚动位置。"""
        def walk(item: QTreeWidgetItem):
            key = item.data(0, self.KEY_ROLE)
            if key in self._outline_expanded_keys:
                item.setExpanded(True)
            for i in range(item.childCount()):
                walk(item.child(i))

        # 恢复展开
        for i in range(self._outline_tree.topLevelItemCount()):
            walk(self._outline_tree.topLevelItem(i))

        # 恢复选择
        if self._outline_selected_key:
            def find(item: QTreeWidgetItem):
                if item.data(0, self.KEY_ROLE) == self._outline_selected_key:
                    return item
                for j in range(item.childCount()):
                    res = find(item.child(j))
                    if res:
                        return res
                return None

            target = None
            for i in range(self._outline_tree.topLevelItemCount()):
                target = find(self._outline_tree.topLevelItem(i))
                if target:
                    break
            if target:
                self._outline_tree.setCurrentItem(target)

        # 恢复滚动
        self._outline_tree.verticalScrollBar().setValue(self._outline_scroll_value)
    def _create_settings_group(self) -> QGroupBox:
        settings_group = QGroupBox("路径设置")
        settings_group.setToolTip("配置 ECL 工具与文档：\n- Thecl: thecl.exe 可执行文件\n- Eclmap: 指令/类型映射，影响反编译/打包\n- 指令文档(json): 悬停说明/补全用的帮助文档")
        layout = QVBoxLayout()
        thecl_row = self._create_path_row("Thecl:", self._thecl_path_input, self._browse_for_thecl)
        eclmap_row = self._create_path_row("Eclmap:", self._eclmap_path_input, self._browse_for_eclmap)
        ref_row = self._create_path_row("指令文档(json):", self._thecl_ref_path_input, self._browse_for_ref)
        layout.addLayout(thecl_row)
        layout.addLayout(eclmap_row)
        layout.addLayout(ref_row)
        settings_group.setLayout(layout)
        return settings_group

    def _create_actions_group(self) -> QGroupBox:
        actions_group = QGroupBox("核心操作")
        actions_group.setToolTip("选择版本后，可解包 .ecl 为文本或将当前文本打包为 .ecl；下方选项影响输出细节。")
        layout = QVBoxLayout()
        
        version_layout = QHBoxLayout()
        version_label = QLabel("游戏版本:")
        version_label.setToolTip("目标游戏版本（影响 thecl 的编解包参数与语法差异）")
        self._version_combo = QComboBox()
        self._version_combo.setToolTip("请选择与目标脚本对应的版本，否则可能出现解析/打包不兼容。")
        for display_name, version_code in ECL_GAME_VERSIONS.items():
            self._version_combo.addItem(display_name, userData=version_code)
        
        version_layout.addWidget(version_label)
        version_layout.addWidget(self._version_combo)

        # 创建一个新的 GroupBox 用于存放选项
        options_group = QGroupBox("选项")
        options_group.setToolTip("解包/打包的附加选项：可控制是否保留地址信息、是否进行转换、以及简化打包模式。")
        options_layout = QVBoxLayout()
        self._use_address_info_checkbox.setToolTip("解包：在每条指令旁展示文件偏移与子程序内偏移（-x）")
        self._raw_dump_checkbox.setToolTip("解包：不做表达式反编译与参数检测，输出原始指令（-r）")
        self._simple_mode_checkbox.setToolTip("打包：采用简化模式，不自动插入任何额外指令（-s）")
        options_layout.addWidget(self._use_address_info_checkbox)
        options_layout.addWidget(self._raw_dump_checkbox)
        options_layout.addWidget(self._simple_mode_checkbox)
        options_group.setLayout(options_layout)

        unpack_btn = QPushButton("解包 ECL 并编辑...")
        unpack_btn.setToolTip("选择 .ecl 文件并解包为可编辑文本；会使用所选版本与选项。")
        unpack_btn.clicked.connect(self.unpack_requested)

        pack_btn = QPushButton("打包当前脚本...")
        pack_btn.setToolTip("将当前编辑的文本按所选版本打包为 .ecl 文件；建议与来源版本一致。")
        pack_btn.clicked.connect(self.pack_requested)

        layout.addLayout(version_layout)
        layout.addWidget(options_group) # 添加选项组
        layout.addWidget(unpack_btn)
        layout.addWidget(pack_btn)
        actions_group.setLayout(layout)
        return actions_group

    def _create_path_row(self, label_text: str, line_edit: QLineEdit, browse_func) -> QHBoxLayout:
        row_layout = QHBoxLayout()
        line_edit.setPlaceholderText("自动检测或手动指定...")
        # 输入框提示
        if label_text.startswith("Thecl"):
            line_edit.setToolTip("thecl.exe 路径：THTK 的 ECL 工具，用于解包/打包。")
        elif label_text.startswith("Eclmap"):
            line_edit.setToolTip("eclmap 路径：指令/类型映射表，影响反编译显示与打包参数解析。")
        else:
            line_edit.setToolTip("thecl_ref.json 帮助文档路径：用于悬停说明与补全提示。")
        style = self.style()
        browse_icon = QIcon(style.standardPixmap(QStyle.StandardPixmap.SP_DirOpenIcon))
        browse_btn = QPushButton(browse_icon, "")
        browse_btn.setFixedSize(30, 30)
        browse_btn.clicked.connect(browse_func)
        # 浏览按钮提示
        if label_text.startswith("Thecl"):
            browse_btn.setToolTip("选择 thecl.exe 可执行文件")
        elif label_text.startswith("Eclmap"):
            browse_btn.setToolTip("选择 eclmap 映射文件")
        else:
            browse_btn.setToolTip("选择 thecl_ref.json 帮助文档")
        label = QLabel(label_text)
        # 标签提示
        if label_text.startswith("Thecl"):
            label.setToolTip("THTK 的 thecl 工具路径")
        elif label_text.startswith("Eclmap"):
            label.setToolTip("ECL 指令/类型映射文件路径")
        else:
            label.setToolTip("thecl 帮助文档（JSON）路径")
        label.setFixedWidth(100)
        row_layout.addWidget(label)
        row_layout.addWidget(line_edit)
        row_layout.addWidget(browse_btn)
        return row_layout

    # --- 槽函数 ---
    def _browse_for_thecl(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 thecl.exe", "", "Executable Files (*.exe);;All Files (*)")
        if path:
            self._thecl_path_input.setText(path)

    def _browse_for_eclmap(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 eclmap 文件", "", "All Files (*)")
        if path:
            self._eclmap_path_input.setText(path)

    def _browse_for_ref(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 thecl_ref.json", "", "JSON Files (*.json);;All Files (*)")
        if path:
            self._thecl_ref_path_input.setText(path)

    # --- 私有：大纲过滤逻辑 ---
    def _filter_outline(self, text: str):
        pattern = text.strip().lower()
        def filter_item(item: QTreeWidgetItem) -> bool:
            # 如果自身或后代命中，则显示；否则隐藏
            hits_self = pattern in item.text(0).lower()
            any_child_visible = False
            for i in range(item.childCount()):
                if filter_item(item.child(i)):
                    any_child_visible = True
            visible = hits_self or any_child_visible or not pattern
            item.setHidden(not visible)
            return visible

        for i in range(self._outline_tree.topLevelItemCount()):
            filter_item(self._outline_tree.topLevelItem(i))