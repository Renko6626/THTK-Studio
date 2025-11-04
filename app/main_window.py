# app/main_window.py

from pathlib import Path
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QMenu, QWidget
from PyQt6.QtGui import QAction, QKeySequence, QIcon
from PyQt6.QtWidgets import QStyle
# --- 导入核心模块 ---
from .core.settings import Settings
from .core.script_handler import ScriptHandler

# --- 导入具体的处理器 ---
from .handlers.anm_handler import AnmScriptHandler
from .handlers.msg_handler import MsgScriptHandler
from .handlers.std_handler import StdScriptHandler
from .handlers.ecl_handler import EclScriptHandler

# --- 导入UI控件 ---
from .widgets.text_editor import TextEditor
from .widgets.help_panel import HelpPanel
from .widgets.about_dialog import AboutDialog


class MainWindow(QMainWindow):
    """
    一个通用的、由处理器驱动的多脚本编辑器主窗口。
    """
    def __init__(self):
        super().__init__()
        
        # --- 1. 通用状态变量 ---
        self.settings = Settings()
        self.current_file_path: Path | None = None
        
        # --- 2. 处理器管理 ---
        anm_handler_instance = AnmScriptHandler()
        msg_handler_instance = MsgScriptHandler()
        std_handler_instance = StdScriptHandler()
        ecl_handler_instance = EclScriptHandler()
        
        self.script_handlers = {
            "ANM": anm_handler_instance,
            "MSG": msg_handler_instance,
            "STD": std_handler_instance,
            "ECL": ecl_handler_instance,
        }
        self.handler_file_map = {
            ".anm.txt": anm_handler_instance, # 更精确的匹配
            ".ddes": anm_handler_instance,
            ".msg.txt": msg_handler_instance, # 更精确的匹配
            ".msg": msg_handler_instance, # 用于直接打开
            ".std.txt": std_handler_instance, # 更精确的匹配
            ".std": std_handler_instance, # 用于直接打开
            ".ecl.txt": ecl_handler_instance, # ECL 文本
            ".ecl": ecl_handler_instance,     # 直接打开 ECL
            ".txt": std_handler_instance, # 作为默认或通用txt处理器
        }
        self.current_handler: ScriptHandler | None = None

        # --- 3. UI 构建---
        self.setWindowTitle("东方Project脚本编辑器")
        self.setGeometry(100, 100, 1400, 800)
        
        self._setup_central_widget()
        self._create_actions()
        self._create_dock_widgets() 
        self._create_menu_bar()      

        self._create_tool_bar()
        self._create_status_bar()
        
        # --- 4. 信号连接 ---
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.setInterval(400) # 400毫秒延迟
        self.update_timer.timeout.connect(self.run_handler_update)

        # 2. 连接 textChanged 到轻量级槽函数
        self.text_editor.document().modificationChanged.connect(self._on_modification_changed)
        #print("[DEBUG] MainWindow: Connected modificationChanged signal.")
        self.text_editor.textChanged.connect(self.on_text_changed_lightweight)


        # --- 5. 初始状态 ---
        
        # 启动时默认激活 ANM 处理器
        self.switch_handler(self.script_handlers["ANM"])
    # ==================================================================
    # 通用 UI 创建方法
    # ==================================================================
    def on_text_changed_lightweight(self):
        """
        轻量级槽函数：每次文本改变时，只重置并启动计时器。
        这个操作非常快，不会导致UI卡顿。
        """
        #print("[DEBUG] MainWindow.on_text_changed_lightweight: Text changed, restarting timer.")
        self.update_timer.start()
    def run_handler_update(self):
        """
        重量级槽函数：由计时器超时或手动刷新调用。
        这是所有分析和UI更新的总指挥。
        """
        #print("[DEBUG | Main] run_handler_update CALLED. Beginning full update...")
        
        # 1. 如果没有处理器，就什么都不做
        if not self.current_handler:
            #print("[DEBUG | Main] No active handler. Aborting update.")
            return

        # 2. 命令当前处理器更新其内部数据和专用视图
        #    例如，AnmHandler 会在这里解析文本并更新精灵预览区
        self.current_handler.update_views(self)
        
        # 3. 处理通用的、依赖于高亮器的 TextEditor 功能
        highlighter = self.text_editor.highlighter
        if not highlighter:
            print("[DEBUG | Main] No active highlighter. Aborting further updates.")
            return
            
        # 3a. 更新代码补全模型
        #print("[DEBUG | Main] Updating completion model...")
        self.text_editor.update_completion_model()
        # 同步帮助面板下拉候选
        try:
            if hasattr(highlighter, 'get_completion_words'):
                words = highlighter.get_completion_words() or []
                self.help_panel.set_completion_words(words)
        except Exception:
            pass
        
        # 3b. 执行语法检查并更新错误高亮
        all_errors = []
        if hasattr(highlighter, 'check_syntax'):
            #print("[DEBUG | Main] Checking syntax...")
            all_errors = highlighter.check_syntax(self.text_editor.toPlainText())
        
        #print(f"[DEBUG | Main] Found {len(all_errors)} syntax errors. Highlighting them...")
        self.text_editor.highlight_errors(all_errors)
        
        # 3c. 触发代码补全的弹出窗口
        #print("[DEBUG | Main] Triggering completion popup...")
        self.text_editor.trigger_completion()

        # 4. 最后，强制高亮器重绘整个文档
        #    这必须在所有数据处理（如动态规则更新）之后进行
        #print("[DEBUG | Main] Rehighlighting document...")
        highlighter.rehighlight()
        
        #print("[DEBUG | Main] Full update finished.")
    def _create_dock_widgets(self):
        """创建所有通用的可停靠面板。"""
        self.help_panel = HelpPanel(parent=self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.help_panel)
        # 关于弹窗（懒加载）：不嵌入 Dock，仅在菜单触发时显示
        self._about_dialog: AboutDialog | None = None
        # 注入文档获取回调：统一通过当前高亮器的规范化逻辑解析文档
        def _get_doc(word: str) -> str:
            hl = getattr(self.text_editor, 'highlighter', None)
            if not hl:
                return ""
            if hasattr(hl, 'get_documentation'):
                try:
                    html = hl.get_documentation(word) or ""
                except Exception:
                    html = ""
                if html:
                    return html
            docs = getattr(hl, 'instruction_docs', {}) or {}
            return docs.get(word, "")
        try:
            self.help_panel.set_get_doc_callback(_get_doc)
        except Exception:
            pass
    def _setup_central_widget(self):
        """设置中央的文本编辑器。"""
        self.text_editor = TextEditor()
        self.setCentralWidget(self.text_editor)
        self.text_editor.syntax_status_changed.connect(self._update_syntax_status)
        self.text_editor.word_under_cursor_changed.connect(self._on_word_under_cursor)

    def _create_actions(self):
        """创建通用的 QAction 对象。"""
        style = self.style()
        self.new_action = QAction(QIcon(style.standardPixmap(QStyle.StandardPixmap.SP_FileIcon)), "&新建", self)
        self.open_action = QAction(QIcon(style.standardPixmap(QStyle.StandardPixmap.SP_DirOpenIcon)), "&打开...", self)
        self.open_action.triggered.connect(self.open_file)
        
        self.save_action = QAction(QIcon(style.standardPixmap(QStyle.StandardPixmap.SP_DialogSaveButton)), "&保存", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.triggered.connect(self.save_file)
        self.save_action.setEnabled(False)

        self.save_as_action = QAction("&另存为...", self)
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_as_action.triggered.connect(self.save_file_as)
        
        self.exit_action = QAction("退出", self)
        self.exit_action.triggered.connect(self.close)
        
        self.refresh_action = QAction(QIcon(style.standardPixmap(QStyle.StandardPixmap.SP_BrowserReload)), "&刷新", self)
        self.refresh_action.setShortcut(QKeySequence.StandardKey.Refresh)
        self.refresh_action.triggered.connect(self.refresh_handler_view)

        self.find_action = QAction(QIcon(style.standardPixmap(QStyle.StandardPixmap.SP_FileDialogInfoView)), "&查找", self)
        self.find_action.setShortcut(QKeySequence.StandardKey.Find)
        self.find_action.triggered.connect(self.text_editor.show_find_panel)

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&文件")
        file_menu.addAction(self.new_action); file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action); file_menu.addAction(self.save_as_action)
        file_menu.addSeparator(); file_menu.addAction(self.exit_action)
        edit_menu = menu_bar.addMenu("&编辑"); edit_menu.addAction(self.find_action)
        
        self.type_menu = menu_bar.addMenu("脚本类型")
        
        self.view_menu = menu_bar.addMenu("&视图")
        self.view_menu.addAction(self.refresh_action)
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.help_panel.toggleViewAction())
        # 顶部“关于”菜单，点击弹出完整说明对话框
        about_menu = menu_bar.addMenu("关于(&A)")
        self.about_overview_action = QAction("项目整体说明...", self)
        self.about_overview_action.triggered.connect(self.show_about_dialog)
        about_menu.addAction(self.about_overview_action)

    def show_about_dialog(self):
        if self._about_dialog is None:
            try:
                self._about_dialog = AboutDialog(self)
            except Exception:
                self._about_dialog = None
        if self._about_dialog is not None:
            try:
                self._about_dialog.load_default()
            except Exception:
                pass
            self._about_dialog.show()
            self._about_dialog.raise_()
            self._about_dialog.activateWindow()

        
    def _populate_type_menu(self):
        """用可用的处理器填充“脚本类型”菜单。"""
        self.type_menu.clear()
        for name, handler in self.script_handlers.items():
            action = QAction(name, self, checkable=True)
            action.setChecked(self.current_handler is handler)
            action.triggered.connect(lambda checked, h=handler: self.switch_handler(h) if checked else self.switch_handler(None))
            self.type_menu.addAction(action)

    def _create_tool_bar(self):
        """创建一个完全通用的工具栏。"""
        self.tool_bar = self.addToolBar("工具")
        self.tool_bar.setMovable(False)
        self.tool_bar.addAction(self.new_action)
        self.tool_bar.addAction(self.open_action)
        self.tool_bar.addAction(self.save_action)
        self.tool_bar.addSeparator()
        self.tool_bar.addAction(self.refresh_action)

    def _create_status_bar(self):
        self.statusBar = self.statusBar()
        self.statusBar.showMessage("准备就绪")
    
    # ==================================================================
    # 核心：处理器驱动的逻辑
    # ==================================================================

    def on_text_changed(self):
        """通用槽函数：当文本改变时，命令当前处理器更新其视图。"""
        if self.current_handler:
            self.current_handler.update_views(self)

    def open_file(self):
        """打开文件，并只在处理器类型确实改变时才切换处理器。"""
        all_filters = ";;".join(set(h.get_file_filter() for h in self.script_handlers.values()))
        file_path_str, _ = QFileDialog.getOpenFileName(self, "打开脚本文件", "", all_filters)
        if not file_path_str: return

        file_path = Path(file_path_str)
        

        # 优先匹配更具体的文件名，如 'st01.anm.txt'
        new_handler = self.handler_file_map.get(file_path.name.lower(), None)
        if not new_handler:
            # 如果没有匹配到完整文件名，则回退到匹配后缀
            new_handler = self.handler_file_map.get(file_path.suffix.lower(), None)


        if not new_handler:
            QMessageBox.warning(self, "不支持的文件类型", f"没有为 '{file_path.suffix}' 类型的文件配置处理器。")
            return
        
        if self.current_handler is not new_handler:
            self.switch_handler(new_handler)
        
        self._load_file_content(file_path)

    def switch_handler(self, handler: ScriptHandler | None):
        if self.current_handler is handler:
            return

        if self.current_handler:
            self.current_handler.clear_ui(self)
        self.current_handler = handler
        if self.current_handler:
            self.current_handler.setup_ui(self)
            highlighter = self.current_handler.create_highlighter(self.text_editor.document())
            self.text_editor.highlighter = highlighter
            self.current_handler.connect_signals(self)
        else:
            self.text_editor.highlighter = None
        self._populate_type_menu()
        self._update_window_title()
    def _load_file_content(self, file_path: Path):
        """
        使用 TextEditor 的新方法来安全地加载内容。
        """
        self.current_file_path = file_path
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # 1. 使用新的、安全的方法设置文本
            self.text_editor.set_document_content(content)

            # 2. 手动触发一次立即更新，以便在加载文件后立即看到结果
            self.run_handler_update()

            self._update_window_title()
            self.statusBar.showMessage(f"已加载 {file_path.name}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开文件失败: {e}")


    def refresh_handler_view(self):
        """手动刷新时，立即执行更新，绕过计时器。"""
        print("\n[DEBUG | Main] refresh_handler_view CALLED (Manual Refresh Button).\n")
        self.run_handler_update()

    # ==================================================================
    # 通用槽函数和文件操作
    # ==================================================================

    def _write_to_file(self, file_path: Path) -> bool:
        """将编辑器内容写入指定路径的辅助函数。"""
        try:
            content = self.text_editor.toPlainText()
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.text_editor.document().setModified(False)
            self.statusBar.showMessage(f"文件已保存至 {file_path.name}", 3000)
            return True
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"无法保存文件到 '{file_path}':\n{e}")
            return False

    def save_file(self):
        """槽函数：保存当前文件。如果文件是新的，则行为同“另存为”。"""
        if self.current_file_path is None:
            self.save_file_as()
        else:
            self._write_to_file(self.current_file_path)

    def save_file_as(self):
        """槽函数：弹出对话框，将文件另存为新文件。"""
        filter_str = self.current_handler.get_file_filter() if self.current_handler else "All Files (*)"
        file_path_str, _ = QFileDialog.getSaveFileName(self, "另存为", "", filter_str)
        if not file_path_str: return
        new_path = Path(file_path_str)
        if self._write_to_file(new_path):
            self.current_file_path = new_path
            self._update_window_title()

    def _on_modification_changed(self, is_modified: bool):
        """槽函数：当编辑器内容被修改时调用。"""
        self.save_action.setEnabled(is_modified)
        self._update_window_title()

    def _update_window_title(self):
        """根据当前文件和修改状态更新主窗口标题。"""
        title = "东方Project脚本编辑器"
        file_name = "未命名"
        is_modified = self.text_editor.document().isModified()
        if self.current_file_path:
            file_name = self.current_file_path.name
        prefix = "* " if is_modified else ""
        handler_name = f" ({self.current_handler.get_name()})" if self.current_handler else ""
        self.setWindowTitle(f"{prefix}{file_name}{handler_name} - {title}")
    
    def _update_syntax_status(self, is_valid: bool, message: str):
        """槽函数：更新状态栏的语法检查信息。"""
        self.statusBar.showMessage(message, 2000)

    def _on_word_under_cursor(self, word: str):
        """槽函数：当光标下的单词变化时，更新帮助面板。"""
        hl = self.text_editor.highlighter
        #print(hl)
        if not hl:
            self.help_panel.show_default()
            return
        # 优先通过高亮器的 get_documentation 获取（允许各处理器做规范化）
        if hasattr(hl, 'get_documentation'):
            try:
                html = hl.get_documentation(word)

            except Exception:
                #print("[DEBUG] 获取指令文档时出错。")
                html = ""
            if html:
                self.help_panel.update_content(html)
                # 同步帮助面板下拉框当前词
                try:
                    self.help_panel.set_current_word(word)
                except Exception:
                    pass
                return
        # 回退：直接用公开字典
        if hasattr(hl, 'instruction_docs'):
            docs = getattr(hl, 'instruction_docs', {}) or {}
            html = docs.get(word, "")
            if html:
                self.help_panel.update_content(html)
                try:
                    self.help_panel.set_current_word(word)
                except Exception:
                    pass
                return
        self.help_panel.show_default()