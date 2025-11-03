# app/widgets/std_syntax_highlighter.py

import json
import re
from pathlib import Path
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextFormat, QTextCursor
from typing import Dict, List

class StdSyntaxHighlighter(QSyntaxHighlighter):
    IS_COLOR_PROPERTY = QTextFormat.Property.UserProperty + 1
    """
    一个专门用于东方Project STD 脚本的自定义语法高亮器。
    实现了 TextEditor 所需的通用接口，并包含语法检查。
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
        # 记录每个文本块内的颜色片段 (start, end, hex_code)
        self._color_spans = {}

        # --- 1. 定义颜色和样式 ---
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("#f92672")) # Pink for keywords like SCRIPT, ENTRY
        self.keyword_format.setFontWeight(QFont.Weight.Bold)

        self.property_format = QTextCharFormat()
        self.property_format.setForeground(QColor("#66d9ef")) # Cyan for properties like Position, Width

        self.instruction_format = QTextCharFormat()
        self.instruction_format.setForeground(QColor("#a6e22e")) # Green for instructions

        self.parameter_format = QTextCharFormat()
        self.parameter_format.setForeground(QColor("#ae81ff")) # Purple for numbers/floats
        
        self.hex_format = QTextCharFormat()
        self.hex_format.setForeground(QColor("#f99157")) # Orange for hex colors like #...
        
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#e6db74")) # Yellow for strings like .anm paths

        self.label_format = QTextCharFormat()
        self.label_format.setForeground(QColor("#f92672")) # Pink for time labels

        self.label_ref_format = QTextCharFormat()
        self.label_ref_format.setForeground(QColor("#e6db74")) # Yellow for label references
        self.label_ref_format.setFontWeight(QFont.Weight.Bold)
        self.label_ref_format.setToolTip("跳转目标标签或偏移量")

        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#75715e"))
        self.comment_format.setFontItalic(True)
        
        # 语法检查格式
        error_bg_color = QColor(255, 85, 85, 70)
        # 与 ANM 高亮器一致的命名：分号错误高亮格式
        self._semicolon_error_format = QTextCharFormat()
        self._semicolon_error_format.setBackground(error_bg_color)
        self._semicolon_error_format.setProperty(QTextFormat.Property.FullWidthSelection, True)

        # --- 2. 定义高亮规则 ---
        # 关键字
        keywords = ['ANM', 'Std_unknown', 'ENTRY', 'QUAD', 'FACE', 'SCRIPT']
        self.highlighting_rules.append((re.compile(r'\b(' + '|'.join(keywords) + r'):'), self.keyword_format))

        # 属性
        properties = ['Unknown', 'Position', 'Depth', 'Width', 'Height', 'Type', 'Script_index', 'Padding']
        self.highlighting_rules.append((re.compile(r'\b(' + '|'.join(properties) + r'):'), self.property_format))

        hex_rule = re.compile(r'(#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}))\b')
        self.highlighting_rules.append((hex_rule, self.hex_format))
        
        # 指令 (ins_xxx 或翻译后的名称)
        self.highlighting_rules.append((re.compile(r'\b([\w_]+)(?=\()'), self.instruction_format))
        # 规则 1: 标签定义 (支持 1234: 和 @label:)
        # 使用非捕获组 (?:...) 来匹配两种情况
        self.highlighting_rules.append((re.compile(r'^\s*((?:\d+|@[a-zA-Z_]\w*)):'), self.label_format))

        # 规则 2: @标签引用 (例如在 jmp 中)
        # 这个规则很具体，可以放在前面
        self.highlighting_rules.append((re.compile(r'(@[a-zA-Z_]\w*)'), self.label_ref_format))

        # 规则 3: jmp指令中的数字偏移量
        # 这个规则必须放在通用数字规则之前，以获得更高的优先级。
        # 它匹配整个jmp指令，但只捕获第二个数字参数。
        self.highlighting_rules.append((re.compile(r'\bjmp\s*\([^,]+,\s*(\d+)\)'), self.label_ref_format))

        # 时间标签
        self.highlighting_rules.append((re.compile(r'^\s*(\d+):'), self.label_format))

        # 浮点数和整数
        self.highlighting_rules.append((re.compile(r'\b[+-]?(\d+\.\d*f?|\.\d+f?|\d+)\b', re.IGNORECASE), self.parameter_format))
        
        # .anm 文件路径 (作为字符串)
        self.highlighting_rules.append((re.compile(r'\b\w+\.anm\b'), self.string_format))
        
        # 注释: STD 脚本中注释仅用 '//' 表示
        self.highlighting_rules.append((re.compile(r'//[^\n]*'), self.comment_format))

        # 颜色代码行: 所有以 '#' 开头的整行都视为颜色代码并使用 hex_format
        # 该规则放在最后以覆盖其他可能的匹配（如关键字、指令等）
        self.highlighting_rules.append((re.compile(r'^\s*#.*'), self.hex_format))

    def highlightBlock(self, text: str):
        """ [REVISED] 统一的、无歧义的高亮逻辑，并记录颜色片段供悬浮预览使用。 """
        # 为当前块初始化颜色片段列表
        block_number = self.currentBlock().blockNumber()
        self._color_spans[block_number] = []
        for pattern, fmt in self.highlighting_rules:
            for match in pattern.finditer(text):
                # 默认高亮整个匹配，使用原始格式
                final_format = fmt
                group_index = 0
                
                # --- 1. 检查是否需要特殊处理 ---
                if fmt == self.hex_format:
                    # 如果是颜色规则，捕获完整的十六进制颜色代码（第一个捕获组）
                    group_index = 1
                    try:
                        start = match.start(group_index)
                        end = match.end(group_index)
                        hex_code = match.group(group_index)
                        # 记录颜色片段，供悬浮时使用
                        if hex_code:
                            self._color_spans[block_number].append((start, end, hex_code))
                    except IndexError:
                        pass
                
                # --- 2. 检查是否需要高亮特定捕获组 ---
                elif fmt in (self.keyword_format, self.property_format, self.instruction_format, 
                             self.label_format, self.label_ref_format):
                    # 这些规则也只高亮第一个捕获组
                    group_index = 1

                # --- 3. 统一应用最终格式 ---
                try:
                    start = match.start(group_index)
                    length = match.end(group_index) - start
                    if length > 0:
                        self.setFormat(start, length, final_format)
                except IndexError:
                    # 回退到高亮整个匹配
                    self.setFormat(match.start(), match.end() - match.start(), final_format)
    # ==================================================================
    # TextEditor 通用接口实现
    # ==================================================================
    def get_hover_preview_html(self, cursor: QTextCursor) -> str:
        """根据记录的颜色片段，判断光标是否悬停在颜色代码上，并返回预览HTML。"""
        try:
            block_number = cursor.block().blockNumber()
            pos_in_block = cursor.position() - cursor.block().position()
            spans = self._color_spans.get(block_number, [])
            for start, end, hex_code in spans:
                if start <= pos_in_block < end:
                    return self._generate_color_tooltip_html(hex_code)
        except Exception:
            pass
        return ""
    def get_completion_words(self) -> List[str]:
        """为 STD 脚本提供代码补全词汇（仅指令）。"""
        if self.instruction_docs:
            return list(self.instruction_docs.keys())
        return []

    def get_documentation(self, word: str) -> str:
        """为 STD 指令提供悬停文档。"""
        return self.instruction_docs.get(word, "")
        
    def check_syntax(self, text: str) -> List:
        """为 STD 脚本执行分号检查。"""
        return self._check_semicolons(text)
        
    def get_error_message(self, errors: List) -> str:
        """为分号错误生成状态栏消息。"""
        semicolon_count = sum(1 for _, _, fmt in errors if fmt == self._semicolon_error_format)
        if semicolon_count > 0:
            return f"语法错误: {semicolon_count}处缺少分号"
        return ""

    def _check_semicolons(self, text: str) -> List:
        """检查 SCRIPT: 部分的指令行是否缺失了分号。"""
        errors = []
        in_script_section = False

        # 指令关键字：来自参考 JSON 的已知指令名 + ins_0..ins_999
        instruction_keywords = list(self.instruction_docs.keys()) if self.instruction_docs else []
        instruction_keywords += [f'ins_{i}' for i in range(1000)]
        # 构建模式：匹配指令名后紧跟左括号
        pattern = None
        if instruction_keywords:
            try:
                pattern = re.compile(r'\b(' + '|'.join(re.escape(k) for k in instruction_keywords) + r')\b(?=\s*\()')
            except re.error:
                pattern = None

        offset = 0
        for line in text.splitlines():
            stripped_line = line.strip()

            # 区段切换
            if stripped_line == 'SCRIPT:':
                in_script_section = True
            elif stripped_line == 'ENTRY:':
                in_script_section = False

            if not in_script_section:
                offset += len(line) + 1
                continue

            if not stripped_line:
                offset += len(line) + 1
                continue

            # 忽略纯注释/颜色行/标签行
            if stripped_line.startswith(('//', '#', ';')) or stripped_line.endswith(':'):
                offset += len(line) + 1
                continue

            # 移除行内注释后再检查（仅识别 // 注释，# 在行首是颜色代码，行内可能是颜色值的一部分）
            code_part = stripped_line.split('//', 1)[0].rstrip()
            if not code_part:
                offset += len(line) + 1
                continue

            # 若已以分号结束，则无错误
            if code_part.endswith(';'):
                offset += len(line) + 1
                continue

            # 若该行看起来是指令调用且缺少分号，则报错
            if pattern and pattern.search(code_part):
                errors.append((offset, len(line), self._semicolon_error_format))

            offset += len(line) + 1
        return errors
    def _generate_color_tooltip_html(self, hex_code: str) -> str:
        """根据十六进制颜色代码生成一个美观的HTML工具提示。"""
        if not re.match(r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})', hex_code):
            return ""
        try:
            # 统一解析：支持 #RRGGBB 和 #RRGGBBAA（末尾为 alpha）
            m = re.fullmatch(r'#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?', hex_code)
            if not m:
                return ""
            hex_rgb = m.group(1)
            hex_a = m.group(2) or 'FF'  # 默认不透明
            #std脚本的颜色格式是bbggrraa
            b = int(hex_rgb[0:2], 16)
            g = int(hex_rgb[2:4], 16)
            r = int(hex_rgb[4:6], 16)
            a = int(hex_a, 16)

            # 使用明确的 RGBA 值构建 QColor，确保 alpha 正确
            color = QColor(r, g, b, a)

            luminance = (0.299 * r + 0.587 * g + 0.114 * b)
            text_color = "black" if luminance > 128 else "white"
            rgba_css = f"rgba({r}, {g}, {b}, {a / 255.0:.2f})"
            
            style = f"""
                background-color: {rgba_css};
                background-image: 
                    linear-gradient(45deg, #ccc 25%, transparent 25%), 
                    linear-gradient(-45deg, #ccc 25%, transparent 25%),
                    linear-gradient(45deg, transparent 75%, #ccc 75%),
                    linear-gradient(-45deg, transparent 75%, #ccc 75%);
                background-size: 16px 16px;
                background-position: 0 0, 0 8px, 8px -8px, -8px 0px;
                padding: 10px;
                border: 1px solid #555;
                color: {text_color};
                font-family: Consolas, monospace;
            """
            return f"<div style='{style}'><b>{hex_code.upper()}</b><br>R: {r}, G: {g}, B: {b}, A: {a}</div>"
        except Exception:
            return ""