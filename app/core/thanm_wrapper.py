# app/core/thanm_wrapper.py
import subprocess
import os
from typing import List, Optional

class ThanmError(Exception):
    def __init__(self, message, stderr):
        super().__init__(message)
        self.stderr = stderr

class ThanmWrapper:
    def __init__(self, thanm_path: str, anmm_path: Optional[str] = None):
        if not os.path.isfile(thanm_path) or not os.access(thanm_path, os.X_OK):
            raise FileNotFoundError(f"指定的 thanm 路径 '{thanm_path}' 不存在。")
        self.thanm_path = thanm_path
        self.anmm_path = anmm_path
        if self.anmm_path and not os.path.isfile(self.anmm_path):
            print(f"警告: 指定的 anmm 映射文件 '{self.anmm_path}' 不存在。")
            self.anmm_path = None
        # 简化版：移除了 ref 和 map path 的自动加载，使其更通用

    def _run_command(self, args: List[str], working_dir: Optional[str] = None) -> str:
        command = [self.thanm_path] + args
        print(f"🚀 正在执行命令: {' '.join(command)}")
        if working_dir: print(f"   (在目录下: {working_dir})")
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, encoding='utf-8', 
                check=False, cwd=working_dir
            )
            if result is None:
                raise ThanmError("Thanm 编译错误。", "")
            if result.returncode != 0:
                raise ThanmError(
                    f"Thanm 命令执行失败 (退出码 {result.returncode})",
                    result.stderr.strip()
                )
            if result.stdout.strip(): print(f"📋 stdout:\n{result.stdout.strip()}")
            if result.stderr.strip(): 
                print(f"ℹ️ stderr:\n{result.stderr.strip()}")
                raise ThanmError(
                    "Thanm 命令执行时出现错误输出。", result.stderr.strip()
                )
            return result.stdout
        except Exception as e:
            raise ThanmError(f"执行命令时发生未知错误: {e}", e.stderr)

    # --- 您的原始方法 ---
    def analyze_structure(self, version: str, anm_path: str, output_path: str):
        """提取指令文件 (-l)，如果提供了 anmm 映射则使用它。"""
        cmd = ['-l', version, anm_path]
        if self.anmm_path:
            cmd.extend(['-m', self.anmm_path])
        content = self._run_command(cmd)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def extract_images(self, version: str, anm_path: str, working_dir: str):
        """提取图片素材 (-x)。"""
        # anm_path 需要是绝对路径，因为我们会切换工作目录
        cmd = ['-x', version, os.path.abspath(anm_path)]
        self._run_command(cmd, working_dir=working_dir)
        print(f"✅ 成功从 '{os.path.basename(anm_path)}' 提取图片到 '{working_dir}'。")

    def create(self, version: str, output_archive: str, spec_file: str):
        """打包新的档案 (-c)，如果提供了 anmm 映射则使用它。"""
        spec_dir = os.path.dirname(spec_file)
        spec_filename = os.path.basename(spec_file)
        relative_output_path = os.path.relpath(output_archive, spec_dir)
        cmd = ['-c', version, '-v', relative_output_path, spec_filename]
        if self.anmm_path:
            cmd.extend(['-m', self.anmm_path])
        self._run_command(cmd, working_dir=spec_dir)

    # --- 新增的高级封装方法 ---
    def unpack_all(self, version: str, anm_path: str, output_dir: str) -> str:
        """
        一个高级封装，执行完整的解包流程：
        1. 在 output_dir 中提取图片。
        2. 在 output_dir 中生成指令文件。
        返回生成的指令文件的路径。
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. 提取图片
        self.extract_images(version, anm_path, output_dir)
        
        # 2. 提取指令文件，我们约定它的名字和输出目录名一样，后缀为 .txt
        spec_file_path = os.path.join(output_dir, f"{os.path.basename(output_dir)}.txt")
        self.analyze_structure(version, anm_path, spec_file_path)
        
        return spec_file_path