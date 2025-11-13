# 完整最终版 app/widgets/text_editor.py

from PyQt6.QtWidgets import QPlainTextEdit, QTextEdit, QToolTip, QCompleter, QWidget
from PyQt6.QtGui import (
    QKeyEvent,
    QTextCharFormat,
    QTextCursor,
    QFont,
    QColor,
    QPainter,
    QPaintEvent,
    QTextFormat,
    QSyntaxHighlighter,
    QTextDocument,
    QLinearGradient,
    QPen
)
from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel, QTimer, QRect, QSize
import re
from PyQt6.QtWidgets import QStyledItemDelegate, QStyle

from .search_panel import SearchPanel
# NOTE: syntax highlighter class names are dynamically assigned by handlers, avoid direct dependency on a specific one here.

class LineNumberArea(QWidget):
    """用于显示行号的侧边栏控件。"""
    def __init__(self, editor: "TextEditor"):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event: QPaintEvent):
        self.editor.lineNumberAreaPaintEvent(event)

class MinimapArea(QWidget):
    """右侧小地图控件。"""
    def __init__(self, editor: "TextEditor"):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.minimapWidth(), 0)

    def paintEvent(self, event: QPaintEvent):
        self.editor.minimapPaintEvent(event)
    
    def mousePressEvent(self, event):
        self.editor.minimapMouseEvent(event)
    
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.editor.minimapMouseEvent(event)

class TextEditor(QPlainTextEdit):
    """
    一个通用的、“被动”的文本编辑器核心：负责文本显示与信号发射，
    具体的分析与视图更新由外部（主窗口/处理器）驱动。
    """
    syntax_status_changed = pyqtSignal(bool, str)
    word_under_cursor_changed = pyqtSignal(str)
    INDENT_WIDTH = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        # 颜色与边框走样式表；字体族与字号改由 QFont 控制，便于运行时调整
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #2b2b2b; color: #f8f8f2;
                border: 1px solid #44475a; selection-background-color: #44475a;
            }
        """)
        editor_font = QFont("Consolas", 12); editor_font.setWeight(QFont.Weight.DemiBold)
        self.setFont(editor_font)
        # 将制表符宽度设置为 INDENT_WIDTH 个空格的宽度，避免显示为默认的 8 个字符宽
        try:
            space_width = self.fontMetrics().horizontalAdvance(' ')
            self.setTabStopDistance(space_width * self.INDENT_WIDTH)
        except Exception:
            # 兼容性保障：如果运行环境不支持 setTabStopDistance，则忽略
            pass
        
        self.line_number_area = LineNumberArea(self)
        # 小地图
        self._minimap_enabled = True
        self._minimap_width = 64
        self.minimap_area = MinimapArea(self)
        self.blockCountChanged.connect(self.updateAuxiliaryAreasWidth)
        self.updateRequest.connect(self._on_update_request)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.updateAuxiliaryAreasWidth(0)

        self.setMouseTracking(True)
        self._last_hovered_word = None

        self.find_panel = SearchPanel(self)
        self.find_panel.hide()
        self.find_panel.closed.connect(self.find_panel.hide)
        self.find_panel.find_next.connect(self._find_next)
        self.find_panel.find_previous.connect(self._find_previous)
        self.find_panel.search_text_changed.connect(self._update_search_count)

        self._highlighter: QSyntaxHighlighter | None = None

        self.completer = QCompleter(self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.activated.connect(self._insert_completion)

        popup = self.completer.popup()
        popup.setUniformItemSizes(True)
        popup.setWindowFlag(Qt.WindowType.FramelessWindowHint, False)
        popup.setIconSize(QSize(16, 16))

        # 使用与编辑器一致的等宽字体，并让项目间距更紧凑
        mono_font = QFont("Consolas", 11)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        popup.setFont(mono_font)

        # 深色现代样式（背景、文字、选中样式、间距）
        popup.setStyleSheet("""
            QListView {
            background-color: #2b2b2b;
            color: #f8f8f2;
            border: 1px solid #44475a;
            padding: 2px;
            }
            QListView::item {
            padding: 4px 8px;
            margin: 0px;
            }
            QListView::item:selected {
            background-color: #44475a;
            color: #f8f8f2;
            }
            QListView::item:hover {
            background-color: #3b3a3f;
            }
        """)

        
        self.completion_model = QStringListModel()
        self.completer.setModel(self.completion_model)


        self.cursorPositionChanged.connect(self._on_cursor_position_changed)
        
        tooltip_font = QFont("Segoe UI", 10); tooltip_font.setWeight(QFont.Weight.Bold)
        QToolTip.setFont(tooltip_font)

    @property
    def highlighter(self) -> QSyntaxHighlighter | None:
        return self._highlighter

    @highlighter.setter
    def highlighter(self, new_highlighter: QSyntaxHighlighter | None):
        if self._highlighter:
            self._highlighter.setDocument(None)
        
        self._highlighter = new_highlighter
        
        if self._highlighter:
            self._highlighter.setDocument(self.document())
        

    def update_completion_model(self):
        """由外部 (MainWindow) 调用的公共方法。"""
        all_words = []
        if self.highlighter and hasattr(self.highlighter, 'get_completion_words'):
            all_words = self.highlighter.get_completion_words()
        self.completion_model.setStringList(sorted(list(set(all_words))))
    def trigger_completion(self):
        """由外部 (MainWindow) 调用的公共方法。"""
        completion_prefix = self._text_under_cursor()
        if len(completion_prefix) >= 2 and self.textCursor().atBlockEnd():
            self.completer.setCompletionPrefix(completion_prefix)
            cr = self.cursorRect()
            cr.setWidth(self.completer.popup().sizeHintForColumn(0) + self.completer.popup().verticalScrollBar().sizeHint().width())
            self.completer.complete(cr)
        else:
            self.completer.popup().hide()

    def set_document_content(self, text: str):
        """
        安全地设置文档内容，并控制更新流程。
        """
        self._is_setting_text = True
        try:
            # 清空文档时也会触发 textChanged，但会被抑制
            self.clear() 
            # 插入新文本
            self.insertPlainText(text)
            self.document().setModified(False)
        finally:
            self._is_setting_text = False
    

    def highlight_errors(self, errors: list):
        """通用实现：根据高亮器提供的错误信息进行高亮。"""
        selections = []
        if not errors:
            self.setExtraSelections([])
            return
            
        for error_info in errors:
            # 假设错误信息是一个元组 (index, length, format)
            try:
                index, length, error_format = error_info
                sel = QTextEdit.ExtraSelection()
                sel.format = error_format
                cursor = self.textCursor()
                cursor.setPosition(index)
                cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, length)
                
                # 如果格式要求高亮整行
                if error_format.property(QTextFormat.Property.FullWidthSelection):
                    cursor.clearSelection()
                    cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
                    
                sel.cursor = cursor
                selections.append(sel)
            except (ValueError, TypeError):
                print(f"警告: 无效的错误信息格式: {error_info}")
        
        self.setExtraSelections(selections)

    def mouseMoveEvent(self, event):
        """
        悬浮提示逻辑：
        1) 优先向高亮器请求特殊 HTML 预览（如颜色块等）；
        2) 否则回退为普通的指令/单词说明。
        """
        cursor = self.cursorForPosition(event.pos())
        
        # --- 1. 尝试获取特殊预览 ---
        preview_html = ""
        if self.highlighter and hasattr(self.highlighter, 'get_hover_preview_html'):
            preview_html = self.highlighter.get_hover_preview_html(cursor)
        
        if preview_html:
            # 如果高亮器返回了 HTML，直接显示并返回
            QToolTip.showText(event.globalPosition().toPoint(), preview_html, self)
            super().mouseMoveEvent(event)
            return

        # --- 2. 如果没有特殊预览，执行普通单词文档逻辑 ---
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        word = cursor.selectedText()

        # 避免在同一个单词上重复触发工具提示
        if self._last_hovered_word == word and QToolTip.isVisible():
            super().mouseMoveEvent(event)
            return
        self._last_hovered_word = word
        
        doc_string = ""
        if self.highlighter and hasattr(self.highlighter, 'get_documentation'):
            doc_string = self.highlighter.get_documentation(word)
        
        if doc_string:
            QToolTip.showText(event.globalPosition().toPoint(), doc_string, self)
        else:
            # 没有任何提示可显示时，隐藏并重置
            QToolTip.hideText()
            self._last_hovered_word = None

        super().mouseMoveEvent(event)

    def _text_under_cursor(self) -> str:
        """获取当前光标左侧正在输入的单词。"""
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        return cursor.selectedText()

    def _insert_completion(self, completion: str):
        """将选择的补全项插入文本。"""
        cursor = self.textCursor()
        # 获取当前正在补全的单词前缀
        extra = len(completion) - len(self.completer.completionPrefix())
        # 将光标向右移动，选中需要被替换的部分
        cursor.movePosition(QTextCursor.MoveOperation.Left)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfWord)
        cursor.insertText(completion[-extra:])
        self.setTextCursor(cursor)
    def show_find_panel(self):
        self.find_panel.show()
        self.find_panel.raise_()
        self.find_panel.focus_input()
        self._update_search_count(self.find_panel.get_search_text())
    
    def resizeEvent(self, event):
        """当编辑器大小改变时，重新定位行号栏和搜索面板。"""
        super().resizeEvent(event)
        
        # 定位行号栏
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))
        # 定位小地图
        if self._minimap_enabled and self.minimap_area:
            self.minimap_area.setGeometry(QRect(cr.right() - self.minimapWidth() + 1, cr.top(), self.minimapWidth(), cr.height()))
        
        # 定位搜索面板
        if self.find_panel:
            margin = 10
            x = self.viewport().width() - self.find_panel.width() - margin
            y = margin
            self.find_panel.move(x, y)

    def leaveEvent(self, event):
        QToolTip.hideText()
        self._last_hovered_word = None
        super().leaveEvent(event)

    def _on_cursor_position_changed(self):
        """
        当光标位置改变时，仅处理帮助提示逻辑（补全触发在外部更新流程中）。
        """
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        word = cursor.selectedText()
        self.word_under_cursor_changed.emit(word)



    def keyPressEvent(self, event: QKeyEvent):
        key=event.key()
        cursor = self.textCursor()
        """覆写按键事件，处理补全列表的交互。"""
        if key == Qt.Key.Key_BraceLeft:
            # 先调用父类的方法，插入 '{'
            super().keyPressEvent(event)
            # 然后在光标后插入 '}'
            self.insertPlainText("}")
            # 将光标移回括号中间
            cursor.movePosition(QTextCursor.MoveOperation.Left)
            self.setTextCursor(cursor)
            return
        # <--- 5. 处理补全相关的按键 ---
        if self.completer.popup().isVisible():
            key = event.key()
            
            if key in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Tab, Qt.Key.Key_Right):
                # 如果用户按 Enter, Tab 或右箭头, 接受当前选中的补全项
                event.accept()
                self.completer.activated.emit(self.completer.currentCompletion())
                return

            elif key == Qt.Key.Key_Escape:
                # 如果按 Escape, 关闭补全窗口
                event.accept()
                self.completer.popup().hide()
                return
            elif key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
                 # 将上下移动事件传递给补全窗口
                self.completer.popup().keyPressEvent(event)
                return

        # --- 原有的按键处理逻辑 ---
        if event.key() == Qt.Key.Key_Escape and self.find_panel.isVisible():
            self.find_panel.hide()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            current_line = cursor.block().text()
            leading_spaces = len(current_line) - len(current_line.lstrip(' '))
            current_indent = ' ' * leading_spaces
            
            # 智能缩进：如果在大括号内换行，则增加缩进
            if current_line.strip().endswith('{') and self.toPlainText()[cursor.position()] == '}':
                 self.insertPlainText('\n' + current_indent + ' ' * self.INDENT_WIDTH + '\n' + current_indent)
                 cursor.movePosition(QTextCursor.MoveOperation.Up)
                 cursor.movePosition(QTextCursor.MoveOperation.EndOfLine)
                 self.setTextCursor(cursor)
            else:
                 self.insertPlainText('\n' + current_indent)
            return
        if event.key() == Qt.Key.Key_Tab:
            self.insertPlainText(' ' * self.INDENT_WIDTH)
            return

        # 将其他所有按键事件交由父类处理，这样用户才能正常输入
        super().keyPressEvent(event)

        # 在父类处理后，再次检查是否需要更新或显示补全
        prefix = self._text_under_cursor()
        if prefix:
             self.completer.setCompletionPrefix(prefix)
             if self.completer.popup().isVisible(): # if it's already visible, refresh it
                 self.completer.complete(self.cursorRect())
    def jump_to_line(self, line_number: int):
        """将光标和视图移动到指定的行号。"""
        cursor = self.textCursor()
        # QTextCursor.movePosition 的 blockNumber 从0开始，所以要-1
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(cursor.MoveOperation.NextBlock,
                            cursor.MoveMode.MoveAnchor,
                            line_number - 1)
        self.setTextCursor(cursor)
        self.setFocus()
    def _find_next(self, text):
        if not text: return
        if not self.find(text):
            self.moveCursor(QTextCursor.MoveOperation.Start)
            self.find(text)
        self._update_search_count(text)

    def _find_previous(self, text):
        if not text: return
        flags = QTextDocument.FindFlag.FindBackward
        if not self.find(text, flags):
            self.moveCursor(QTextCursor.MoveOperation.End)
            self.find(text, flags)
        self._update_search_count(text)
    
    def _update_search_count(self, text):
        """计算并更新匹配数。"""
        if not text:
            self.find_panel.update_match_count(0, 0)
            return

        # 统计总数
        doc = self.document()
        cursor = QTextCursor(doc)
        count = 0
        while not (cursor := doc.find(text, cursor)).isNull():
            count += 1
        
        # 统计当前是第几个
        current_match = 0
        cursor = self.textCursor() # 获取当前光标
        # 向后搜索，计算光标前有多少个匹配项
        temp_cursor = QTextCursor(doc)
        while not (temp_cursor := doc.find(text, temp_cursor)).isNull():
            if temp_cursor.anchor() < cursor.anchor():
                current_match += 1
            else:
                break
        
        self.find_panel.update_match_count(current_match + 1 if count > 0 else 0, count)
    def lineNumberAreaWidth(self) -> int:
        """计算行号栏应该有的宽度。"""
        digits = 1
        max_count = max(1, self.blockCount())
        while max_count >= 10:
            max_count /= 10
            digits += 1
        
        # 根据数字位数计算宽度，并增加一些边距
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits + 3
        return space

    def updateAuxiliaryAreasWidth(self, _=None):
        """更新辅助区域（行号栏与小地图）的宽度，并调整编辑器内容区域的边距。"""
        right_margin = self.minimapWidth() if self._minimap_enabled else 0
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, right_margin, 0)

    def updateLineNumberArea(self, rect: QRect, dy: int):
        """当编辑器滚动时，同步滚动行号栏。"""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateAuxiliaryAreasWidth(0)

    def _on_update_request(self, rect: QRect, dy: int):
        # 同步行号栏
        self.updateLineNumberArea(rect, dy)
        # 同步小地图
        if self._minimap_enabled and self.minimap_area:
            if dy:
                self.minimap_area.scroll(0, 0)  # 小地图整体按比例绘制，不做像素滚动
            else:
                self.minimap_area.update(0, rect.y(), self.minimap_area.width(), rect.height())
    def lineNumberAreaPaintEvent(self, event: QPaintEvent):
        """由 LineNumberArea 调用，实际执行绘制操作。"""
        painter = QPainter(self.line_number_area)
        # 用编辑器的背景色填充行号栏
        painter.fillRect(event.rect(), QColor("#2b2b2b"))
        
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        # 遍历所有可见的文本块（行）
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                # 为当前行设置不同的颜色
                if self.textCursor().blockNumber() == block_number:
                    painter.setPen(QColor("#f8f8f2")) # 当前行，亮白色
                else:
                    painter.setPen(QColor("#75715e")) # 其他行，暗灰色
                
                painter.drawText(0, int(top), self.line_number_area.width() - 3,
                                 self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)
            
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1
    def highlightCurrentLine(self):
        """
        高亮编辑器中的当前行，并安全地触发一次行号栏的重绘。
        """
        # 1. 暂时阻塞信号，防止 setExtraSelections 触发 textChanged
        self.blockSignals(True)
        
        try:
            extra_selections = []
            selection = QTextEdit.ExtraSelection()
            line_color = QColor("#3E3D32")
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
            self.setExtraSelections(extra_selections)
        finally:
            # 2. 确保信号总是会被恢复
            self.blockSignals(False)

        
        # 触发一次行号栏的重绘，以更新数字的颜色
        self.line_number_area.update()
        if self._minimap_enabled and self.minimap_area:
            self.minimap_area.update()

    # ---------------------------------------------------------------
    # 公开 API：动态调整编辑器字体/字号
    # ---------------------------------------------------------------
    def apply_editor_font(self, family: str | None = None, point_size: int | None = None):
        """
        动态应用编辑器字体设置。
        - family: 字体族名；None 表示保持不变
        - point_size: 字号；None 表示保持不变
        自动调整制表符宽度与行号栏。
        """
        f = QFont(self.font())
        if family:
            f.setFamily(family)
        if point_size:
            f.setPointSize(point_size)
        self.setFont(f)
        try:
            space_width = self.fontMetrics().horizontalAdvance(' ')
            self.setTabStopDistance(space_width * self.INDENT_WIDTH)
        except Exception:
            pass
        # 刷新与字体相关的区域
        self.updateAuxiliaryAreasWidth(0)
        self.line_number_area.update()
        if self._minimap_enabled and self.minimap_area:
            self.minimap_area.update()

    # ---------------------------------------------------------------
    # 小地图绘制与交互
    # ---------------------------------------------------------------
    def minimapWidth(self) -> int:
        return self._minimap_width

    def minimapPaintEvent(self, event: QPaintEvent):
        """绘制改进版小地图：
        - 背景使用渐变与淡淡的网格感
        - 每行显示代码密度条（基于非空字符数）
        - 大文件下进行抽样避免性能问题
        - 当前视口范围高亮 + 当前行指示线
        """
        painter = QPainter(self.minimap_area)
        rect = event.rect()
        w = rect.width()
        h = rect.height()

        # 背景渐变
        # QLinearGradient 需要 QPointF 或数值，而 QRect 返回的是 QPoint
        # 明确转换为浮点坐标避免类型错误
        top_left = rect.topLeft()
        bottom_left = rect.bottomLeft()
        gradient = QLinearGradient(float(top_left.x()), float(top_left.y()), float(bottom_left.x()), float(bottom_left.y()))
        gradient.setColorAt(0.0, QColor("#202020"))
        gradient.setColorAt(1.0, QColor("#262626"))
        painter.fillRect(rect, gradient)

        total_blocks = max(1, self.blockCount())

        # 如果行数太多，抽样（压缩到最多 150 条渲染）
        max_render = 150
        step = max(1, total_blocks // max_render)

        # 统计最大行“密度”用于归一化
        # 简单度量：去除空白后的字符数
        max_density = 1
        for i in range(0, total_blocks, step):
            block = self.document().findBlockByNumber(i)
            text = block.text().rstrip()
            # 使用非空白字符数作为密度
            d = len(re.sub(r"\s+", "", text))
            if d > max_density:
                max_density = d

        # 绘制“缩略图”：将每行文本压缩为若干列的小块，模拟微缩文字
        bar_left = 2
        bar_width = max(1, w - 4)

        def char_intensity(ch: str) -> float:
            if ch.isspace():
                return 0.0
            if ch.isalpha():
                return 0.85 if ch.isupper() else 0.75
            if ch.isdigit():
                return 0.7
            # 括号、花括号、分号等给更高对比
            if ch in '(){}[];:,._':
                return 0.9
            # 其他符号
            return 0.6

        # 每行最多渲染的列数，避免过宽影响性能
        max_cols = min(96, bar_width)

        for i in range(0, total_blocks, step):
            block = self.document().findBlockByNumber(i)
            text = block.text().rstrip('\n')

            # 行在小地图中的纵向区间（按比例映射）
            y1 = int(i * h / total_blocks)
            y2 = int((i + step) * h / total_blocks)
            bh = max(1, y2 - y1)

            if not text:
                # 空行用很淡的底色
                painter.fillRect(bar_left, y1, bar_width, bh, QColor("#2d2d2d"))
                continue

            # 将该行压缩成若干列
            cols = max(1, max_cols)
            cw = max(1, int(bar_width / cols))
            # 计算抽样步长：将行字符平均映射到列
            stride = max(1, int(len(text) / cols))

            # 简单的“注释行”与“字符串”检测，用不同色调
            is_comment = text.strip().startswith('//')
            in_string = '"' in text

            for c in range(cols):
                idx = c * stride
                if idx >= len(text):
                    break
                ch = text[idx]
                inten = char_intensity(ch)
                # 基于整行总体密度微调强度
                line_density = len(re.sub(r"\s+", "", text)) / max_density
                inten = min(1.0, 0.4 * inten + 0.6 * line_density)

                # 着色：普通为灰度，注释偏绿，字符串偏黄
                if is_comment:
                    base = QColor(95, 174, 95)  # 绿
                elif in_string:
                    base = QColor(210, 190, 90)  # 黄
                else:
                    base = QColor(120, 120, 120) # 灰

                r = int(base.red() * inten)
                g = int(base.green() * inten)
                b = int(base.blue() * inten)
                color = QColor(max(35, r), max(35, g), max(35, b))

                x = bar_left + c * cw
                painter.fillRect(x, y1, cw, bh, color)

        # 视口高亮框：基于实际像素高度累加更精确
        first_block = self.firstVisibleBlock()
        first_block_number = first_block.blockNumber()
        visible_px = self.viewport().height()
        acc_px = 0.0
        block = first_block
        visible_blocks = 0
        while block.isValid() and acc_px < visible_px:
            acc_px += self.blockBoundingRect(block).height()
            visible_blocks += 1
            block = block.next()
        # 比例位置
        y_top = int(first_block_number * h / total_blocks)
        y_bottom = int((first_block_number + max(1, visible_blocks)) * h / total_blocks)
        view_h = max(3, y_bottom - y_top)
        overlay = QColor("#4ec9b0")
        overlay.setAlpha(80)
        painter.fillRect(0, y_top, w, view_h, overlay)

        # 当前行指示线
        current_line = self.textCursor().blockNumber()
        y_line = int(current_line * h / total_blocks)
        pen = QPen(QColor("#ffcc00"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(0, y_line, w, y_line)

        # 外边框
        painter.setPen(QColor("#3a3a3a"))
        painter.drawRect(rect.adjusted(0, 0, -1, -1))

    def minimapMouseEvent(self, event):
        """点击 / 拖动小地图时跳转。使用累积高度寻找目标行，适配不同块高度。"""
        if not self._minimap_enabled:
            return
        y_clicked = event.position().toPoint().y()
        h = max(1, self.minimap_area.height())
        total_blocks = max(1, self.blockCount())
        # 目标比例
        ratio = min(1.0, max(0.0, y_clicked / h))
        target_index = int(ratio * (total_blocks - 1))

        # 使用累积方式微调：在长行高度差异较大时更准确
        # 简化：直接跳转到 target_index，对性能友好
        self.jump_to_line(target_index + 1)

    def set_minimap_enabled(self, enabled: bool):
        self._minimap_enabled = bool(enabled)
        if self._minimap_enabled:
            if self.minimap_area is None:
                self.minimap_area = MinimapArea(self)
            self.minimap_area.show()
        else:
            if self.minimap_area:
                self.minimap_area.hide()
        self.updateAuxiliaryAreasWidth(0)
        self.update()

    def set_minimap_width(self, width_px: int):
        width_px = int(max(16, min(400, width_px)))
        self._minimap_width = width_px
        self.updateAuxiliaryAreasWidth(0)
        if self.minimap_area:
            self.minimap_area.update()
    