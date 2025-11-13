# app/core/thecl_wrapper.py

import subprocess
import os
from pathlib import Path
from typing import List, Optional
from PyQt6.QtWidgets import QMessageBox

class TheclError(Exception):
    """当 thecl 子进程返回错误时抛出此异常。"""
    def __init__(self, message, stderr):
        super().__init__(message)
        self.stderr = stderr

class TheclWrapper:
    """
    一个封装了 thecl.exe 工具的包装类，用于处理东方Project的ECL脚本。
    """
    def __init__(self, thecl_path: str, eclmap_path: Optional[str] = None):
        """
        初始化 TheclWrapper。

        :param thecl_path: thecl.exe 工具的路径。
        :param eclmap_path: (可选) 用于翻译指令的 eclmap 文件路径。
        """
        self.thecl_path = Path(thecl_path)
        if not self.thecl_path.is_file():
            raise FileNotFoundError(f"指定的 thecl 路径 '{self.thecl_path}' 不存在或不是一个文件。")

        self.eclmap_path: Optional[Path] = None
        if eclmap_path:
            self.eclmap_path = Path(eclmap_path)
            if not self.eclmap_path.is_file():
                print(f"警告: 指定的 eclmap 映射文件 '{self.eclmap_path}' 不存在。")
                self.eclmap_path = None

    def _run_command(self, args: List[str]) -> str:
        """
        内部方法，用于执行 thecl 命令并处理结果。
        """
        command = [str(self.thecl_path.absolute())] + args
        print(f"🚀 正在执行命令: {' '.join(command)}")
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
            )
            
            if result.returncode != 0:
                raise TheclError(
                    f"Thecl 命令执行失败 (退出码 {result.returncode})",
                    result.stderr.strip()
                )
            print(result)
            if result.stdout.strip():
                print(f"📋 stdout:\n{result.stdout.strip()}")
            if result.stderr.strip():
                # thecl 可能会在 stderr 输出一些非错误信息；但为防止忽略潜在问题，
                # 即使返回码为 0，也弹出警告提示用户留意这些输出。
                stderr_msg = result.stderr.strip()
                print(f"ℹ️ stderr:\n{stderr_msg}")

                # 粗略识别当前操作类型，给出更友好的提示文案
                op = "操作"
                if '-c' in args:
                    op = "打包"
                elif '-d' in args:
                    op = "解包"
                elif '-h' in args:
                    op = "头文件生成"

                title = "thecl 警告"
                # 结合用户需求给出明确说明
                # 例如：打包成功，但是存在错误/警告（stderr）
                msg = (
                    f"{op}成功，但检测到 thecl 的 stderr 输出，可能存在错误或警告。\n\n"
                    f"提示：{op}成功但是存在错误，这就是：\n\n{stderr_msg}"
                )
                try:
                    QMessageBox.warning(None, title, msg)
                except Exception:
                    # 若在无 GUI 环境下（例如命令行独立运行）无法弹窗，则忽略
                    pass

            return result.stdout
            
        except FileNotFoundError:
            raise FileNotFoundError(f"无法找到 thecl 可执行文件: '{self.thecl_path}'")
        except Exception as e:
            # 捕获更广泛的异常，以防万一
            stderr_info = getattr(e, 'stderr', str(e))
            raise TheclError(f"执行命令时发生未知错误: {e}", stderr_info)

    # ==================================================================
    # 核心公开方法
    # ==================================================================

    def unpack(self, version: str, input_ecl_path: str, output_txt_path: str, 
               use_address_info: bool = False, raw_dump: bool = False) -> str:
        """
        将 .ecl 文件解包 (dump) 为人类可读的 .txt 脚本文件。

        :param version: 游戏版本号 (例如 '12', '18')。
        :param input_ecl_path: 输入的 .ecl 文件路径。
        :param output_txt_path: 输出的 .txt 文件路径。
        :param use_address_info: (可选) 是否添加地址信息 (-x 选项)。
        :param raw_dump: (可选) 是否禁止代码转换，进行原始转储 (-r 选项)。
        :return: 输出文件的路径。
        """
        ecl_path = Path(input_ecl_path).absolute()
        txt_path = Path(output_txt_path).absolute()
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = ['-d', str(version)]
        
        # 默认启用 Shift-JIS <-> UTF-8 转换，对现代编辑器至关重要
        cmd.append('-j')
        
        if self.eclmap_path:
            cmd.extend(['-m', str(self.eclmap_path.absolute())])
            #pass
        if use_address_info:
            cmd.append('-x')
        if raw_dump:
            cmd.append('-r')
            
        cmd.extend([str(ecl_path), str(txt_path)])
        
        self._run_command(cmd)
        print(f"✅ 成功将 '{ecl_path.name}' 解包到 '{txt_path.name}'。")
        return str(txt_path)

    def pack(self, version: str, input_txt_path: str, output_ecl_path: str, 
             simple_mode: bool = False) -> str:
        """
        将 .txt 脚本文件打包 (compile) 回 .ecl 文件。

        :param version: 游戏版本号。
        :param input_txt_path: 输入的 .txt 脚本文件路径。
        :param output_ecl_path: 输出的 .ecl 文件路径。
        :param simple_mode: (可选) 是否启用简单创建模式 (-s 选项)。
        :return: 输出文件的路径。
        """
        txt_path = Path(input_txt_path).absolute()
        ecl_path = Path(output_ecl_path).absolute()
        ecl_path.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = ['-c', str(version)]
        
        # 默认启用 UTF-8 -> Shift-JIS 转换
        cmd.append('-j')

        if self.eclmap_path:
            cmd.extend(['-m', str(self.eclmap_path.absolute())])
        if simple_mode:
            cmd.append('-s')
            
        cmd.extend([str(txt_path), str(ecl_path)])
        
        self._run_command(cmd)
        print(f"✅ 成功将 '{txt_path.name}' 打包到 '{ecl_path.name}'。")
        return str(ecl_path)

    def create_header(self, version: str, input_ecl_path: str, output_header_path: str) -> str:
        """
        为一个 .ecl 文件创建包含子程序声明的头文件。

        :param version: 游戏版本号。
        :param input_ecl_path: 输入的 .ecl 文件路径。
        :param output_header_path: 输出的 .h 头文件路径。
        :return: 输出文件的路径。
        """
        ecl_path = Path(input_ecl_path).absolute()
        header_path = Path(output_header_path).absolute()
        header_path.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = ['-h', str(version)]
        if self.eclmap_path:
            cmd.extend(['-m', str(self.eclmap_path.absolute())])
            
        cmd.extend([str(ecl_path), str(header_path)])
        
        self._run_command(cmd)
        print(f"✅ 成功为 '{ecl_path.name}' 创建头文件 '{header_path.name}'。")
        return str(header_path)

# ==================================================================
# 调试和独立运行的示例代码
# ==================================================================
if __name__ == "__main__":
    # 使用方法:
    # 1. 将 thecl.exe 放在 'resources' 目录下。
    # 2. 将一个 eclmap 文件 (可选) 放在 'resources' 目录下。
    # 3. 将一个用于测试的 .ecl 文件放在 'data' 目录下。
    # 4. 在项目根目录运行 `python app/core/thecl_wrapper.py`
    
    # 创建必要的目录
    os.makedirs("resources", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    
    try:
        # 假设 a.exe 在 resources 目录
        thecl_exe_path = "resources/thecl.exe"
        eclmap_file_path = "resources/eclmap_th12.txt" # 示例，可以是任何有效的eclmap
        test_ecl_file = "data/st01.ecl" # 示例，你需要提供一个真实文件
        
        if not os.path.exists(thecl_exe_path):
            print(f"错误: a.exe 不在 '{thecl_exe_path}'。请放置好文件后重试。")
        elif not os.path.exists(test_ecl_file):
            print(f"错误: 测试文件不在 '{test_ecl_file}'。请放置好文件后重试。")
        else:
            # 初始化 Wrapper
            # 如果没有 eclmap 文件，可以将第二个参数设为 None
            wrapper = TheclWrapper(thecl_exe_path, eclmap_file_path)
            
            # --- 测试解包 ---
            print("\n--- Testing Unpack ---")
            unpacked_txt = "output/st01_unpacked.txt"
            wrapper.unpack("12", test_ecl_file, unpacked_txt, use_address_info=True)
            
            # --- 测试打包 ---
            print("\n--- Testing Pack ---")
            repacked_ecl = "output/st01_repacked.ecl"
            wrapper.pack("12", unpacked_txt, repacked_ecl)

            # --- 测试创建头文件 ---
            print("\n--- Testing Header Creation ---")
            header_file = "output/st01.h"
            wrapper.create_header("12", test_ecl_file, header_file)
            
            print("\n✅ All tests completed.")

    except (TheclError, FileNotFoundError) as e:
        print(f"\n❌ An error occurred: {e}")
        if isinstance(e, TheclError) and e.stderr:
            print(f"Stderr:\n{e.stderr}")