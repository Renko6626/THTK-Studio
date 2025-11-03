# THTK-Studio

Touhou-Toolkit的集成式打包/解包和脚本编辑器

一个面向东方 Project 资源的图形化脚本编辑器，基于 PyQt6 开发。支持 ANM / STD / MSG / ECL 多脚本类型，集成了解包/打包、语法高亮、结构大纲、悬浮说明与帮助面板等功能；并提供“关于 → 项目整体说明”的独立弹窗以便快速上手与查阅项目说明。

## 目录
- [更新日志](#-更新日志)
- [主要特性](#-主要特性)
- [快速开始](#-快速开始)
- [使用指南](#-使用指南)
- [自定义与扩展](#-自定义与扩展)
- [目录结构（节选）](#-目录结构节选)
- [详细文档](#-详细文档)
- [未来规划](#-未来规划)
- [联系方式](#-联系方式)
## 更新日志
- 2025-07-xx : 项目原型的前期准备, 用python封装了touhou-toolkit的核心模块功能
- 2025-10-xx : 项目雏形——一个比thtk-gui更好的msg脚本解包和翻译工具。
- 2025-11-04 : 第一个正式版本,引入了内联编辑器和多脚本支持，并封装了thanm/thstd/thmsg/thecl等核心工具的一键打包解包功能。

## ✨ 主要特性

- 多脚本支持：ANM（动画）、STD（3d背景）、MSG（对话）、ECL（弹幕）统一编辑体验，自动按后缀切换处理器
- 语法高亮与补全：按脚本类型加载关键字与指令文档，提供补全与错误高亮（如 STD 分号检查）
- 实时精灵预览（ANM）：在编辑 ANM 文本时预览图集精灵
- 结构大纲（ECL）：右侧 Dock 树状结构，支持过滤、展开/折叠、双击跳转，状态稳定（防重置）
- 帮助面板（右侧）：光标悬停显示指令签名与说明；顶部下拉可直接检索指令名
- 文档管线：支持从 `resources/thecl_ref.json` 加载 ECL 指令说明，兼容 `ins_<id>` 与指令名两种检索
- 一键打包/解包：内置 `thanm`/`thstd`/`thmsg`/`thecl` 封装入口，图形化设置路径与选项
- 关于弹窗：菜单“关于 → 项目整体说明...” 打开完整 HTML 弹窗，便于查阅与定制


## 🚀 快速开始

### 傻瓜体验

如果你连Python环境都懒得配置, 可以去[release](https://github.com/Renko6626/THTK-Studio/releases/tag/THTK-Studio)页面下载exe版本的压缩包

### 环境要求
- Windows 10/11
- Python 3.13

### 安装依赖

使用根目录的依赖文件（注意：文件名为 `requirments.txt`）：

```powershell
pip install -r .\requirments.txt
```

如需手动安装核心依赖，可参考：

```powershell
pip install PyQt6 pillow
```

### 运行

```powershell
python .\main.py
```

程序启动后将进入默认 ANM 处理器，可根据打开的文件类型自动切换。

### 外部工具（可选但推荐）

将 `thanm.exe` / `thstd.exe` / `thmsg.exe` / `thecl.exe` 等放在 `resources/`，或在相应工具面板中手动设置路径。未设置时某些解包/打包功能将不可用，但编辑器与查看器功能仍可使用。


## 🔧 使用指南

1) 打开文件：文件 → 打开…，选择 `.anm.txt` / `.std(.txt)` / `.msg(.txt)` / `.ecl(.txt)` 等，处理器自动切换。

2) 帮助面板：
     - 光标悬停到指令/变量会显示说明与签名。
     - 顶部下拉可输入或选择指令名进行检索。

3) ECL 结构大纲：
     - 右侧 Dock 展示函数与标签的层级结构。
     - 支持过滤、展开/折叠，双击可跳转到相应位置。

4) 关于 → 项目整体说明…：
     - 在菜单栏的“关于(&A)”中，点击“项目整体说明...”，将弹出完整 HTML 对话框。
     - 内容来源：`resources/project_overview.html`，可直接编辑自定义。

5) 打包/解包：
     - 打开对应脚本类型时，左侧（或工具面板区域）会显示该类型的工具入口。
     - 选择游戏版本与路径，点击“解包…”或“打包…”。


## 🧩 自定义与扩展

- 指令说明（ECL）：
    - 文件：`resources/thecl_ref.json`
    - 支持通过签名中的指令名或 `ins_<id>` 两种键检索（如 `wait` 或 `ins_18`）。
- 概览文档：
    - 文件：`resources/project_overview.html`
    - 用于“关于 → 项目整体说明…”弹窗的展示内容，可自由编辑。
- 语法/关键字：
    - 相关定义与变量可在 `resources/` 下的 JSON 文件中扩展。


## 📂 目录结构（节选）

```
├─ main.py
├─ README.md
├─ PROJECT_DOCUMENTATION.md
├─ requirments.txt
├─ app/
│  ├─ main_window.py
│  ├─ core/               # 解析与工具封装（thecl/thstd/thanm/thmsg 等）
│  ├─ handlers/           # 各脚本类型处理器（anm/msg/std/ecl）
│  └─ widgets/            # 编辑器、帮助面板、关于弹窗等 UI 组件
├─ resources/
│  ├─ project_overview.html
│  ├─ thecl_ref.json
│  ├─ thstd_ref.json / thmsg_ref.json / instructions.json ...
│  └─ eclm_files/
└─ data/
```

## � 详细文档

- 更全面的技术说明、架构与扩展指南，请查阅项目根目录的 `PROJECT_DOCUMENTATION.md`。

## 📅 未来规划

- 集成thbgm和thdat模块
- 加入对Thecl1.1版本的eclm支持(它的指令名和一些语法略有区别)
- 加入更智能的代码补全和错误检查系统, 特别是对于函数调用和参数类型的检测
- 加入代码折叠功能, 方便用户管理和浏览大型脚本文件
- 加强文档与帮助系统，提供更全面的使用指南与示例
- 更进一步的可视化编辑器, 比如对动画甚至3D场景的可视化编辑和时间轴功能

## ❓ 常见问题

- 看不到指令帮助？
    - 确认 `resources/thecl_ref.json` 存在或在设置中指定了有效路径。
    - 将光标悬停在指令名或 `ins_<id>` 上，或在帮助面板下拉中直接输入检索。

- 切换编辑器类型后右侧大纲反复刷新/堆积？
    - 已修复：切换处理器时会销毁旧 Dock，避免重复累积；大纲刷新做了去抖处理，避免折叠状态被重置。

- 运行时报 PyQt6 相关的 IDE 告警？
    - 若是代码检查的“无法解析导入”类提示，多为本地环境未安装 PyQt6 所致；按上文安装依赖即可。


## 联系方式

本项目由同人社团[境界景观学会](https://abl.secret-sealing.club) 发起和维护, 并欢迎更多热爱东方 Project 的同好参与开发。

如有问题或建议，请通过以下方式与我们联系：
- 社团qq群: 748966757
- 邮箱：contact@secret-sealing.club
- GitHub： [THTK-Studio](https://github.com/Renko6626/THTK-Studio)

## 🤝 贡献

欢迎提交 Issue / PR 来改进这个项目，包括：新脚本类型支持、语法定义完善、错误修复与 UI 体验优化等。



## 📄 许可与声明

本项目用于东方 Project 相关的二次创作学习与研究，请遵循原作与社区规范。
