# app/handlers/std_handler.py

import json
import re
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from ..core.script_handler import ScriptHandler
from ..core.thstd_wrapper import ThstdWrapper, ThstdError
from ..widgets.std_syntax_highlighter import StdSyntaxHighlighter
from ..widgets.thstd_panel import ThstdPanel

class StdScriptHandler(ScriptHandler):
    """
    STD 脚本的具体处理器。
    负责创建和管理所有 STD 专用的UI组件、解析逻辑和工具交互。
    """

    def __init__(self):
        self.instruction_docs = {}
        self.tool_panel: ThstdPanel | None = None

    # ==================================================================
    # ScriptHandler 接口实现
    # ==================================================================

    def get_name(self) -> str:
        """返回处理器的名称。"""
        return "STD"

    def get_file_filter(self) -> str:
        """返回用于文件对话框的过滤器字符串。"""
        return "STD Scripts (*.std *.txt)"

    def create_highlighter(self, document):
        """创建并返回 STD 语法高亮器实例。"""
        # 初始时传入空的指令字典，后续在 connect_signals 中填充
        return StdSyntaxHighlighter(document, self.instruction_docs)

    def create_parser(self):
        """
        为 STD 创建一个虚拟解析器。
        目前不需要复杂的解析来支持额外视图（如精灵预览或快速跳转）。
        """
        class DummyParser:
            def parse(self, text): return {}
        return DummyParser()

    def create_tool_wrapper(self, settings):
        """创建并返回 ThstdWrapper 的实例。"""
        thstd_path = settings.get_thstd_path()
        ref_path = settings.get_std_ref_path()
        if not thstd_path or not ref_path:
            # 不弹出消息框，因为这在切换处理器时可能会很烦人。
            # 可以在实际使用工具时再提示。
            return None
        try:
            return ThstdWrapper(thstd_path, ref_path)
        except FileNotFoundError as e:
            print(f"STD Wrapper Error: {e}")
            return None

    def setup_ui(self, main_window):
        """
        为 STD 处理器设置UI。
        创建并添加 STD 工具面板。
        """
        main_window.setCentralWidget(main_window.text_editor)
        self.tool_panel = ThstdPanel(main_window)
        main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.tool_panel)
        main_window.view_menu.addAction(self.tool_panel.toggleViewAction())

    def clear_ui(self, main_window):
        """
        清理 STD 处理器的UI。
        """
        if self.tool_panel:
            main_window.removeDockWidget(self.tool_panel)
            self.tool_panel.deleteLater()
            self.tool_panel = None

    def connect_signals(self, main_window):
        """
        连接信号，并加载 STD 指令集以更新高亮器和帮助提示。
        """
        # 1. 连接工具面板信号
        if self.tool_panel:
            # 设置初始路径
            self.tool_panel.set_thstd_path(main_window.settings.get_thstd_path())
            self.tool_panel.set_ref_path(main_window.settings.get_std_ref_path())

            # 连接路径变化信号以保存设置
            self.tool_panel.thstd_path_changed.connect(
                lambda path: main_window.settings.set_user_path("user_thstd_path", path)
            )
            # 保存指令集 JSON 路径
            self.tool_panel.ref_path_changed.connect(
                lambda path: main_window.settings.set_user_path("user_std_ref_path", path)
            )

            # 连接功能信号
            self.tool_panel.unpack_requested.connect(lambda: self.on_unpack_request(main_window))
            self.tool_panel.pack_requested.connect(lambda: self.on_pack_request(main_window))

        # 2. 从 settings 获取指令集路径并加载
        ref_path_str = main_window.settings.get_std_ref_path()
        if ref_path_str:
            self._load_instruction_docs(ref_path_str)
        else:
            print("警告: STD 指令集路径 (thstd_ref.json) 未设置，悬停提示和补全将不可用。")
            self.instruction_docs.clear()

        # 3. 更新已存在的高亮器实例
        highlighter = main_window.text_editor.highlighter
        if isinstance(highlighter, StdSyntaxHighlighter):
            highlighter.instruction_docs = self.instruction_docs
            # 触发一次重新高亮以应用新加载的指令
            highlighter.rehighlight()

    def update_views(self, main_window):
        """
        当文本更改时更新视图。
        对于基础的 STD 处理器，此方法无需任何操作。
        """
        pass

    # ==================================================================
    # 辅助方法
    # ==================================================================

    def _load_instruction_docs(self, file_path: str):
        """
        从给定的 JSON 文件路径加载并解析 STD 指令文档。
        文件格式示例: {"ins_0": ["SetSpeed(speed, time)", "设置速度"], ...}
        """
        self.instruction_docs.clear()
        try:
            with open(file_path, "r", encoding='utf-8') as f:
                raw_data = json.load(f)

            # thstd_ref.json 的格式是 {"ins_id": ["name(args)", "desc"]}
            for key, value in raw_data.items():
                if not isinstance(value, list) or len(value) < 2:
                    continue
                
                full_name, description = value[0], value[1]
                
                # 提取指令名 (如 SetSpeed)
                name_match = re.match(r'([\w_]+)\(.*\)', full_name)
                if name_match:
                    instruction_name = name_match.group(1)
                    # 创建 HTML 格式的文档字符串
                    doc_html = f"<b>{full_name}</b><br>{description}"
                    self.instruction_docs[instruction_name] = doc_html
                    
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"错误: 无法加载或解析STD指令集 '{file_path}': {e}")

    # ==================================================================
    # 工具流槽函数 (未来可扩展)
    # ==================================================================
    # 以下是为未来实现打包/解包功能预留的框架，当前为空。

    def on_unpack_request(self, main_window):
        """响应“解包 STD”按钮。"""
        tool = self.create_tool_wrapper(main_window.settings)
        if not tool:
            QMessageBox.warning(main_window, "工具缺失", "请在 STD 面板中指定 thstd.exe 的路径。")
            return
       
        std_file, _ = QFileDialog.getOpenFileName(main_window, "选择要解包的 STD 文件", "", "STD Files (*.std)")
        if not std_file: return
        
        output_txt = Path(std_file).with_suffix('.txt')
        version = self.tool_panel.get_selected_version()
        if not version:
            QMessageBox.warning(main_window, "版本未选择", "请在 STD 面板中选择一个游戏版本。")
            return
        
        try:
            main_window.statusBar.showMessage(f"正在解包 {Path(std_file).name}...", 5000)
            # 从面板读取解包模式（default/clean），传递给包装器
            unpack_mode = self.tool_panel.get_unpack_mode() if hasattr(self.tool_panel, 'get_unpack_mode') else 'default'
            tool.unpack(version, std_file, str(output_txt), mode=unpack_mode)
            QMessageBox.information(main_window, "成功", f"文件已成功解包到:\n{output_txt}")
            main_window._load_file_content(output_txt)
        except ThstdError as e:
            QMessageBox.critical(main_window, "Thstd 错误", f"解包失败: {e}\n\n详细信息:\n{e.stderr}")

    def on_pack_request(self, main_window):
        """响应“打包当前脚本”按钮。"""
        if not main_window.current_file_path or main_window.current_file_path.suffix != '.txt':
            QMessageBox.warning(main_window, "操作无效", "请先打开一个要打包的 .txt 脚本文件。")
            return
            
        tool = self.create_tool_wrapper(main_window.settings)
        if not tool:
            QMessageBox.warning(main_window, "工具缺失", "请在 STD 面板中指定 thstd.exe 的路径。")
            return

        default_name = main_window.current_file_path.with_suffix('.std').name
        output_std, _ = QFileDialog.getSaveFileName(main_window, "选择新 STD 文件的保存位置", default_name, "STD Files (*.std)")
        if not output_std: return
            
        version = self.tool_panel.get_selected_version()
        if not version:
            QMessageBox.warning(main_window, "版本未选择", "请在 STD 面板中选择一个游戏版本。")
            return

        try:
            main_window.statusBar.showMessage(f"正在打包到 {Path(output_std).name}...", 5000)
            tool.pack(version, str(main_window.current_file_path), output_std)
            QMessageBox.information(main_window, "成功", f"文件已成功打包到:\n{output_std}")
        except ThstdError as e:
            QMessageBox.critical(main_window, "Thstd 错误", f"打包失败: {e}\n详细信息:\n{e.stderr}")
    