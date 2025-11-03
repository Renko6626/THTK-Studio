# app/widgets/syntax_highlighter.py

import json
import re
from pathlib import Path
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextFormat
#从 app.core.settings 导入默认路径
from app.core.settings import Settings

settings = Settings()
DEFAULT_INSTRUCTION_PATH = settings.get_instructions_path()
DEFAULT_VARIABLE_PATH = settings.get_variables_path()
DEFAULT_SYNTAX_PATH = settings.get_anm_syntax_path()

class AnmSyntaxHighlighter(QSyntaxHighlighter):
    """
    一个用于 ANM 脚本的自定义语法高亮器。
    实现了 TextEditor 所需的通用接口。
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.instruction_docs = {}
        self.variable_docs = {}
        self.highlighting_rules = []
        
        self.sprite_names = set()
        self.label_names = set()

        # --- 1. 定义颜色和样式 ---
        keyword_format = QTextCharFormat(); keyword_format.setForeground(QColor("#f92672")); keyword_format.setFontWeight(QFont.Weight.Bold)
        property_format = QTextCharFormat(); property_format.setForeground(QColor("#66d9ef"))
        instruction_format = QTextCharFormat(); instruction_format.setForeground(QColor("#a6e22e"))
        sprite_usage_format = QTextCharFormat(); sprite_usage_format.setForeground(QColor("#fd971f"))
        sprite_def_format = QTextCharFormat(); sprite_def_format.setForeground(QColor("#A072D3")); sprite_def_format.setFontWeight(QFont.Weight.Bold)
        string_format = QTextCharFormat(); string_format.setForeground(QColor("#e6db74"))
        number_format = QTextCharFormat(); number_format.setForeground(QColor("#ae81ff"))
        comment_format = QTextCharFormat(); comment_format.setForeground(QColor("#75715e")); comment_format.setFontItalic(True)
        self.label_format = QTextCharFormat(); self.label_format.setForeground(QColor("#f92672"))
        variable_format = QTextCharFormat(); variable_format.setForeground(QColor("#c586c0"))
        
        # 新增：错误高亮格式
        error_bg_color = QColor(255, 85, 85, 70)
        self._bracket_error_format = QTextCharFormat(); self._bracket_error_format.setBackground(error_bg_color)
        self._semicolon_error_format = QTextCharFormat(); self._semicolon_error_format.setBackground(error_bg_color)
        self._semicolon_error_format.setProperty(QTextFormat.Property.FullWidthSelection, True)

        # --- 2. 加载静态规则 ---
        try:
            with open(DEFAULT_SYNTAX_PATH, "r", encoding='utf-8') as f:
                defs = json.load(f)
            for word in defs["keywords"]:
                if word == 'sprite': continue
                self.highlighting_rules.append((re.compile(f"\\b{word}\\b"), keyword_format))
            for word in defs["properties"]:
                self.highlighting_rules.append((re.compile(f"\\b{word}\\b(?=\\s*[:=])"), property_format))
        except FileNotFoundError:
            print("警告: syntax_definitions.json 未找到。")

        try:
            with open(DEFAULT_INSTRUCTION_PATH, "r", encoding='utf-8') as f:
                instructions_data = json.load(f)
            instruction_names = []
            for key, value in instructions_data.items():
                full_name, desc = value.get("name", ""), value.get("description", "无描述。")
                name_match = re.match(r'(\w+)\(.*\)', full_name)
                if name_match:
                    instruction_name = name_match.group(1)
                    instruction_names.append(instruction_name)
                    self.instruction_docs[instruction_name] = f"<b>{full_name}</b><br>{desc}"
            if instruction_names:
                self.highlighting_rules.append((re.compile("\\b(" + "|".join(instruction_names) + ")\\b(?=\\s*\\()"), instruction_format))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"错误: 处理 instructions.json 时出错: {e}")

        try:
            with open(DEFAULT_VARIABLE_PATH, "r", encoding='utf-8') as f:
                variables_data = json.load(f)
            variable_names = []
            for key, value in variables_data.items():
                var_name, id_repr = key, value.get('name', '')
                doc_str = f"<b>{var_name}</b> ({value.get('type', '未知')})<br>{value.get('description', '无描述。')}"
                if id_repr: doc_str += f"<br>ID表示: {id_repr}"
                self.variable_docs[var_name] = doc_str
                if var_name.startswith(('%', '$')): variable_names.append(re.escape(var_name))
                if id_repr and id_repr.startswith('['): variable_names.append(re.escape(id_repr))
            if variable_names:
                self.highlighting_rules.append((re.compile(r'(' + '|'.join(variable_names) + r')'), variable_format))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"错误: 处理 variables.json 时出错: {e}")
            
        self.highlighting_rules.append((re.compile(r'"[^"]*"'), string_format))
        self.highlighting_rules.append((re.compile(r'^\s*([a-zA-Z_][\w]*):'), self.label_format))
        self.highlighting_rules.append((re.compile(r'\b[+-]?(\d+\.\d*f?|\.\d+f?|\d+f?)\b', re.IGNORECASE), number_format))
        self.highlighting_rules.append((re.compile(r'//[^\n]*'), comment_format))
        self.highlighting_rules.append((re.compile(r'^\s*sprite\s+[a-zA-Z_]\w*'), sprite_def_format))

        # --- 动态规则占位符 ---
        self.sprite_usage_rule = (None, sprite_usage_format)

    def highlightBlock(self, text: str):
        for pattern, format in self.highlighting_rules:
            for match in pattern.finditer(text):
                if format == self.label_format:
                     self.setFormat(match.start(1), match.end(1) - match.start(1), format)
                else:
                    self.setFormat(match.start(), match.end() - match.start(), format)
        pattern, format = self.sprite_usage_rule
        if pattern:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), format)

    def update_dynamic_rules(self, full_text: str):
        sprite_def_pattern = r'^\s*sprite\s+([a-zA-Z_]\w*)\s*='
        self.sprite_names = set(re.findall(sprite_def_pattern, full_text, re.MULTILINE))
        if self.sprite_names:
            sprite_usage_pattern = re.compile("\\b(" + "|".join(re.escape(name) for name in self.sprite_names) + ")\\b")
            self.sprite_usage_rule = (sprite_usage_pattern, self.sprite_usage_rule[1])
        else:
            self.sprite_usage_rule = (None, self.sprite_usage_rule[1])
        label_def_pattern = r'^\s*([a-zA-Z_][\w]*):'
        self.label_names = set(re.findall(label_def_pattern, full_text, re.MULTILINE))
        # self.rehighlight() is called by TextEditor after this

    # ==================================================================
    # TextEditor 通用接口实现
    # ==================================================================

    def get_completion_words(self) -> list[str]:
        """返回所有可用于代码补全的词汇。"""
        return list(self.instruction_docs.keys()) + \
               list(self.variable_docs.keys()) + \
               list(self.sprite_names) + \
               list(self.label_names)

    def get_documentation(self, word: str) -> str:
        """根据单词返回其HTML格式的文档字符串。"""
        # 优先查找指令，其次是变量
        return self.instruction_docs.get(word) or self.variable_docs.get(word, "")

    def check_syntax(self, text: str) -> list:
        """执行所有 ANM 语法检查并返回错误列表。"""
        # 我们将返回一个 (index, length, format) 格式的元组列表
        errors = []
        errors.extend(self._check_brackets(text))
        errors.extend(self._check_semicolons(text))
        return errors
        
    def get_error_message(self, errors: list) -> str:
        """根据错误列表生成一条状态栏消息。"""
        bracket_count = sum(1 for _, _, fmt in errors if fmt == self._bracket_error_format)
        semicolon_count = sum(1 for _, _, fmt in errors if fmt == self._semicolon_error_format)
        
        messages = []
        if bracket_count > 0: messages.append(f"{bracket_count}个括号不匹配")
        if semicolon_count > 0: messages.append(f"{semicolon_count}处缺少分号")
        
        return "语法错误: " + ", ".join(messages)

    # --- 语法检查辅助方法 (从 TextEditor 迁移而来) ---
    
    def _check_brackets(self, text: str) -> list:
        stack, errors = [], []
        for i, char in enumerate(text):
            if char == '{': stack.append(i)
            elif char == '}':
                if stack: stack.pop()
                else: errors.append((i, 1, self._bracket_error_format)) # (index, length, format)
        for i in stack:
            errors.append((i, 1, self._bracket_error_format))
        return errors

    def _check_semicolons(self, text: str) -> list:
        errors = []
        if not self.instruction_docs: return []

        instruction_keywords = self.instruction_docs.keys()
        if not instruction_keywords: return []
        
        pattern = re.compile(r'\b(' + '|'.join(re.escape(k) for k in instruction_keywords) + r')\b(?=\s*\()')

        offset = 0
        for line in text.splitlines():
            stripped_line = line.strip()
            is_skippable = (not stripped_line or
                            stripped_line.startswith(('//', '#')) or
                            stripped_line.endswith(('{', '}', ':', ';')))
            
            if not is_skippable and pattern.search(stripped_line):
                # 错误位置是这一行的开头，长度是整行，格式要求整行高亮
                errors.append((offset, len(line), self._semicolon_error_format))
            
            offset += len(line) + 1
        return errors