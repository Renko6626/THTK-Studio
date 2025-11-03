# app/handlers/msg_handler.py

from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QFileDialog, QMessageBox
import json
import re
from ..core.script_handler import ScriptHandler
from ..core.thmsg_wrapper import ThmsgWrapper, ThmsgError
from ..widgets.msg_syntax_highlighter import MsgSyntaxHighlighter
from ..widgets.thmsg_panel import MsgToolPanel

class MsgScriptHandler(ScriptHandler):
    """
    MSG 脚本的具体处理器。
    负责创建和管理所有 MSG 专用的UI组件、解析逻辑和工具交互。
    """



    def __init__(self):
        # 处理器自身维护其UI组件的引用
        self.tool_panel: MsgToolPanel | None = None
        self.instruction_docs = {}
    # ==================================================================
    # ScriptHandler 接口实现
    # ==================================================================
    def create_highlighter(self, document):
        """
        创建 MsgSyntaxHighlighter 实例，并注入指令文档。
        """
        # 注意：这里我们还没有加载数据，所以先传入一个空字典。
        # 真实的数据将在 connect_signals 中加载。
        return MsgSyntaxHighlighter(document, self.instruction_docs)
    def get_name(self) -> str:
        return "MSG"

    def get_file_filter(self) -> str:
        # MSG 脚本本身是 .msg 文件，但我们编辑的是解包后的 .txt
        # 为了清晰，我们让它能同时打开这两种
        return "MSG Related Files (*.msg *.txt)"

    def create_highlighter(self, document):
        # 注意：高亮器是为解包后的 .txt 文件设计的
        return MsgSyntaxHighlighter(document,self.instruction_docs)
    
    def create_parser(self):
        # MSG 脚本没有复杂的结构需要解析以支持额外功能（如快速跳转），
        # 所以我们返回一个虚拟的 "Dummy" 解析器来满足接口要求。
        class DummyParser:
            def parse(self, text): return {}
        return DummyParser()

    def create_tool_wrapper(self, settings):
        """创建并返回 ThmsgWrapper 的实例。"""
        # 假设你的 settings.py 中有 get_thmsg_path 和 get_msg_ref_path 方法
        thmsg_path = settings.get_thmsg_path() 
        ref_path = settings.get_msg_ref_path()
        if not thmsg_path or not ref_path:
            return None
        try:
            return ThmsgWrapper(thmsg_path, ref_path)
        except FileNotFoundError as e:
            QMessageBox.critical(None, "路径错误", str(e))
            return None

    def setup_ui(self, main_window):
        """创建 MSG 专用的UI面板。"""
        # 1. 确保中央控件是纯文本编辑器（MSG不需要预览区）
        main_window.setCentralWidget(main_window.text_editor)
        
        # 2. 创建并添加 MSG 工具面板
        self.tool_panel = MsgToolPanel(main_window)
        main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.tool_panel)
        main_window.view_menu.addAction(self.tool_panel.toggleViewAction())

    def clear_ui(self, main_window):
        """清理所有 MSG 专用的UI。"""
        if self.tool_panel:
            main_window.removeDockWidget(self.tool_panel)
            self.tool_panel.deleteLater()
            self.tool_panel = None
            
    def connect_signals(self, main_window):
        """
        [MODIFIED] 连接信号，并在此处加载指令集。
        """
        # 1. 加载指令集数据
        ref_path_str = main_window.settings.get_msg_ref_path()
        if ref_path_str:
            self._load_instruction_docs(ref_path_str)
        else:
            print("警告: MSG 指令集路径未设置，悬停提示将不可用。")
            self.instruction_docs.clear()
        
        # 2. 如果高亮器已经创建，则更新它的字典
        if main_window.text_editor.highlighter:
            main_window.text_editor.highlighter.instruction_docs = self.instruction_docs
            main_window.text_editor.highlighter.rehighlight()

        # 3. 连接工具面板的信号
        if self.tool_panel:
            # 设置初始路径
            self.tool_panel.set_thmsg_path(main_window.settings.get_thmsg_path())
            self.tool_panel.set_ref_path(main_window.settings.get_msg_ref_path())

            # 连接路径变化信号以保存设置
            self.tool_panel.thmsg_path_changed.connect(
                lambda path: main_window.settings.set_user_path("user_thmsg_path", path)
            )
            self.tool_panel.ref_path_changed.connect(
                lambda path: main_window.settings.set_user_path("user_ref_path", path)
            )
            
            # 连接功能信号
            self.tool_panel.unpack_requested.connect(lambda: self.on_unpack_request(main_window))
            self.tool_panel.pack_requested.connect(lambda: self.on_pack_request(main_window))
            self.tool_panel.insert_snippet_requested.connect(
                lambda text: self.on_insert_snippet(main_window, text)
            )
    def on_insert_snippet(self, main_window, text: str):
        """
        在文本编辑器中插入代码片段，并智能地移动光标。
        """
        editor = main_window.text_editor
        cursor = editor.textCursor()

        # 检查是否有 {cursor} 占位符
        if "{cursor}" in text:
            # 将文本分割成两部分
            before_cursor, after_cursor = text.split("{cursor}", 1)
            
            # 插入第一部分
            cursor.insertText(before_cursor)
            
            # 记录下光标应该在的位置
            cursor_final_pos = cursor.position()
            
            # 插入第二部分
            cursor.insertText(after_cursor)
            
            # 将光标移回到我们记录的位置
            cursor.setPosition(cursor_final_pos)
            
        else:
            # 如果没有占位符，就直接插入全部文本
            cursor.insertText(text)
        
        # 将修改后的光标应用回编辑器
        editor.setTextCursor(cursor)
        editor.setFocus() # 确保编辑器获得焦点
    def _load_instruction_docs(self, file_path: str):
        """从给定的JSON文件路径加载并解析指令文档。"""
        self.instruction_docs.clear()
        try:
            with open(file_path, "r", encoding='utf-8') as f:
                raw_data = json.load(f)
            for key, value in raw_data.items():
                full_name, description = value[0], value[1]
                name_match = re.match(r'(\w+)\(.*\)', full_name)
                if name_match:
                    instruction_name = name_match.group(1)
                    self.instruction_docs[instruction_name] = f"<b>{full_name}</b><br>{description}"
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"错误: 无法加载或解析MSG指令集 '{file_path}': {e}")
    def update_views(self, main_window):
        """MSG 脚本没有复杂的视图需要更新，所以这个方法什么都不做。"""
        # No operation needed for MSG script type when text changes.
        pass

    # ==================================================================
    # MSG 工具流槽函数
    # ==================================================================

    def on_unpack_request(self, main_window):
        """响应“解包 MSG”按钮。"""
        tool = self.create_tool_wrapper(main_window.settings)
        if not tool:
            QMessageBox.warning(main_window, "工具缺失", "请在设置中指定 thmsg.exe 和指令映射文件的路径。")
            return
       
        msg_file, _ = QFileDialog.getOpenFileName(main_window, "选择要解包的 MSG 文件", "", "MSG Files (*.msg)")
        if not msg_file: return
        
        output_txt = Path(msg_file).with_suffix('.txt')
        version = self.tool_panel.get_selected_version()
        
        # --- [MODIFICATION] 从面板获取解包模式 ---
        unpack_mode = self.tool_panel.get_unpack_mode()
        unpack_encoding = self.tool_panel.get_unpack_encoding()
        # --- END MODIFICATION ---
        
        try:
            main_window.statusBar.showMessage(f"正在解包 {Path(msg_file).name}...", 5000)
            
            # --- [MODIFICATION] 将模式传递给 unpack 方法 ---
            # (你需要确保你的 ThmsgWrapper.unpack 方法也接受 mode 参数)
            tool.unpack(version, msg_file, str(output_txt), mode=unpack_mode, encoding=unpack_encoding)
            # --- END MODIFICATION ---
            
            QMessageBox.information(main_window, "成功", f"文件已成功解包到:\n{output_txt}")
            main_window._load_file_content(output_txt)
        except ThmsgError as e:
            QMessageBox.critical(main_window, "Thmsg 错误", f"解包失败: {e}\n\n详细信息:\n{e.stderr}")

    def on_pack_request(self, main_window):
        """响应“打包当前脚本”按钮。"""
        if not main_window.current_file_path or main_window.current_file_path.suffix not in ['.txt', '.ecl']: # 假设未来ecl也是txt格式
            QMessageBox.warning(main_window, "操作无效", "请先打开一个要打包的 .txt 脚本文件。")
            return
            
        tool = self.create_tool_wrapper(main_window.settings)
        if not tool:
            QMessageBox.warning(main_window, "工具缺失", "请在设置中指定 thmsg.exe 和指令映射文件的路径。")
            return

        # 默认输出的 .msg 文件名与当前 .txt 文件名相同
        default_name = main_window.current_file_path.with_suffix('.msg').name
        output_msg, _ = QFileDialog.getSaveFileName(main_window, "选择新 MSG 文件的保存位置", default_name, "MSG Files (*.msg)")
        if not output_msg: return
            
        version = self.tool_panel.get_selected_version()
        pack_encoding = self.tool_panel.get_pack_encoding()
        try:
            main_window.statusBar.showMessage(f"正在打包到 {Path(output_msg).name}...", 5000)
            tool.pack(version, str(main_window.current_file_path), output_msg, encoding=pack_encoding)
            QMessageBox.information(main_window, "成功", f"文件已成功打包到:\n{output_msg}")
        except ThmsgError as e:
            QMessageBox.critical(main_window, "Thmsg 错误", f"打包失败: {e}\n详细信息:\n{e.stderr}")
            print("stderr:",e.stderr)
            print("message:",str(e))