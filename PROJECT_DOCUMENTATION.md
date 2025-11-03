# 东方Project ANM & MSG 脚本编辑器 - 项目文档

## 项目概览

这是一个功能完善的东方Project ANM (动画) 和 MSG (对话) 脚本编辑器，基于PyQt6框架开发。该编辑器为这两种脚本类型提供了代码高亮、实时预览（ANM精灵）、语法检查、快速跳转等丰富功能，并集成了 `thanm` 和 `thmsg` 等配套工具进行文件的打包和解包操作。

## 项目审阅与总结

本项目是一个设计精良、功能完备的领域特定语言（DSL）编辑器，专为东方Project的 ANM 和 MSG 脚本设计。其架构清晰，功能深入，用户体验流畅，是PyQt桌面应用开发的优秀范例。

**核心优势:**
- **优秀的架构设计**: 采用“处理器驱动”的策略模式，将不同脚本（ANM, MSG, ECL等）的逻辑完全解耦，具有极高的可扩展性和可维护性。
- **专业级编辑器体验**: 针对不同脚本类型，通过动态语法高亮、上下文感知代码补全、实时括号匹配、悬停帮助提示等功能，提供了媲美专业IDE的编辑体验。
- **深度集成工作流**: 无缝集成了`thanm`和`thmsg`工具，将脚本的解包、编辑、预览、打包流程融为一体，形成了高效的工作闭环。
- **注重性能优化**: 运用了延迟解析（debounce）、图像缓存（ANM）等关键技术，确保了在处理复杂脚本和大量资源时依然保持流畅的响应。

该项目不仅是一个实用的多功能工具，更是一个值得学习的、包含了现代GUI应用开发诸多最佳实践的案例。

**主要特性：**
- 🎨 针对 ANM 和 MSG 的专业语法高亮和代码补全
- 🖼️ ANM 脚本的实时精灵图集预览
- 🔍 智能查找和快速跳转功能
- 📦 集成 `thanm` 和 `thmsg` 工具进行文件打包/解包
- 💡 指令帮助提示和文档显示
- 🎯 括号匹配检查和错误提示
- 🔄 可扩展的处理器架构，轻松支持新脚本类型

---

## 项目结构

```
THTK-STUDIO/
├── main.py                      # 应用程序入口
├── README.md                    # 项目简介与快速入门
├── PROJECT_DOCUMENTATION.md     # 详细项目技术文档
├── requirements.txt             # Python依赖项
├── app/                         # 应用程序主模块
│   ├── main_window.py          # 主窗口类
│   ├── core/                   # 核心功能模块
│   ├── handlers/               # 脚本类型处理器
│   └── widgets/                # 自定义UI组件
├── resources/                   # 资源文件 (配置文件, anmm等)
└── data/                        # 测试数据和示例文件
```

---

## 核心模块详解

### 1. 入口文件

#### `main.py`
- **功能**：应用程序启动入口
- **职责**：
  - 创建QApplication实例
  - 初始化主窗口
  - 启动事件循环
- **关键代码**：
```python
app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())
```

---

### 2. 主窗口模块

#### `app/main_window.py`
- **类名**：`MainWindow`
- **继承**：`QMainWindow`
- **功能**：编辑器的核心窗口，采用**处理器驱动架构**
- **核心设计理念**：
  - 使用`ScriptHandler`接口实现多脚本类型支持
  - 通过处理器映射根据文件扩展名自动切换处理器
  - 统一的文件操作和UI管理

- **主要组件**：
  - `text_editor`: 中央文本编辑器
  - `help_panel`: 帮助文档面板（右侧停靠）
  - `script_handlers`: 脚本处理器字典
  - `current_handler`: 当前激活的处理器

- **关键方法**：
  - `open_file()`: 打开文件并自动切换处理器
  - `switch_handler()`: 切换脚本处理器
  - `save_file()` / `save_file_as()`: 文件保存
  - `on_text_changed()`: 文本变化时触发处理器更新
  - `refresh_handler_view()`: 手动刷新视图

- **信号连接**：
  - `text_editor.syntax_status_changed` → `_update_syntax_status`
  - `text_editor.word_under_cursor_changed` → `_on_word_under_cursor`
  - `text_editor.document().modificationChanged` → `_on_modification_changed`

---

### 3. 核心功能模块 (`app/core/`)

#### 3.1 `parser.py` - ANM脚本解析器
- **类名**：`ScriptParser`
- **功能**：解析ANM脚本文本，提取结构化数据
- **解析内容**：
  - Entry块（纹理图集定义）
  - Script块（脚本定义）
  - Sprite定义（精灵坐标和尺寸）
  
- **核心方法**：
  - `parse(text: str) -> Dict`: 解析完整脚本
  - `get_all_sprite_locations(text: str) -> Dict[str, int]`: 获取所有精灵定义的行号

- **解析策略**：
  - 使用正则表达式分割策略
  - 贪婪匹配处理嵌套括号
  - 容错处理避免解析失败

- **返回数据结构**：
```python
{
    "entries": {
        "entry0": {
            "line": 1,
            "image_path": "pl00/pl00.png",
            "sprites": {
                "sprite0": {"x": 1, "y": 1, "w": 30, "h": 46},
                ...
            }
        }
    },
    "scripts": {
        "main": {"line": 100}
    }
}
```

#### 3.2 `image_manager.py` - 图像管理器
- **类名**：`ImageManager`
- **功能**：管理精灵图集的加载、缓存和裁剪
- **优化特性**：
  - 内存缓存机制，避免重复加载
  - 支持相对路径解析
  - 错误处理和容错

- **主要方法**：
  - `set_base_path(path: str)`: 设置基准路径
  - `load_spritesheet(path: str) -> PILImage`: 加载图集
  - `get_sprite_image(path: str, rect: Dict) -> PILImage`: 裁剪精灵
  - `clear_cache()`: 清空缓存

- **使用流程**：
```python
manager = ImageManager(base_path="/path/to/project")
sprite = manager.get_sprite_image("pl00/pl00.png", {"x": 1, "y": 1, "w": 30, "h": 46})
```

#### 3.3 `script_handler.py` - 脚本处理器基类
- **类名**：`ScriptHandler` (抽象基类)
- **设计模式**：策略模式 + 工厂模式
- **功能**：定义脚本处理器接口
- **必须实现的方法**：
  - `get_name() -> str`: 返回处理器名称
  - `get_file_filter() -> str`: 返回文件过滤器
  - `create_highlighter()`: 创建语法高亮器
  - `create_parser()`: 创建解析器
  - `create_tool_wrapper()`: 创建工具封装
  - `setup_ui()`: 设置UI
  - `clear_ui()`: 清理UI
  - `connect_signals()`: 连接信号
  - `update_views()`: 更新视图

#### 3.4 `settings.py` - 设置管理器
- **类名**：`Settings`
- **功能**：管理应用程序配置和路径设置
- **存储内容**：
  - `user_thanm_path`: 用户指定的thanm.exe路径
  - `user_anmm_path`: 用户指定的ANMM映射文件路径

- **智能路径解析**：
  - 优先使用用户设置路径
  - 自动查找内置资源路径
  - 兼容开发环境和打包环境

- **主要方法**：
  - `load()` / `save()`: 加载/保存设置
  - `get_thanm_path()`: 获取thanm路径（智能回退）
  - `get_anmm_path()`: 获取anmm路径（智能回退）
  - `set_user_path(key, value)`: 设置用户路径

#### 3.5 `thanm_wrapper.py` - Thanm工具封装
- **类名**：`ThanmWrapper`
- **功能**：封装thanm.exe命令行工具的调用
- **支持操作**：
  - 解包ANM文件（提取图片和脚本）
  - 打包ANM文件（从脚本生成ANM）
  - 结构分析

- **主要方法**：
  - `unpack_all(version, anm_path, output_dir)`: 完整解包流程
  - `extract_images(version, anm_path, working_dir)`: 提取图片
  - `analyze_structure(version, anm_path, output_path)`: 提取脚本
  - `create(version, output_archive, spec_file)`: 打包ANM

- **错误处理**：
  - 自定义`ThanmError`异常
  - 捕获stderr输出
  - 详细的错误信息反馈

---

### 4. 脚本处理器模块 (`app/handlers/`)

#### 4.1 `anm_handler.py` - ANM脚本处理器
- **类名**：`AnmScriptHandler`
- **继承**：`ScriptHandler`
- **功能**：ANM脚本的完整处理逻辑
- **管理的UI组件**：
  - `preview_pane`: 精灵预览面板（右侧）
  - `thanm_panel`: thanm工具面板（左侧停靠）
  - `jump_combo`: 快速跳转下拉框（工具栏）
  - `central_splitter`: 分割器（编辑器+预览面板）

- **核心工作流**：
  1. **文本变化** → `update_views()` 被调用
  2. **解析脚本** → 使用`ScriptParser`
  3. **加载图像** → 使用`ImageManager`
  4. **更新预览** → `_update_sprite_previews()`
  5. **更新跳转框** → `_update_jump_combo()`

- **关键方法**：
  - `setup_ui()`: 创建ANM专用UI（预览面板、工具面板等）
  - `clear_ui()`: 销毁所有创建的UI组件
  - `update_views()`: 解析文本并更新所有视图
  - `_update_sprite_previews()`: 更新精灵预览
  - `_update_jump_combo()`: 更新快速跳转下拉框
  - `on_unpack_request()`: 处理解包请求
  - `on_pack_request()`: 处理打包请求
  - `_jump_to_sprite_definition()`: 跳转到精灵定义
  - `_jump_to_block()`: 跳转到entry/script

---

### 5. UI组件模块 (`app/widgets/`)

#### 5.1 `text_editor.py` - 文本编辑器
- **类名**：`TextEditor`
- **继承**：`QPlainTextEdit`
- **功能**：增强的代码编辑器，提供专业IDE体验
- **核心特性**：
  
  **1. 语法高亮**
  - 通过`AnmSyntaxHighlighter`实现
  - 动态规则更新（精灵名、标签名）
  
  **2. 代码补全**
  - 使用`QCompleter`实现
  - 补全源：指令、精灵名、标签名
  - 触发条件：输入2个字符且在行尾
  - 智能补全窗口：醒目样式、加粗字体
  
  **3. 括号匹配检查**
  - 实时检查大括号配对
  - 红色波浪线标记错误
  - 状态栏显示错误数量
  
  **4. 智能缩进**
  - 自动保持当前缩进
  - 大括号后自动增加缩进
  - Tab键插入4个空格
  
  **5. 查找功能**
  - 集成`SearchPanel`
  - 支持下一个/上一个
  - 显示匹配计数
  - 快捷键：Ctrl+F
  
  **6. 帮助提示**
  - 鼠标悬停显示指令文档
  - 光标位置改变时更新帮助面板
  - 粗体醒目字体

- **性能优化**：
  - 使用`QTimer`延迟分析（500ms）
  - 轻量级文本变化处理
  - 重量级分析只在停止输入后执行

- **主要方法**：
  - `update_full_analysis()`: 执行完整的语法分析
  - `_update_completion_model()`: 更新补全模型
  - `_text_under_cursor()`: 获取光标下的单词
  - `_insert_completion()`: 插入补全项
  - `show_find_panel()`: 显示查找面板
  - `jump_to_line(line_number)`: 跳转到指定行
  - `_check_brackets()`: 检查括号匹配
  - `_highlight_errors()`: 高亮错误位置

- **信号**：
  - `syntax_status_changed(bool, str)`: 语法状态变化
  - `word_under_cursor_changed(str)`: 光标下单词变化

- **样式特性**：
  - 编辑器字体：Consolas 12pt DemiBold
  - 补全窗口：Segoe UI Semibold 11pt Bold
  - 工具提示：Segoe UI 10pt Bold
  - 深色主题配色

#### 5.2 `syntax_highlighter.py` - 语法高亮器
- **类名**：`AnmSyntaxHighlighter`
- **继承**：`QSyntaxHighlighter`
- **功能**：ANM脚本的语法着色
- **高亮规则**：
  - **关键字**（粉色、粗体）：`entry`, `script`, `sprites`等
  - **属性**（青色）：`version`, `name`, `width`等
  - **指令**（绿色）：从`instructions.json`加载
  - **变量**（紫色）：从`variables.json`加载，支持%和$前缀
  - **精灵定义**（紫色、粗体）：`sprite sprite_name`
  - **精灵使用**（橙色）：动态识别已定义的精灵
  - **标签**（粉色）：行首的`label:`格式
  - **字符串**（黄色）：双引号内容
  - **数字**（紫色）：整数、浮点数、科学计数法
  - **注释**（灰色、斜体）：`//`开头的行

- **动态规则**：
  - `update_dynamic_rules(full_text)`: 扫描全文提取精灵名和标签名
  - 实时更新精灵引用高亮
  - 自动触发重新高亮

- **文档加载**：
  - `instruction_docs`: 指令帮助文档映射
  - `variable_docs`: 变量帮助文档映射
  - 支持HTML格式文档

#### 5.3 `sprite_preview.py` - 精灵预览面板
- **类名**：`SpritePreviewPane`
- **继承**：`QScrollArea`
- **功能**：以网格形式显示所有精灵
- **UI结构**：
  - 使用`QStackedWidget`切换占位符和预览内容
  - 使用`FlowLayout`实现自动换行网格布局
  - 深色主题背景（#222222）
  - 自定义滚动条样式

- **主要方法**：
  - `add_sprite_preview(widget)`: 添加精灵项
  - `clear_previews()`: 清空所有预览
  - `show_placeholder()`: 显示占位符

#### 5.4 `sprite_preview_item.py` - 精灵预览项
- **类名**：`SpritePreviewItem`
- **继承**：`QWidget`
- **功能**：单个精灵的显示卡片
- **显示内容**：
  - 精灵图像（保持宽高比缩放）
  - 精灵名称（entry/sprite格式）
  - 鼠标悬停高亮效果

- **交互**：
  - 点击发出`clicked(str)`信号
  - 连接到跳转功能

#### 5.5 `help_panel.py` - 帮助面板
- **类名**：`HelpPanel`
- **继承**：`QDockWidget`
- **功能**：显示指令和变量的帮助文档
- **停靠位置**：左侧或右侧
- **内容格式**：支持HTML富文本
- **主要方法**：
  - `update_content(html)`: 更新显示内容
  - `show_default()`: 显示默认提示

#### 5.6 `thanm_panel.py` - Thanm工具面板
- **类名**：`ThanmPanel`
- **继承**：`QDockWidget`
- **功能**：thanm工具的图形化界面
- **UI组件**：
  - **路径设置**：
    - Thanm.exe路径输入框
    - ANMM映射文件路径输入框
    - 浏览按钮（标准文件夹图标）
  - **游戏版本选择**：
    - 下拉框支持th12-th19
    - 版本号映射
  - **操作按钮**：
    - "解包ANM并编辑..."
    - "打包当前脚本..."

- **信号**：
  - `unpack_requested`: 解包请求
  - `pack_requested`: 打包请求
  - `thanm_path_changed(str)`: 路径变化
  - `anmm_path_changed(str)`: ANMM路径变化

- **样式特性**：
  - 深色主题
  - 圆角边框
  - 悬停效果

#### 5.7 `search_panel.py` - 查找面板
- **类名**：`SearchPanel`
- **继承**：`QWidget`
- **功能**：文本查找界面
- **UI组件**：
  - 搜索输入框
  - 上一个/下一个按钮
  - 匹配计数显示
  - 关闭按钮

- **信号**：
  - `find_next(str)`: 查找下一个
  - `find_previous(str)`: 查找上一个
  - `search_text_changed(str)`: 搜索文本变化
  - `closed`: 关闭面板

- **特性**：
  - 浮动在编辑器右上角
  - Esc键关闭
  - 实时更新匹配计数

#### 5.8 `flow_layout.py` - 流式布局
- **类名**：`FlowLayout`
- **继承**：`QLayout`
- **功能**：自动换行的网格布局
- **用途**：精灵预览的自适应布局
- **特性**：
  - 根据容器宽度自动换行
  - 支持间距和边距设置
  - 智能计算子项位置

---

### `requirements.txt`
标准的Python依赖文件，用于通过`pip install -r requirements.txt`快速安装所有必需的第三方库。
```
PyQt6
Pillow
```

### `resources/` 目录
此目录用于存放应用的静态资源。
- `instructions.json`: 存储ANM指令的名称和描述。
- `variables.json`: 存储ANM内置变量的名称和描述。
- `syntax_definitions.json`: 定义语法高亮中的关键字和属性。
- `default.anmm`: 默认的ANMM映射文件，用于`thanm`工具。
- `settings.json`: 存储用户配置，如`thanm.exe`的路径。

---

## 工作流程

### 1. 应用启动流程
```
main.py
  → 创建 QApplication
  → 创建 MainWindow
    → 加载 Settings
    → 创建 AnmScriptHandler
    → 初始化 UI 组件
      → TextEditor
      → HelpPanel
    → 设置信号连接
    → 激活默认处理器（ANM）
      → setup_ui()
        → 创建 SpritePreviewPane
        → 创建 ThanmPanel
        → 创建 快速跳转ComboBox
      → connect_signals()
  → 显示窗口
  → 启动事件循环
```

### 2. 文件打开流程
```
用户点击"打开"
  → open_file()
    → QFileDialog 选择文件
    → 根据扩展名查找处理器
    → 切换处理器（如需要）
      → 旧处理器 clear_ui()
      → 新处理器 setup_ui()
    → 加载文件内容
      → setPlainText()
        → 触发 textChanged 信号
          → on_text_changed_lightweight()
            → 启动 500ms 定时器
              → update_full_analysis()
                → 更新动态规则
                → 更新补全模型
                → 检查括号
                → 触发补全（如需要）
          → on_text_changed() (MainWindow)
            → current_handler.update_views()
              → 解析脚本
              → 更新精灵预览
              → 更新跳转下拉框
```

### 3. 编辑流程
```
用户输入文本
  → keyPressEvent()
    → 处理补全按键（Enter/Tab/Esc）
    → 处理缩进（Tab/Enter）
    → 默认处理（字符输入）
  → textChanged 信号
    → on_text_changed_lightweight()
      → 重置定时器（500ms）
    (用户继续输入时定时器被重置)
    (用户停止输入500ms后)
      → update_full_analysis()
        → 语法分析
        → 补全触发
    → on_text_changed() (MainWindow)
      → update_views()
        → 解析和更新视图
```

### 4. ANM解包流程
```
用户点击"解包ANM"
  → on_unpack_request()
    → 检查 thanm 路径
    → QFileDialog 选择 .anm 文件
    → 获取游戏版本
    → ThanmWrapper.unpack_all()
      → extract_images()
        → 调用 thanm -x
        → 提取PNG图片
      → analyze_structure()
        → 调用 thanm -l
        → 生成 .txt 脚本
    → 自动加载生成的 .txt 文件
      → _load_file_content()
        → 触发解析和预览更新
```

### 5. ANM打包流程
```
用户点击"打包当前脚本"
  → on_pack_request()
    → 检查当前文件是否打开
    → 检查 thanm 路径
    → 获取游戏版本
    → QFileDialog 选择输出 .anm 路径
    → ThanmWrapper.create()
      → 调用 thanm -c
      → 从 .txt 和图片生成 .anm
    → 显示成功消息
```

---

## 技术特点

### 1. 架构设计
- **处理器驱动架构**：通过`ScriptHandler`接口实现可扩展的多脚本类型支持
- **MVC模式**：清晰的模型-视图-控制器分离
- **信号-槽机制**：松耦合的组件通信
- **策略模式**：不同脚本类型使用不同的处理策略

### 2. 性能优化
- **图像缓存**：`ImageManager`避免重复加载
- **延迟分析**：500ms定时器避免频繁解析
- **增量更新**：只在必要时刷新视图
- **异步处理**：长时间操作使用QTimer分散

### 3. 用户体验
- **智能补全**：上下文感知的代码补全
- **实时预览**：所见即所得的精灵显示
- **快速跳转**：一键跳转到定义位置
- **错误提示**：直观的波浪线和状态栏提示
- **键盘快捷键**：Ctrl+S保存、Ctrl+F查找等

### 4. 代码质量
- **类型注解**：使用Python类型提示
- **文档字符串**：详细的方法说明
- **错误处理**：完善的异常捕获和用户反馈
- **代码注释**：关键逻辑都有中文注释

### 5. 可扩展性
- **插件化处理器**：轻松添加新的脚本类型
- **配置化语法**：JSON文件定义语法规则
- **主题可定制**：QSS样式表自定义外观
- **工具封装**：抽象的工具包装器接口

---

## 依赖项

### Python标准库
- `sys`, `os`, `pathlib`: 系统和路径操作
- `json`: 配置文件读写
- `re`: 正则表达式解析
- `subprocess`: 外部工具调用
- `typing`: 类型注解

### 第三方库
- **PyQt6** (6.x): GUI框架
  - `QtWidgets`: UI组件
  - `QtCore`: 核心功能（信号、定时器等）
  - `QtGui`: 图形元素（字体、颜色等）
- **Pillow** (PIL): 图像处理
  - 图像加载
  - 图像裁剪
  - 格式转换

### 外部工具
- **thanm.exe**: 东方Project ANM文件处理工具
  - 版本：支持th12-th19
  - 功能：解包、打包、结构分析

---

## 运行要求

### 环境要求
- Python 3.10+
- Windows 10/11（主要测试平台）
- 8GB+ RAM推荐（处理大型ANM文件）

### 安装步骤
```bash
# 1. 克隆或下载项目
git clone https://github.com/your-username/your-repo.git
cd your-repo

# 2. 安装依赖
# 推荐在虚拟环境中操作
pip install -r requirements.txt

# 3. 准备thanm.exe (可选)
# 将thanm.exe放入resources/目录，或在程序UI中指定路径

# 4. 运行程序
python main.py
```

### 文件夹结构要求
```
项目根目录/
├── main.py
├── requirements.txt        # 必需
├── resources/
│   ├── instructions.json       # 必需
│   ├── variables.json          # 必需
│   ├── syntax_definitions.json # 必需
│   ├── thanm.exe          # 可选（可在UI中指定）
│   └── default.anmm       # 可选
└── app/                   # 必需
```

---

## 扩展指南

### 添加新的脚本类型

1. **创建解析器** (`app/core/xxx_parser.py`)
```python
class XxxParser:
    def parse(self, text: str) -> Dict:
        # 解析逻辑
        pass
```

2. **创建语法高亮器** (`app/widgets/xxx_syntax_highlighter.py`)
```python
class XxxSyntaxHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text: str):
        # 高亮逻辑
        pass
```

3. **创建处理器** (`app/handlers/xxx_handler.py`)
```python
class XxxScriptHandler(ScriptHandler):
    def get_name(self) -> str:
        return "XXX"
    
    def setup_ui(self, main_window):
        # 创建专用UI
        pass
    
    # 实现其他抽象方法...
```

4. **注册处理器** (在`main_window.py`)
```python
xxx_handler = XxxScriptHandler()
self.script_handlers["XXX"] = xxx_handler
self.handler_file_map[".xxx"] = xxx_handler
```

### 添加新的指令

编辑`instructions.json`：
```json
{
    "新指令ID": {
        "name": "指令名称(参数1, 参数2)",
        "description": "详细描述"
    }
}
```

### 自定义主题

修改各组件的`setStyleSheet()`调用，使用QSS语法：
```python
self.setStyleSheet("""
    QWidget {
        background-color: #your_color;
        color: #text_color;
    }
""")
```

---

## 已知问题和改进方向

### 当前限制
1. ECL脚本支持尚未完全实现
2. 大文件（>10MB）可能导致UI卡顿
3. 仅支持Windows平台的thanm.exe
4. 暂不支持语法错误的详细诊断

### 未来改进
1. **性能优化**
   - 虚拟滚动加载大量精灵
   - 后台线程解析大文件
   - 增量解析优化

2. **功能增强**
   - 代码折叠
   - 多标签页编辑
   - Git集成
   - 项目管理器
   - 精灵动画预览

3. **用户体验**
   - 深色/浅色主题切换
   - 自定义快捷键
   - 撤销/重做历史面板
   - 智能错误修复建议

4. **跨平台支持**
   - 封装thanm为跨平台库
   - macOS和Linux版本

---

## 开发团队与维护

### 代码风格
- 遵循PEP 8规范
- 使用4空格缩进
- 中文注释（面向中文用户）
- 类型注解（提高代码可读性）

### 贡献指南
1. Fork项目
2. 创建功能分支
3. 提交详细的commit信息
4. 通过测试
5. 提交Pull Request

### 许可证
本项目为个人学习项目，基于东方Project二次创作规范。

---

## 常见问题 (FAQ)

**Q: 为什么打开文件后没有精灵预览？**
A: 检查：
1. 图片文件路径是否正确（相对于脚本文件）
2. 图片文件是否存在
3. sprites定义是否正确（x, y, w, h）

**Q: thanm解包失败怎么办？**
A: 检查：
1. thanm.exe路径是否正确
2. 游戏版本是否匹配
3. ANM文件是否损坏
4. 查看错误信息中的stderr输出

**Q: 如何添加自定义指令文档？**
A: 编辑`instructions.json`，添加新条目后重启程序。

**Q: 代码补全不工作？**
A: 确保：
1. 已输入至少2个字符
2. 光标在行尾
3. `instructions.json`已正确加载

**Q: 如何切换到ECL模式？**
A: ECL处理器目前是预留功能，需要完成`ecl_handler.py`的实现。

---

## 总结

这是一个功能完善、架构清晰的东方Project脚本编辑器。通过**处理器驱动架构**实现了良好的可扩展性，通过**组件化设计**实现了代码的高内聚低耦合。项目展示了现代GUI应用开发的最佳实践，包括MVC架构、信号-槽通信、性能优化、用户体验设计等多个方面。

核心亮点：
- ✅ 完整的ANM编辑工作流
- ✅ 专业级代码编辑器体验
- ✅ 直观的可视化预览
- ✅ 可扩展的插件化架构
- ✅ 优雅的UI设计和交互

适合作为：
- PyQt6学习参考项目
- 游戏资源编辑器开发范例
- DSL（领域特定语言）编辑器设计案例
- 代码编辑器功能实现参考

---
 
## 更新说明（2025-11-04）

- ECL 支持完善：
  - 右侧结构大纲 Dock，支持过滤、展开/折叠与双击跳转；基于文本指纹与定时器去抖，避免折叠状态被频繁刷新重置。
  - 处理器切换时清理并销毁大纲 Dock，防止 Dock 堆积。
- 帮助面板升级：顶部新增可编辑下拉框，可直接检索指令名；与高亮器的补全候选同步，悬浮与光标移动会自动刷新说明。
- ECL 文档管线：
  - 通过 Settings 的 `get_ecl_ref_path()` 读取 `resources/thecl_ref.json`（或用户指定路径）。
  - 解析 JSON 的数字键 id → [signature, description]，提取签名中的指令名作为主键，并为每个 id 生成 `ins_<id>` 别名；输出 HTML 为 `<b>signature</b><br>description`。
  - 高亮器实现 `get_documentation(word)` 统一规范化（去除 `@`、尾随冒号、大小写等），主窗口优先调用高亮器进行说明查询。
- 顶部“关于(&A) → 项目整体说明...”弹窗：
  - 新增 `app/widgets/about_dialog.py`，以弹窗（QDialog + QTextBrowser）显示 `resources/project_overview.html`；
  - 从菜单打开，非 Dock 嵌入，便于全局查阅说明；可直接编辑该 HTML 定制内容。
- 其它：
  - MainWindow：改进处理器选择映射（优先匹配文件名，再匹配后缀）；
  - 去抖刷新集中在 `run_handler_update()`，统一完成补全、错误高亮与 rehighlight；
  - README 与本技术文档同步更新，说明依赖文件名为 `requirments.txt`。

---

*文档版本：1.2*  
*最后更新：2025年11月4日*
