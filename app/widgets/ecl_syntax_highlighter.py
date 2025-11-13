# app/widgets/ecl_syntax_highlighter.py

import re
import json
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from typing import Dict, List, Optional, Set

class EclSyntaxHighlighter(QSyntaxHighlighter):
    """
    一个专门为东方Project ECL 脚本设计的自定义语法高亮器。
    它现在能够区分内置指令/函数和用户自定义的子程序。
    """
    def __init__(self, 
                 parent, 
                 instruction_docs: Optional[Dict[str, str]] = None,
                 builtin_variables: Optional[List[str]] = None):
        """
        初始化高亮器。
        
        :param parent: 父对象 (通常是 QTextDocument)。
        :param instruction_docs: (可选) 从eclmap映射的指令名到文档的字典。
        :param builtin_variables: (可选) 从JSON文件加载的游戏内置变量列表。
        """
        super().__init__(parent)
        
        self.instruction_docs = instruction_docs or {}
        self.builtin_variables = set(builtin_variables or [])

    # --- 1. 定义颜色和样式 ---

        # 粉色/品红: 关键字 (控制流, 类型)
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("#f92672"))
        self.keyword_format.setFontWeight(QFont.Weight.Bold)

        # 橙色: 内置变量 (如 player_x)
        self.builtin_variable_format = QTextCharFormat()
        self.builtin_variable_format.setForeground(QColor("#fd971f"))
        self.builtin_variable_format.setFontWeight(QFont.Weight.Bold)

        # 绿色: 内置指令/函数 (来源于 instruction_docs)
        self.instruction_format = QTextCharFormat()
        self.instruction_format.setForeground(QColor("#a6e22e"))

        # 青色: 用户自定义的函数/子程序
        self.user_function_format = QTextCharFormat()
        self.user_function_format.setForeground(QColor("#66d9ef"))

        # 紫色: 数字和特殊数值
        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor("#ae81ff"))

        # 橙黄色: 标签和特殊标记
        self.label_format = QTextCharFormat()
        self.label_format.setForeground(QColor("#f99157"))
        
        # 黄色: 字符串 (文件名)
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#e6db74"))

        # 红色/粉色，加粗: 普通变量 ($var, %var)
        self.variable_format = QTextCharFormat()
        self.variable_format.setForeground(QColor("#f8509a"))
        self.variable_format.setFontWeight(QFont.Weight.Bold)
        
        # 灰色，斜体: 注释 (未来可能支持)
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#75715e"))
        self.comment_format.setFontItalic(True)

        # 初始化并构建高亮规则
        self.highlighting_rules = []
        self._rebuild_highlighting_rules()

    def _rebuild_highlighting_rules(self):
        """根据当前的 instruction_docs 与 builtin_variables 重新构建高亮规则。
        规则按优先级由高到低追加到列表中，实际应用时会在 highlightBlock 中反向迭代，
        以保证高优先级规则覆盖低优先级规则。
        """
        rules: list[tuple[re.Pattern, QTextCharFormat]] = []

        # 特殊优先级：行注释 //...
        # 将其置于最高优先级（列表最前），在 highlightBlock 中最后应用，
        # 并在实现中避免覆盖字符串内的 "//"。
        self._comment_re = re.compile(r'//.*')
        rules.append((self._comment_re, self.comment_format))

        # 优先级 1: 关键字 (包括预处理器)
        keywords = ['void', 'var', 'if', 'for', 'while', 'goto', 'return', 'async', 'anim', 'ecli', 'int', 'float', 'sub']
        rules.append((re.compile(r'\b(' + '|'.join(keywords) + r')\b'), self.keyword_format))

        # 优先级 2: 内置变量
        if self.builtin_variables:
            builtin_pattern = r'\b(' + '|'.join(re.escape(v) for v in self.builtin_variables) + r')\b'
            rules.append((re.compile(builtin_pattern), self.builtin_variable_format))

        # 优先级 3: 内置指令/函数 (来源于 docs)
        known_instructions = list(self.instruction_docs.keys())
        if known_instructions:
            instr_pattern_str = r'\b(' + '|'.join(re.escape(name) for name in known_instructions) + r')(?=\s*\()'
            rules.append((re.compile(instr_pattern_str), self.instruction_format))

            # 为 @ 形式的调用也创建一个版本
            instr_pattern_at_str = r'@(' + '|'.join(re.escape(name) for name in known_instructions) + r')(?=\s*\()'
            rules.append((re.compile(instr_pattern_at_str), self.instruction_format))

        # 优先级 4: 用户自定义的函数/子程序调用
        rules.append((re.compile(r'\b([a-zA-Z_]\w+)(?=\s*\()'), self.user_function_format))
        rules.append((re.compile(r'@([a-zA-Z_]\w+)(?=\s*\()'), self.user_function_format))

        # 优先级 5: 标签定义
        rules.append((re.compile(r'^([a-zA-Z_]\w+):'), self.label_format))

        # 优先级 6: 普通变量 ($var, %var)
        rules.append((re.compile(r'([$%][a-zA-Z_]\w*)'), self.variable_format))

        # 优先级 7: 特殊块标记
        rules.append((re.compile(r'^(!\w+\*?)'), self.label_format))

        # 优先级 8: 原生指令 (ins_xxx)
        rules.append((re.compile(r'\b(ins_\d+)\b'), self.instruction_format))

        # 优先级 9: 字符串
        self._string_re = re.compile(r'"[^"]*"')
        rules.append((self._string_re, self.string_format))

        # 优先级 10: 特殊数值
        rules.append((re.compile(r'(\[[-+]?\d+(\.\d*)?f?\])'), self.number_format))

        # 优先级 11: 普通数字
        rules.append((re.compile(r'\b[-+]?(\d+\.\d*f?|\.\d+f?|\d+)\b', re.IGNORECASE), self.number_format))

        # 优先级 12: 行尾的跳转标签
        rules.append((re.compile(r'(@\s*\d+)'), self.label_format))

        self.highlighting_rules = rules

    # 对外方法：更新内置指令文档并重建规则
    def set_instruction_docs(self, instruction_docs: Dict[str, str] | None):
        self.instruction_docs = instruction_docs or {}
        self._rebuild_highlighting_rules()
        try:
            self.rehighlight()
        except Exception:
            pass

    # 可选：更新内置变量并重建规则
    def set_builtin_variables(self, builtin_variables: List[str] | None):
        self.builtin_variables = set(builtin_variables or [])
        self._rebuild_highlighting_rules()
        try:
            self.rehighlight()
        except Exception:
            pass

    def highlightBlock(self, text: str):
        """ PyQt 会对每一行文本自动调用此方法。 """
        # 注意：后设置的格式会覆盖先前设置的格式。
        # 因此我们按“从低优先级到高优先级”的顺序应用，
        # 以确保较高优先级的规则(列表靠前的)最后生效并覆盖低优先级。
        # 预先计算本行的字符串范围，供注释规则避让
        string_spans = []
        try:
            if hasattr(self, '_string_re') and self._string_re is not None:
                string_spans = [(m.start(), m.end()) for m in self._string_re.finditer(text)]
        except Exception:
            string_spans = []

        for pattern, fmt in reversed(self.highlighting_rules):
            for match in pattern.finditer(text):
                group_index = 1 if pattern.groups > 0 else 0
                try:
                    start = match.start(group_index)
                    end = match.end(group_index)

                    # 若为注释规则：跳过位于字符串内部的 //
                    if hasattr(self, '_comment_re') and pattern is self._comment_re:
                        # 如果注释起点位于任一字符串范围内，则忽略该注释匹配
                        in_string = False
                        for s, e in string_spans:
                            if s <= start < e:
                                in_string = True
                                break
                        if in_string:
                            continue

                    length = end - start
                    if length > 0:
                        self.setFormat(start, length, fmt)
                except IndexError:
                    self.setFormat(match.start(), match.end() - match.start(), fmt)

    # ==================================================================
    # TextEditor 通用接口实现 (可选)
    # ==================================================================

    def get_completion_words(self) -> List[str]:
        """为 ECL 脚本提供代码补全词汇。"""
        keywords = ['void', 'var', 'if', 'for', 'while', 'goto', 'return', 'async', 'anim', 'ecli', 'int', 'float', 'sub']
        instructions = list(self.instruction_docs.keys())
        builtins = list(self.builtin_variables)
        return sorted(keywords + instructions + builtins)

    def get_documentation(self, word: str) -> str:
        """为 ECL 指令或内置变量提供悬停文档。"""
        if not word:
            return ""
        
        # 检查是否为内置变量
        if word in self.builtin_variables:
            return f"<b>【内置变量】</b><br>{word}"

        docs = self.instruction_docs or {}
        
        # 检查是否为已知指令/函数
        cleaned_word = str(word).strip().lstrip('@').rstrip(':').split('(')[0]
        if cleaned_word in docs:
            # 返回指令的签名和描述
            doc_content = docs[cleaned_word].replace('\n', '<br>')
            return f"<b>【内置指令】</b><br>{doc_content}"
            
        return ""