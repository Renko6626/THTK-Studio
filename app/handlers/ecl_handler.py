# app/handlers/ecl_handler.py

from pathlib import Path
import hashlib
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QMessageBox
import json
import re
from ..core.script_handler import ScriptHandler
from ..core.thecl_wrapper import TheclWrapper, TheclError
# 我们需要为ECL创建一个新的高亮器，现在先用一个占位符
from ..widgets.ecl_syntax_highlighter import EclSyntaxHighlighter 
from PyQt6.QtGui import QSyntaxHighlighter # 临时使用基础高亮器
from ..widgets.thecl_panel import TheclPanel
class EclParser:
    """
    一个用于解析ECL脚本，提取函数和标签定义的解析器。
    """
    # 匹配 void FunctionName(...)
    FUNCTION_RE = re.compile(r'^\s*void\s+([a-zA-Z_]\w+)\s*\(')
    # 匹配 LabelName:
    LABEL_RE = re.compile(r'^\s*([a-zA-Z_]\w+):')

    def parse(self, text: str) -> dict:
        """
        解析文本，返回一个包含所有符号（函数和标签）的列表。
        """
        symbols = []
        for line_num, line in enumerate(text.splitlines(), 1): # 行号从1开始
            func_match = self.FUNCTION_RE.match(line)
            if func_match:
                symbols.append({
                    "name": func_match.group(1),
                    "type": "function",
                    "line": line_num
                })
                continue # 函数定义优先

            label_match = self.LABEL_RE.match(line)
            if label_match:
                symbols.append({
                    "name": label_match.group(1),
                    "type": "label",
                    "line": line_num
                })
        
        return {"symbols": symbols}
class EclScriptHandler(ScriptHandler):
    """
    ECL 脚本的具体处理器。
    负责创建和管理所有 ECL 专用的UI组件、解析逻辑和工具交互。
    """

    def __init__(self):
        self.tool_panel: TheclPanel | None = None
        # ECL脚本的指令集通常在eclmap文件中，暂时不需要像MSG那样加载
        self.instruction_docs = {}
        self.builtin_variables = []
        try:
            # 假设文件在 resources 目录下
            with open('./resources/ecl_variables.json', 'r', encoding='utf-8') as f:
                self.builtin_variables = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"警告：无法加载内置变量文件: {e}")

        self.parser = EclParser()
        # 记录上一次用于大纲的文本指纹，避免重复刷新导致折叠状态被重置
        self._last_outline_fingerprint = None

    # ==================================================================
    # ScriptHandler 接口实现
    # ==================================================================

    def get_name(self) -> str:
        """返回处理器的名称。"""
        return "ECL"

    def get_file_filter(self) -> str:
        """返回用于文件对话框的过滤器字符串。"""
        return "ECL Scripts (*.ecl *.txt)"

    def create_highlighter(self, document):
        """创建并返回 ECL 语法高亮器实例。"""
        # TODO: 将来替换为 EclSyntaxHighlighter
        return EclSyntaxHighlighter(document, self.instruction_docs,builtin_variables=self.builtin_variables)
        # 暂时返回一个不执行任何操作的基础高亮器
        return QSyntaxHighlighter(document)

    def create_parser(self):
        """
        为 ECL 创建一个虚拟解析器。
        未来可以扩展它来支持子程序跳转、大纲视图等功能。
        """
        return self.parser

    def create_tool_wrapper(self, settings):
        """创建并返回 TheclWrapper 的实例。"""
        # 假设 settings 中有 get_thecl_path 和 get_eclmap_path 方法
        thecl_path = settings.get_thecl_path()
        eclmap_path = settings.get_eclmap_path()
        if not thecl_path:
            # 不弹出消息框，因为这在切换处理器时可能会很烦人。
            return None
        try:
            # Eclmap路径是可选的，所以可以为None
            return TheclWrapper(thecl_path, eclmap_path)
        except FileNotFoundError as e:
            print(f"ECL Wrapper Error: {e}")
            return None

    def setup_ui(self, main_window):
        """
        为 ECL 处理器设置UI。
        创建并添加 ECL 工具面板。
        """
        main_window.setCentralWidget(main_window.text_editor)
        self.tool_panel = TheclPanel(main_window)
        # 左侧：工具面板（路径、选项、打包解包）
        main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.tool_panel)
        main_window.view_menu.addAction(self.tool_panel.toggleViewAction())

        # 右侧：结构大纲（独立 Dock）
        try:
            outline_dock = self.tool_panel.create_outline_dock(main_window)
            main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, outline_dock)
            main_window.view_menu.addAction(outline_dock.toggleViewAction())
            # 保存引用，避免被垃圾回收
            self._outline_dock = outline_dock
        except Exception as e:
            print(f"Failed to create outline dock: {e}")

    def clear_ui(self, main_window):
        """
        清理 ECL 处理器的UI。
        """
        # 优先移除右侧创建的结构大纲 Dock，避免切换处理器后残留堆积
        if hasattr(self, "_outline_dock") and getattr(self, "_outline_dock") is not None:
            try:
                main_window.removeDockWidget(self._outline_dock)
            except Exception:
                pass
            try:
                self._outline_dock.deleteLater()
            except Exception:
                pass
            self._outline_dock = None

        if self.tool_panel:
            main_window.removeDockWidget(self.tool_panel)
            self.tool_panel.deleteLater()
            self.tool_panel = None

    def connect_signals(self, main_window):
        """
        [REVISED] 连接信号，包括大纲视图的跳转请求。
        """
        if self.tool_panel:
            # ... (路径设置和打包/解包信号连接保持不变) ...
            self.tool_panel.set_thecl_path(main_window.settings.get_thecl_path())
            self.tool_panel.set_eclmap_path(main_window.settings.get_eclmap_path())
            # 统一初始化 thecl_ref.json 路径：优先用户/内置的 get_ecl_ref_path；
            # 若未来存在别名 get_thecl_ref_path 也一并兼容。
            ref_path = ""
            try:
                ref_path = main_window.settings.get_ecl_ref_path()
            except Exception:
                ref_path = ""
            if not ref_path:
                get_ref_compat = getattr(main_window.settings, 'get_thecl_ref_path', None)
                if callable(get_ref_compat):
                    try:
                        ref_path = get_ref_compat() or ""
                    except Exception:
                        ref_path = ""

            # 将路径填入面板输入框
            if ref_path:
                self.tool_panel.set_ref_path(ref_path)
                # 首次加载/应用指令文档（用于悬浮与侧栏）
                self._load_instruction_docs(ref_path)
                self._apply_docs_to_highlighter(main_window)
            else:
                # 即使没有路径，也保持输入框占位符，后续由用户选择时触发加载
                self.tool_panel.set_ref_path("")

            self.tool_panel.thecl_path_changed.connect(lambda path: main_window.settings.set_user_path("user_thecl_path", path))
            self.tool_panel.eclmap_path_changed.connect(lambda path: main_window.settings.set_user_path("user_eclmap_path", path))
            # 监听 ref 路径变化：保存设置并加载文档更新高亮器
            self.tool_panel.thecl_ref_path_changed.connect(lambda path: self._on_ref_path_changed(main_window, path))
            self.tool_panel.unpack_requested.connect(lambda: self.on_unpack_request(main_window))
            self.tool_panel.pack_requested.connect(lambda: self.on_pack_request(main_window))
            
            # vvvvvvvvvvvvvv 新增：连接大纲跳转信号 vvvvvvvvvvvvvv
            self.tool_panel.outline_jump_requested.connect(
                lambda line: self.on_jump_to_line(main_window, line)
            )

    def update_views(self, main_window):
        """
        [REVISED] 当文本更改时，使用自己持有的解析器来更新大纲视图。
        """
        # vvvvvvvvvvvvvv 核心修复 vvvvvvvvvvvvvv
        # 不再访问 main_window.parser，而是使用 self.parser
        if self.parser and self.tool_panel:
            text = main_window.text_editor.toPlainText()
            # 计算稳定指纹（文本变更才更新大纲）
            fingerprint = hashlib.blake2b(text.encode('utf-8'), digest_size=16).hexdigest()
            if fingerprint == self._last_outline_fingerprint:
                return
            self._last_outline_fingerprint = fingerprint

            parsed_data = self.parser.parse(text)
            symbols = parsed_data.get("symbols", [])
            self.tool_panel.update_outline(symbols)

            # 确保当前高亮器持有最新的文档（例如首次载入时）
            self._apply_docs_to_highlighter(main_window)

    # ==================================================================
    # 新增槽函数
    # ==================================================================
    def on_jump_to_line(self, main_window, line_number: int):
        """响应大纲视图的跳转请求。"""
        main_window.text_editor.jump_to_line(line_number)

    # ==================================================================
    # 帮助文档加载与应用
    # ==================================================================
    def _on_ref_path_changed(self, main_window, path: str):
        # 持久化
        try:
            # ECL 使用的设置键是 user_ecl_ref_path（与 Settings 保持一致）
            main_window.settings.set_user_path("user_ecl_ref_path", path)
        except Exception:
            pass
        # 加载与应用
        self._load_instruction_docs(path)
        self._apply_docs_to_highlighter(main_window)

    def _load_instruction_docs(self, file_path: str):
        """从 thecl_ref.json 加载指令文档，并将键标准化为指令名（非数字ID）。"""
        self.instruction_docs.clear()
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"错误: 无法加载或解析 ECL 帮助文档 '{file_path}': {e}")
            return

        # 兼容多种数据结构：
        # thecl_ref.json 通常是 { "id": ["name(args)", "desc"] }
        # 也容许 { key: {signature, description} } 或 { key: "desc" }
        for key, value in data.items():
            sig = None
            desc = None
            if isinstance(value, list):
                if len(value) >= 1:
                    sig = value[0]
                if len(value) >= 2:
                    desc = value[1]
            elif isinstance(value, dict):
                sig = value.get('signature') or value.get('name')
                desc = value.get('description') or value.get('doc')
            elif isinstance(value, str):
                # 只有描述，没有签名时，用 key 作为签名回退
                desc = value
                sig = str(key)

            if not sig and not desc:
                continue

            # 构造 HTML
            sig_text = str(sig) if sig else ""
            desc_text = str(desc) if desc else ""
            doc_html = f"<b>{sig_text}</b><br>{desc_text}" if sig_text else desc_text

            # 从签名中提取指令名（去掉类型/参数），例如 "callAsyncId(string sub, int id)" -> "callAsyncId"
            # 若签名是形如 "ins_18(int id)"，则得到 "ins_18"
            m = re.match(r'@?([A-Za-z_]\w*)', sig_text)
            if m:
                name = m.group(1)
                # 注册多种大小写形态，便于匹配
                for k in {name, name.lower(), name.upper()}:
                    self.instruction_docs[k] = doc_html

            # 额外：如果原始 key 是数字 ID，也登记一个 "ins_<id>" 的别名，以便未映射时也能匹配
            if str(key).isdigit():
                ins_alias = f"ins_{key}"
                self.instruction_docs[ins_alias] = doc_html
                self.instruction_docs[ins_alias.lower()] = doc_html
                self.instruction_docs[ins_alias.upper()] = doc_html

        print(f"ECL 指令文档已加载，共 {len(self.instruction_docs)} 条（含别名）。")

    def _apply_docs_to_highlighter(self, main_window):
        #print("[DEBUG] 应用 ECL 指令文档到高亮器...")
        hl = getattr(main_window.text_editor, 'highlighter', None)
        if hl:
            # 首选：调用高亮器提供的动态更新接口，触发规则重建
            set_docs = getattr(hl, 'set_instruction_docs', None)
            if callable(set_docs):
                try:
                    set_docs(self.instruction_docs)
                except Exception:
                    pass
            else:
                # 兼容旧版本：直接赋值并重绘（但不会重建规则，效果可能不完全）
                if hasattr(hl, 'instruction_docs'):
                    hl.instruction_docs = self.instruction_docs
                try:
                    hl.rehighlight()
                except Exception:
                    pass
        # 刷新侧边栏（用当前光标下的词尝试拉取帮助）
        try:
            if hasattr(main_window.text_editor, '_text_under_cursor'):
                word = main_window.text_editor._text_under_cursor()
                main_window._on_word_under_cursor(word)
        except Exception:
            pass
    # ==================================================================
    # ECL 工具流槽函数
    # ==================================================================

    def on_unpack_request(self, main_window):
        """响应“解包 ECL”按钮。"""
        tool = self.create_tool_wrapper(main_window.settings)
        if not tool:
            QMessageBox.warning(main_window, "工具缺失", "请在 ECL 面板中指定 thecl.exe 的路径。")
            return
       
        ecl_file, _ = QFileDialog.getOpenFileName(main_window, "选择要解包的 ECL 文件", "", "ECL Files (*.ecl)")
        if not ecl_file: return
        
        output_txt = Path(ecl_file).with_suffix('.txt')
        version = self.tool_panel.get_selected_version()
        if not version:
            QMessageBox.warning(main_window, "版本未选择", "请在 ECL 面板中选择一个游戏版本。")
            return
        
        # 从面板获取解包的额外选项
        unpack_options = self.tool_panel.get_unpack_options()
        
        try:
            main_window.statusBar.showMessage(f"正在解包 {Path(ecl_file).name}...", 5000)
            # 将选项作为关键字参数传递给 wrapper 的 unpack 方法
            tool.unpack(
                version, 
                ecl_file, 
                str(output_txt), 
                use_address_info=unpack_options.get("use_address_info", False),
                raw_dump=unpack_options.get("raw_dump", False)
            )
            QMessageBox.information(main_window, "成功", f"文件已成功解包到:\n{output_txt}")
            main_window._load_file_content(output_txt)
        except TheclError as e:
            QMessageBox.critical(main_window, "Thecl 错误", f"解包失败: {e}\n\n详细信息:\n{e.stderr}")

    def on_pack_request(self, main_window):
        """响应“打包当前脚本”按钮。"""
        if not main_window.current_file_path or main_window.current_file_path.suffix != '.txt':
            QMessageBox.warning(main_window, "操作无效", "请先打开一个要打包的 .txt 脚本文件。")
            return
            
        tool = self.create_tool_wrapper(main_window.settings)
        if not tool:
            QMessageBox.warning(main_window, "工具缺失", "请在 ECL 面板中指定 thecl.exe 的路径。")
            return

        default_name = main_window.current_file_path.with_suffix('.ecl').name
        output_ecl, _ = QFileDialog.getSaveFileName(main_window, "选择新 ECL 文件的保存位置", default_name, "ECL Files (*.ecl)")
        if not output_ecl: return
            
        version = self.tool_panel.get_selected_version()
        if not version:
            QMessageBox.warning(main_window, "版本未选择", "请在 ECL 面板中选择一个游戏版本。")
            return

        # 从面板获取打包的额外选项
        pack_options = self.tool_panel.get_pack_options()

        try:
            main_window.statusBar.showMessage(f"正在打包到 {Path(output_ecl).name}...", 5000)
            # 将选项作为关键字参数传递给 wrapper 的 pack 方法
            tool.pack(
                version, 
                str(main_window.current_file_path), 
                output_ecl,
                simple_mode=pack_options.get("simple_mode", False)
            )
            QMessageBox.information(main_window, "成功", f"文件已成功打包到:\n{output_ecl}")
        except TheclError as e:
            QMessageBox.critical(main_window, "Thecl 错误", f"打包失败: {e}\n\n详细信息:\n{e.stderr}")