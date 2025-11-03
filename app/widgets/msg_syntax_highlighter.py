# app/widgets/msg_syntax_highlighter.py

import json
import re
from pathlib import Path
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from typing import Dict, List

class MsgSyntaxHighlighter(QSyntaxHighlighter):
    """
    一个专门用于东方Project MSG 脚本的自定义语法高亮器。
    实现了 TextEditor 所需的通用接口。
    """
    def __init__(self, parent, instruction_docs: Dict[str, str]):
        """
        初始化高亮器。
        
        :param parent: 父对象 (通常是 QTextDocument)。
        :param instruction_docs: 一个预加载的、从指令名到HTML文档字符串的字典。
        """
        super().__init__(parent)
        self.highlighting_rules = []
        self.instruction_docs = instruction_docs

        # --- 1. 定义颜色和样式 ---
        top_level_format = QTextCharFormat()
        top_level_format.setForeground(QColor("#c586c0"))
        top_level_format.setFontWeight(QFont.Weight.Bold)

        self.instruction_format = QTextCharFormat()
        self.instruction_format.setForeground(QColor("#66d9ef"))

        self.parameter_format = QTextCharFormat()
        self.parameter_format.setForeground(QColor("#ae81ff"))
        
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#a6e22e"))
        
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#75715e")) # Grey for comments
        comment_format.setFontItalic(True)

        # --- 2. 定义高亮规则 ---
        self.highlighting_rules.append((re.compile(r'^\s*(entry\s+\w+|T=\d+)\b'), top_level_format))
        self.highlighting_rules.append((re.compile(r'\b(\w+)(?=\()'), self.instruction_format))
        self.highlighting_rules.append((re.compile(r'(?<=[(;])\s*([+-]?(\d+\.\d*f?|\.\d+f?|\d+f?))\b', re.IGNORECASE), self.parameter_format))
        self.highlighting_rules.append((re.compile(r'\(\s*([+-]?(\d+\.\d*f?|\.\d+f?|\d+f?))\b', re.IGNORECASE), self.parameter_format))
        self.highlighting_rules.append((re.compile(r'\btextAdd\((.*)\)'), self.string_format))
        self.highlighting_rules.append((re.compile(r'//[^\n]*'), comment_format))

    def highlightBlock(self, text: str):
        """ PyQt 会对每一行文本自动调用此方法。 """
        for pattern, format in self.highlighting_rules:
            for match in pattern.finditer(text):
                group_index = 0
                # 为有捕获组的规则指定group index
                if format in (self.instruction_format, self.string_format, self.parameter_format):
                    group_index = 1
                
                try:
                    start = match.start(group_index)
                    length = match.end(group_index) - start
                    if length > 0:
                        self.setFormat(start, length, format)
                except IndexError:
                    # 如果捕获组不存在，安全地回退到高亮整个匹配
                    self.setFormat(match.start(), match.end() - match.start(), format)

    # ==================================================================
    # TextEditor 通用接口实现
    # ==================================================================

    def get_completion_words(self) -> List[str]:
        """
        为 MSG 脚本提供代码补全词汇（仅指令）。
        """
        if self.instruction_docs:
            return list(self.instruction_docs.keys())
        return []

    def get_documentation(self, word: str) -> str:
        """
        为 MSG 指令提供悬停文档。
        """
        return self.instruction_docs.get(word, "")
        
    def check_syntax(self, text: str) -> List:
        """
        MSG 脚本没有复杂的语法检查，因此返回一个空列表。
        """
        return []
        
    def get_error_message(self, errors: List) -> str:
        """
        因为没有语法检查，所以总返回空字符串。
        """
        return ""