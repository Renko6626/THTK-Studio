# app/widgets/ecl_syntax_highlighter.py

import re
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextFormat
from typing import Dict, List, Optional

class EclSyntaxHighlighter(QSyntaxHighlighter):
    """
    一个专门为东方Project ECL 脚本设计的自定义语法高亮器。
    它识别类C语法、原生指令、特殊标记和变量。
    """
    def __init__(self, parent, instruction_docs: Optional[Dict[str, str]] = None):
        """
        初始化高亮器。
        
        :param parent: 父对象 (通常是 QTextDocument)。
        :param instruction_docs: (可选) 从eclmap映射的指令名到文档的字典。
        """
        super().__init__(parent)
        self.highlighting_rules = []
        # instruction_docs 对于ECL是可选的，但我们保留它以备将来使用
        self.instruction_docs = instruction_docs if instruction_docs is not None else {}

        # --- 1. 定义颜色和样式 ---
        # 粉色: 关键字 (控制流, 类型)
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("#f92672"))
        self.keyword_format.setFontWeight(QFont.Weight.Bold)

        # 青色: 函数名
        self.function_format = QTextCharFormat()
        self.function_format.setForeground(QColor("#66d9ef"))

        # 绿色: 原生指令 (ins_xxx) 或映射后的指令
        self.instruction_format = QTextCharFormat()
        self.instruction_format.setForeground(QColor("#a6e22e"))

        # 紫色: 数字和特殊数值
        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor("#ae81ff"))

        # 橙色: 标签和特殊标记
        self.label_format = QTextCharFormat()
        self.label_format.setForeground(QColor("#f99157"))
        
        # 黄色: 字符串 (文件名)
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#e6db74"))

        # 红色/粉色，加粗: 变量
        self.variable_format = QTextCharFormat()
        self.variable_format.setForeground(QColor("#f92672"))
        self.variable_format.setFontWeight(QFont.Weight.Bold)
        
        # 灰色，斜体: 注释 (ECL中没有标准注释，但我们可以预留)
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#75715e"))
        self.comment_format.setFontItalic(True)
        
        # --- 2. 定义高亮规则 (顺序很重要!) ---
        
        # a) 预处理器指令 (anim, ecli)
        self.highlighting_rules.append((re.compile(r'\b(anim|ecli)\b'), self.keyword_format))
        
        # b) C风格关键字
        keywords = ['void', 'var', 'if', 'for', 'while', 'goto', 'return', 'async']
        self.highlighting_rules.append((re.compile(r'\b(' + '|'.join(keywords) + r')\b'), self.keyword_format))
        
        # c) 函数定义和调用 (匹配名称)
        # - `void FunctionName(...)`
        # - `@FunctionName() async`
        # - `FunctionName:` (标签形式)
        self.highlighting_rules.append((re.compile(r'\b([a-zA-Z_]\w+)(?=\s*\()'), self.function_format))
        self.highlighting_rules.append((re.compile(r'@([a-zA-Z_]\w+)(?=\s*\()'), self.function_format))
        
        # d) 标签定义 (FunctionName_123:)
        self.highlighting_rules.append((re.compile(r'^([a-zA-Z_]\w+):'), self.label_format))

        # e) 变量使用 ($A)
        self.highlighting_rules.append((re.compile(r'(\$[a-zA-Z_]\w*)'), self.variable_format))
        
        # f) 特殊块标记 (!XXX, !*)
        self.highlighting_rules.append((re.compile(r'^(!\w+\*?)'), self.label_format))
        
        # g) 原生指令 (ins_xxx)
        # 我们用一个更通用的规则来匹配所有看起来像函数调用的东西作为指令
        # 这样即使用户没有eclmap，ins_xxx也能被高亮
        self.highlighting_rules.append((re.compile(r'\b(ins_\d+)\b'), self.instruction_format))
        
        # h) 字符串 (文件名)
        self.highlighting_rules.append((re.compile(r'"[^"]*"'), self.string_format))

        # i) 特殊数值 ([-123.4f])
        self.highlighting_rules.append((re.compile(r'(\[[-+]?\d+(\.\d*)?f?\])'), self.number_format))
        
        # j) 普通数字 (浮点数和整数)
        self.highlighting_rules.append((re.compile(r'\b[-+]?(\d+\.\d*f?|\.\d+f?|\d+)\b', re.IGNORECASE), self.number_format))
        
        # k) 行尾的跳转标签 (@ 0)
        self.highlighting_rules.append((re.compile(r'(@\s*\d+)'), self.label_format))

    def highlightBlock(self, text: str):
        """ PyQt 会对每一行文本自动调用此方法。 """
        for pattern, fmt in self.highlighting_rules:
            for match in pattern.finditer(text):
                group_index = 1 if pattern.groups > 0 else 0
                try:
                    start = match.start(group_index)
                    length = match.end(group_index) - start
                    if length > 0:
                        self.setFormat(start, length, fmt)
                except IndexError:
                    # 如果没有捕获组，则高亮整个匹配
                    self.setFormat(match.start(), match.end() - match.start(), fmt)

    # ==================================================================
    # TextEditor 通用接口实现 (可选)
    # ==================================================================

    def get_completion_words(self) -> List[str]:
        """为 ECL 脚本提供代码补全词汇。"""
        # 可以将关键字和已知指令合并
        keywords = ['void', 'var', 'if', 'for', 'while', 'goto', 'return', 'async']
        instructions = list(self.instruction_docs.keys())
        return keywords + instructions

    def get_documentation(self, word: str) -> str:
        """为 ECL 指令提供悬停文档。"""
        if not word:
            return ""
        docs = self.instruction_docs or {}
        #print(word)
        # 直接命中
        if word in docs:
            #print("[DEBUG] 直接命中文档。")
            return docs[word]
        # 简单规范化尝试：去掉@前缀、尾部冒号与参数括号，大小写回退
        w = str(word).strip()
        w = w.lstrip('@').rstrip(':')
        w = w.split('(')[0]
        if w in docs:
            return docs[w]
        lw = w.lower()
        if lw in docs:
            return docs[lw]
        uw = w.upper()
        if uw in docs:
            return docs[uw]
        return ""