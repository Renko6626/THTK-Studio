# app/core/script_handler.py

from abc import ABC, abstractmethod
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextDocument

class ScriptHandler(ABC):
    # ... (get_name, get_file_filter, create_highlighter, etc. 保持不变) ...
    @abstractmethod
    def get_name(self) -> str: pass
    @abstractmethod
    def get_file_filter(self) -> str: pass
    @abstractmethod
    def create_highlighter(self, document: QTextDocument) -> object: pass
    @abstractmethod
    def create_parser(self) -> object: pass
    @abstractmethod
    def create_tool_wrapper(self, settings) -> object | None: pass

    # --- vvv 修改/新增的方法 vvv ---

    @abstractmethod
    def setup_ui(self, main_window):
        """
        创建并设置所有此处理器专用的UI元素（Dock面板, 工具栏控件等）。
        这个方法在处理器被激活时调用。
        """
        pass

    @abstractmethod
    def clear_ui(self, main_window):
        """
        清理并销毁所有此处理器创建的专用UI元素。
        这个方法在切换到另一个处理器之前调用。
        """
        pass

    @abstractmethod
    def connect_signals(self, main_window):
        """连接此处理器相关的UI信号。"""
        pass
        
    @abstractmethod
    def update_views(self, main_window):
        """解析文本并更新所有此处理器管理的视图。"""
        pass

    # --- ^^^ 结束修改/新增 ^^^ ---