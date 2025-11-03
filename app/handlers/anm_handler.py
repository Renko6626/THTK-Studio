# app/handlers/anm_handler.py (完整、无省略)

from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QFileDialog, QMessageBox, QComboBox, QSplitter
from PyQt6.QtGui import QImage, QPixmap
from PIL.Image import Image as PILImage
import os

from ..core.script_handler import ScriptHandler
from ..core.parser import ScriptParser
from ..core.image_manager import ImageManager
from ..core.thanm_wrapper import ThanmWrapper, ThanmError
from ..widgets.syntax_highlighter import AnmSyntaxHighlighter
from ..widgets.sprite_preview import SpritePreviewPane
from ..widgets.sprite_preview_item import SpritePreviewItem
from ..widgets.thanm_panel import ThanmPanel

class AnmScriptHandler(ScriptHandler):
    def __init__(self):
        self.parser = ScriptParser()
        self.image_manager = ImageManager()
        self.parsed_data = {}
        self.thanm_panel: QWidget | None = None
        self.preview_pane: QWidget | None = None
        self.central_splitter: QSplitter | None = None
        self.jump_combo: QComboBox | None = None
        self.jump_combo_action = None 
        self.toolbar_separator = None
    
    def get_name(self) -> str: return "ANM"
    def get_file_filter(self) -> str: return "ANM Scripts (*.txt;*.ddes)"
    def create_highlighter(self, document): return AnmSyntaxHighlighter(document)
    def create_parser(self): return self.parser
    def create_tool_wrapper(self, settings):
        thanm_path = settings.get_thanm_path()
        anmm_path = settings.get_anmm_path()
        if not thanm_path: return None
        try: return ThanmWrapper(thanm_path, anmm_path)
        except FileNotFoundError as e:
            QMessageBox.critical(None, "路径错误", str(e))
            return None

    def setup_ui(self, main_window):
        """
        [REVISED] 创建并“立即”连接所有 ANM 专用的UI元素。
        """
        # 1. 创建并设置中央控件
        self.preview_pane = SpritePreviewPane(main_window)
        self.central_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.central_splitter.addWidget(main_window.text_editor)
        self.central_splitter.addWidget(self.preview_pane)
        self.central_splitter.setSizes([900, 500])
        main_window.setCentralWidget(self.central_splitter)

        # 2. 创建并连接 Thanm 工具面板
        self.thanm_panel = ThanmPanel(main_window)
        self.thanm_panel.unpack_requested.connect(lambda: self.on_unpack_request(main_window))
        self.thanm_panel.pack_requested.connect(lambda: self.on_pack_request(main_window))
        main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.thanm_panel)
        main_window.view_menu.addAction(self.thanm_panel.toggleViewAction())

        # 3. 创建并连接快速跳转 ComboBox
        self.jump_combo = QComboBox()
        self.jump_combo.setMinimumWidth(150)
        #print(f"[DEBUG] setup_ui: Created jump_combo with id: {id(self.jump_combo)}")
        self.jump_combo.activated.connect(lambda index: self._jump_to_block(main_window, index))
        #print(f"[DEBUG] setup_ui: CONNECTED jump_combo with id: {id(self.jump_combo)}")

        self.toolbar_separator = main_window.tool_bar.addSeparator()
        self.jump_combo_action = main_window.tool_bar.addWidget(self.jump_combo)

        
    def clear_ui(self, main_window):
        if self.thanm_panel:
            main_window.removeDockWidget(self.thanm_panel)
            self.thanm_panel.deleteLater()
            self.thanm_panel = None
        if self.jump_combo_action:
            main_window.tool_bar.removeAction(self.jump_combo_action)
            main_window.tool_bar.removeAction(self.toolbar_separator)
            if self.jump_combo: self.jump_combo.deleteLater()
            self.jump_combo_action.deleteLater()
            self.toolbar_separator.deleteLater()
            self.jump_combo, self.jump_combo_action, self.toolbar_separator = None, None, None
        if self.central_splitter:
            main_window.setCentralWidget(main_window.text_editor)
            self.central_splitter.deleteLater()
            self.central_splitter, self.preview_pane = None, None

    def connect_signals(self, main_window):
        """
        [REVISED] 此方法现在只负责连接不属于本处理器的外部信号，或进行设置。
        """
        if self.thanm_panel:
            self.thanm_panel.set_thanm_path(main_window.settings.get_thanm_path())
            self.thanm_panel.thanm_path_changed.connect(
                lambda path: main_window.settings.set_user_path("user_thanm_path", path))
            self.thanm_panel.set_anmm_path(main_window.settings.get_anmm_path())
            self.thanm_panel.anmm_path_changed.connect(
                lambda path: main_window.settings.set_user_path("user_anmm_path", path))

    def update_views(self, main_window):
        """
        [REVISED] 此方法现在只负责数据解析和更新 ANM 专用视图。
        """
        script_text = main_window.text_editor.toPlainText()
        
        # 1. 更新动态高亮规则 (原 TextEditor 逻辑)
        if hasattr(main_window.text_editor.highlighter, 'update_dynamic_rules'):
            main_window.text_editor.highlighter.update_dynamic_rules(script_text)
            
        # 2. 解析数据 (Handler 自身的核心职责)
        if script_text.strip() and main_window.current_file_path:
            self.parsed_data = self.parser.parse(script_text)
        else:
            self.parsed_data = {}
        
        # 3. 更新 ANM 专用UI (精灵预览)
        self._update_sprite_previews(main_window)
        
        # 4. 更新 ANM 专用UI (快速跳转)
        self._update_jump_combo()

    def _update_sprite_previews(self, main_window):
        self.preview_pane.show_placeholder()
        script_text = main_window.text_editor.toPlainText() # 需要 text 来获取 sprite locations
        sprite_count = 0
        if self.parsed_data:
            if main_window.current_file_path:
                self.image_manager.set_base_path(main_window.current_file_path.parent)
            sprite_locations = self.parser.get_all_sprite_locations(script_text)
            for entry_name, entry_data in self.parsed_data.get("entries", {}).items():
                image_path = entry_data.get('image_path')
                if not image_path: continue
                for sprite_name, rect in entry_data.get('sprites', {}).items():
                    sprite_pil_img = self.image_manager.get_sprite_image(image_path, rect)
                    if sprite_pil_img:
                        pixmap = self._pil_to_qpixmap(sprite_pil_img)
                        full_name = f"{entry_name}/{sprite_name}"
                        item = SpritePreviewItem(full_name, pixmap)
                        line_number = sprite_locations.get(full_name)
                        if line_number: item.clicked.connect(lambda name=full_name, line=line_number: self._jump_to_sprite_definition(main_window, name, line))
                        self.preview_pane.add_sprite_preview(item)
                        sprite_count += 1
        status_msg = f"刷新完成！成功加载 {sprite_count} 个精灵。" if sprite_count > 0 else "刷新完成。"
        main_window.statusBar.showMessage(status_msg, 5000)

    def _update_jump_combo(self):
        self.jump_combo.clear()
        self.jump_combo.addItem("快速跳转...")
        if not self.parsed_data: return
        all_blocks = []
        
        for name, data in self.parsed_data.get("entries", {}).items(): all_blocks.append(("entry", name, data['line']))
        for name, data in self.parsed_data.get("scripts", {}).items(): all_blocks.append(("script", name, data['line']))
        all_blocks.sort(key=lambda x: x[2])
        #print(len(all_blocks))
        for type, name, line in all_blocks:
            display_text = f"{type} {name} (行 {line})"
            self.jump_combo.addItem(display_text, userData=line)

    # ==================================================================
    # Thanm 工具流槽函数
    # ==================================================================

    def on_unpack_request(self, main_window):
        tool = self.create_tool_wrapper(main_window.settings)
        if not tool:
             QMessageBox.warning(main_window, "工具未找到", "未找到 thanm.exe。请在 Thanm 面板中手动指定路径。")
             return
        anm_path, _ = QFileDialog.getOpenFileName(main_window, "选择要解包的 ANM 文件", "", "ANM Files (*.anm)")
        if not anm_path: return
        selected_version = self.thanm_panel.get_selected_version()
        if not selected_version:
            QMessageBox.warning(main_window, "提示", "请先在 Thanm 面板中选择一个游戏版本。")
            return
        try:
            output_dir = Path(anm_path).with_suffix('')
            main_window.statusBar.showMessage(f"正在解包到 {output_dir}...")
            spec_file = tool.unpack_all(selected_version, anm_path, str(output_dir))
            if spec_file and os.path.exists(spec_file):
                QMessageBox.information(main_window, "成功", f"文件已成功解包到:\n{output_dir}")
                main_window._load_file_content(Path(spec_file))
            else:
                QMessageBox.warning(main_window, "警告", "解包操作已执行，但在输出目录中未找到指令文件。")
        except ThanmError as e:
            QMessageBox.critical(main_window, "Thanm 错误", f"{e}\n\n详细信息:\n{e.stderr}")

    def on_pack_request(self, main_window):
        if not main_window.current_file_path:
            QMessageBox.warning(main_window, "提示", "请先打开一个要打包的指令文件。")
            return
        tool = self.create_tool_wrapper(main_window.settings)
        if not tool:
             QMessageBox.warning(main_window, "工具未找到", "未找到 thanm.exe。请在 Thanm 面板中手动指定路径。")
             return
        selected_version = self.thanm_panel.get_selected_version()
        if not selected_version:
            QMessageBox.warning(main_window, "提示", "请先在 Thanm 面板中选择一个游戏版本。")
            return
        default_name = main_window.current_file_path.with_suffix('.anm').name
        output_anm, _ = QFileDialog.getSaveFileName(main_window, "选择新 ANM 文件的保存位置", default_name, "ANM Files (*.anm)")
        if not output_anm: return
        try:
            main_window.statusBar.showMessage(f"正在打包到 {output_anm}...")
            tool.create(selected_version, output_anm, str(main_window.current_file_path))
            QMessageBox.information(main_window, "成功", f"已成功打包文件到:\n{output_anm}")
        except ThanmError as e:
            QMessageBox.critical(main_window, "Thanm 错误", f"{e}\n\n详细信息:\n{e.stderr}")

    # ==================================================================
    # 辅助方法
    # ==================================================================


    def _pil_to_qpixmap(self, pil_image: PILImage) -> QPixmap:
        if pil_image.mode != "RGBA": pil_image = pil_image.convert("RGBA")
        qimage = QImage(pil_image.tobytes(), pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimage)

    def _jump_to_sprite_definition(self, main_window, sprite_name: str, line_number: int):
        main_window.text_editor.jump_to_line(line_number)
        main_window.statusBar.showMessage(f"已跳转到 '{sprite_name}' 的定义处 (行 {line_number})", 3000)

    def _jump_to_block(self, main_window, index: int):
        #print(f"\n--- [DEBUG] _jump_to_block CALLED! --- Index: {index}")
        if not self.jump_combo or index <= 0: return
        line_number = self.jump_combo.itemData(index)
        if line_number:
            main_window.text_editor.jump_to_line(line_number)
        self.jump_combo.setCurrentIndex(0)