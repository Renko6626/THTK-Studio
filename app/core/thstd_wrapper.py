# app/core/thstd_wrapper.py

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import List

class ThstdError(Exception):
    """当 thstd 子进程返回错误时抛出此异常。"""
    def __init__(self, message, stderr=""):
        super().__init__(message)
        self.stderr = stderr

class _LabelNotFoundError(Exception):
    pass

class ThstdWrapper:
    """
    一个封装了 thstd.exe 工具、指令翻译和脚本预处理逻辑的包装类。
    """
    INSTRUCTION_RE = re.compile(r'^\s*([a-zA-Z_][\w_]*)\s*\((.*)\)\s*;.*$')
    LABEL_RE = re.compile(r'^\s*((?:\d+|@[a-zA-Z_]\w*)):')

    def __init__(self, thstd_path: str, reference_json_path: str):
        self.thstd_path = Path(thstd_path)
        self.reference_path = Path(reference_json_path)
        
        if not self.thstd_path.is_file():
             raise FileNotFoundError(f"指定的 thstd 路径 '{self.thstd_path}' 不存在或不是一个文件。")
        if not self.reference_path.is_file():
            raise FileNotFoundError(f"指定的参考文件路径 '{self.reference_path}' 不存在或不是一个文件。")

        self._load_reference_data()

    def _load_reference_data(self):
        try:
            with open(self.reference_path, 'r', encoding='utf-8') as f:
                self.reference_data = json.load(f)
            self.reverse_reference_data = {v[0].split('(')[0]: k for k, v in self.reference_data.items()}
        except Exception as e:
            raise ThstdError(f"加载STD参考文件时发生错误: {e}")

    def _run_command(self, args: List[str]) -> str:
        command = [str(self.thstd_path.absolute())] + args
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, encoding='utf-8', check=False
            )
            if result.returncode != 0:
                raise ThstdError(f"Thstd 命令执行失败 (退出码: {result.returncode})", result.stderr)
            return result.stdout
        except FileNotFoundError:
            raise FileNotFoundError(f"无法找到 thstd 可执行文件: '{self.thstd_path}'")
        except Exception as e:
            raise ThstdError(f"执行命令时发生未知错误: {e}")

    def unpack(self, version: str, std_path: str, output_txt_path: str, mode: str = "default"):
        std_path_abs = Path(std_path).absolute()
        txt_path = Path(output_txt_path)
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dstd_path = Path(tmpdir) / 'temp.dstd'
            self._run_command(['-d', str(version), str(std_path_abs), str(temp_dstd_path)])
            self._translate_dstd_file(temp_dstd_path, txt_path, mode)
        return str(txt_path)

    def pack(self, version: str, txt_path: str, output_std_path: str):
        txt_path = Path(txt_path)
        std_path_abs = Path(output_std_path).absolute()
        std_path_abs.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            preprocessed_content = self._preprocess_jmp_labels(original_content)
            final_content = self._insify_text(preprocessed_content)
            
            with tempfile.TemporaryDirectory() as tmpdir:
                temp_dstd_path = Path(tmpdir) / 'temp.dstd'
                with open(temp_dstd_path, 'w', encoding='utf-8') as f:
                    f.write(final_content)
                self._run_command(['-c', str(version), str(temp_dstd_path), str(std_path_abs)])
        except _LabelNotFoundError as e:
            raise ThstdError(f"脚本预处理失败: {e}")
        except (FileNotFoundError, ThstdError) as e:
            raise e
        except Exception as e:
            raise ThstdError(f"打包过程中发生未知错误: {e}")
        return str(std_path_abs)

    def _preprocess_jmp_labels(self, script_text: str) -> str:
        lines = script_text.splitlines()
        script_start_line = -1
        for i, line in enumerate(lines):
            if line.strip().upper() == 'SCRIPT:':
                script_start_line = i
                break
        if script_start_line == -1: return script_text

        label_offsets = {}
        current_offset = 0
        script_lines = lines[script_start_line + 1:]

        for line in script_lines:
            clean_line = line.strip()
            if not clean_line or clean_line.startswith('//'): continue
            
            if self.LABEL_RE.match(clean_line):
                label_name = self.LABEL_RE.match(clean_line).group(1)
                label_offsets[label_name] = current_offset
                continue

            ins_match = self.INSTRUCTION_RE.match(clean_line)
            if ins_match:
                args_str = ins_match.group(2).strip()
                num_args = len(args_str.split(',')) if args_str else 0
                current_offset += 8 + 4 * num_args

        processed_lines = lines[:script_start_line + 1]
        for line_num, line in enumerate(script_lines, start=script_start_line + 1):
            clean_line = line.strip()
            jmp_match = re.match(r'^\s*jmp\s*\(([^,]+),\s*(@[a-zA-Z_]\w*)\s*\);', clean_line)
            
            if jmp_match:
                time_arg, label_name = jmp_match.group(1).strip(), jmp_match.group(2)
                if label_name not in label_offsets:
                    raise _LabelNotFoundError(f"在第 {line_num + 1} 行: 未定义的标签 '{label_name}'")
                offset = label_offsets[label_name]
                indent = line[:len(line) - len(line.lstrip())]
                processed_lines.append(f"{indent}jmp({time_arg}, {offset});")
            else:
                processed_lines.append(line)
        return "\n".join(processed_lines)

    def _translate_dstd_file(self, dstd_path: Path, output_path: Path, mode: str):
        with open(dstd_path, 'r', encoding='utf-8') as file: lines = file.readlines()
        translated_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('ins_'):
                func_part = stripped.split('(')[0]
                args_part = stripped[len(func_part):]
                ins_id = func_part.replace('ins_', '')

                # vvvvvvvvvvvvvv 修正翻译逻辑 vvvvvvvvvvvvvv
                # 特例：ins_1(offset, time) -> jmp(time, offset)
                if ins_id == '1':
                    match = re.search(r'\(([^,]+),([^)]+)\);', stripped)
                    if match:
                        offset_arg, time_arg = match.group(1).strip(), match.group(2).strip()
                        translated_lines.append(f"    jmp({time_arg}, {offset_arg});\n")
                    else: # 格式不匹配，按原样翻译
                        translated_lines.append(line)
                else: # 通用翻译逻辑
                    new_func_name = self.reference_data.get(ins_id, [func_part])[0].split('(')[0]
                    translated_lines.append(f"    {new_func_name}{args_part}\n")
                
                if mode == 'default':
                    desc = self.reference_data.get(ins_id, [None, 'No description available'])[1]
                    translated_lines.append(f"    // {desc.strip()}\n")
                # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            else:
                translated_lines.append(line)
        with open(output_path, 'w', encoding='utf-8') as file: file.writelines(translated_lines)


    def _insify_text(self, text_content: str) -> str:
        """将翻译好的文本内容字符串恢复为dstd格式字符串。"""
        original_lines = text_content.splitlines()
        insified_lines = []
        for line in original_lines:
            stripped = line.strip()
            if stripped.startswith(r'//'): continue
            
            if line.startswith('\t') or line.startswith('    '):
                func_part = stripped.split('(')[0]

                # vvvvvvvvvvvvvv 核心修正 vvvvvvvvvvvvvv
                # 特例处理：将 jmp(time, offset) 转换为 ins_1(offset, time)
                if func_part == 'jmp':
                    match = re.search(r'\(([^,]+),([^)]+)\);', stripped)
                    if match:
                        time_arg = match.group(1).strip()
                        offset_arg = match.group(2).strip()
                        # 交换参数顺序以符合 thstd.exe 的要求
                        new_line = f"    ins_1({offset_arg}, {time_arg});"
                        insified_lines.append(new_line)
                    else:
                        # 如果格式不匹配，可能导致错误，但还是按原样添加
                        insified_lines.append(line.lstrip())
                else: # 通用处理逻辑
                    args_part = stripped[len(func_part):]
                    if func_part in self.reverse_reference_data:
                        ins_id = self.reverse_reference_data[func_part]
                        new_func_name = f"ins_{ins_id}"
                    else:
                        new_func_name = func_part
                    insified_lines.append(f"    {new_func_name}{args_part}")
                # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            else:
                insified_lines.append(line)
        return "\n".join(insified_lines)