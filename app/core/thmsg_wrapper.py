# app/core/thmsg_wrapper.py

import json
import re
import subprocess
from pathlib import Path
from typing import List

class ThmsgError(Exception):
    """用于表示 thmsg.exe 调用失败的自定义异常。"""
    def __init__(self, message, stderr):
        super().__init__(message)
        self.stderr = stderr

class ThmsgWrapper:
    """
    一个封装了 thmsg.exe 工具和指令翻译逻辑的包装类。
    """
    def __init__(self, thmsg_path: str, reference_json_path: str):
        self.thmsg_path = Path(thmsg_path)
        self.reference_path = Path(reference_json_path)
        
        if not self.thmsg_path.is_file():
            raise FileNotFoundError(f"thmsg tool not found at {self.thmsg_path}")
        if not self.reference_path.is_file():
            raise FileNotFoundError(f"Reference file not found at {self.reference_path}")

        with open(self.reference_path, 'r', encoding='utf-8') as f:
            self.reference_data = json.load(f)

    def _run_command(self, command: List[str]) -> bytes:
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                error_message = stderr.decode('utf-8', errors='ignore') or stdout.decode('utf-8', errors='ignore')
                print(f"Command '{' '.join(command)}' failed with error:\n{error_message}")
                raise ThmsgError(f"命令执行出现错误, 请谨慎处理生成的文件", error_message)
            return stdout
        except FileNotFoundError:
            raise ThmsgError(f"Command not found", f"Command Not Found {command[0]}")
        except Exception as e:
            print(e)
            raise ThmsgError(f"命令执行出现错误, 请谨慎对待你的文件", e.stderr)

    # ==================================================================
    # 核心公开方法
    # ==================================================================

    def unpack(self, version: str, msg_path: str, output_txt_path: str, mode: str, encoding: str="Shift-JIS", keep_dmsg: bool = False):
        msg_path = Path(msg_path)
        txt_path = Path(output_txt_path)
        dmsg_path = txt_path.with_suffix('.dmsg')
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Decompiling {msg_path.name} to dmsg...")
        dmsg_bytes = self._run_command([str(self.thmsg_path.absolute()), '-d', str(version), str(msg_path.absolute())])
        dmsg_path.write_bytes(dmsg_bytes)
        
        print(f"Translating {dmsg_path.name} to txt...")
        self._translate_dmsg_to_txt(dmsg_path, txt_path, mode=mode, encoding=encoding)
        
        if not keep_dmsg:
            dmsg_path.unlink()
        
        print(f"Successfully unpacked {msg_path.name} to {txt_path.name}")
        return str(txt_path)

    def pack(self, version: str, txt_path: str, output_msg_path: str,encoding: str="Shift-JIS",keep_dmsg: bool = False):
        txt_path = Path(txt_path)
        msg_path = Path(output_msg_path)
        dmsg_path = txt_path.with_suffix('.dmsg')
        msg_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Recovering {txt_path.name} to dmsg...")
        self._recover_txt_to_dmsg(txt_path, dmsg_path, encoding=encoding)
        
        print(f"Compiling {dmsg_path.name} to msg...")
        self._run_command([
            str(self.thmsg_path.absolute()), '-c', str(version),
            str(dmsg_path.absolute()), str(msg_path.absolute())
        ])
        
        if not keep_dmsg:
            dmsg_path.unlink()
            
        print(f"Successfully packed {txt_path.name} to {msg_path.name}")
        return str(msg_path)

    # ==================================================================
    # 内部翻译和恢复逻辑
    # ==================================================================

    def _translate_dmsg_to_txt(self, dmsg_path: Path, output_path: Path, mode: str = "default",encoding: str="Shift-JIS"):
        """根据参考文件将 dmsg 文件翻译为可读的 txt 格式，使用4个空格进行缩进。"""
        original_dmsg_lines = dmsg_path.read_text(encoding=encoding, errors='ignore').splitlines()
        translated_lines = []
        indent = "    " # 使用4个空格作为缩进

        for line in original_dmsg_lines:
            content = line.strip()
            if not content: continue
            
            if content.startswith('entry'):
                translated_lines.append(content)
            elif content.startswith('@'):
                translated_lines.append(f'T={content[1:]}')
            else:
                ins_id, *args = content.split(';')
                if ins_id in self.reference_data:
                    ins_name = self.reference_data[ins_id][0].split('(')[0]
                    ins_desc = self.reference_data[ins_id][1]
                    translated_lines.append(f'{indent}{ins_name}({";".join(args)})')
                    if mode == 'default':
                        translated_lines.append(f'{indent}// {ins_desc}')
                else:
                    translated_lines.append(f'{indent}ins_{ins_id}({";".join(args)})')
                    if mode == 'default':
                        translated_lines.append(f'{indent}// Unknown Instruction ID')
        
        output_path.write_text('\n'.join(translated_lines) + '\n', encoding='utf-8')

    def _recover_txt_to_dmsg(self, txt_path: Path, output_path: Path, encoding: str="Shift-JIS"):
        """将翻译后的 txt 文件恢复为 dmsg 格式，生成带 \t 的 dmsg。"""
        txt_lines = txt_path.read_text(encoding='utf-8').splitlines()
        recovered_lines = []
        
        reverse_ref = {v[0].split('(')[0]: k for k, v in self.reference_data.items()}

        for line_num, line in enumerate(txt_lines, 1):
            content = line.strip()
            if not content or content.startswith('//'):
                continue

            if not line.startswith((' ', '\t')):
                if content.startswith('entry'):
                    recovered_lines.append(content)
                elif content.startswith('T='):
                    recovered_lines.append(f'@{content[2:]}')
                else:
                    print(f'Warning [Line {line_num}]: Unindented line is not a valid command: "{content}"')
                    recovered_lines.append(content)
            else:
                match = re.search(r'([\w_]+)\((.*)\)', content)
                if not match:
                    print(f'Warning [Line {line_num}]: Indented line has invalid format: "{content}"')
                    recovered_lines.append(line)
                    continue

                func_name, params_str = match.groups()
                params = params_str.split(';') if params_str else []
                
                line_to_write = ""
                if func_name in reverse_ref:
                    ins_id = reverse_ref[func_name]
                    # --- [KEY FIX] ---
                    # 针对 thmsg 工具的 bug，为特定无参数指令自动添加 '0'
                    # 7: speakerPlayer, 4: playerHide, 6: textboxHide, etc.
                    if ins_id in ('7') and not params:
                        print(f"DEBUG [Line {line_num}]: Auto-fixing empty params for instruction '{func_name}' (ID: {ins_id}). Adding '0'.")
                        params = ['0']
                    if ins_id in ('14') and len(params) < 2:
                        print(f"DEBUG [Line {line_num}]: Auto-fixing missing params for instruction '{func_name}' (ID: {ins_id}). Adding '0'.")
                        params.insert(0,'0')
                    # --- END FIX ---

                    if ins_id == '19' and not params: params = ['0']

                    line_to_write = f'{ins_id}' # dmsg格式不需要 \t
                    
                    if params: line_to_write += f';{";".join(params)}'
                elif func_name.startswith('ins_'):
                    try:
                        ins_id = func_name.split('_')[1]
                        line_to_write = f'{ins_id}'
                        if params: line_to_write += f';{";".join(params)}'
                    except (IndexError, ValueError):
                        print(f'Warning [Line {line_num}]: Could not parse unknown instruction: "{func_name}"')
                        line_to_write = line
                else:
                    print(f'Warning [Line {line_num}]: Function "{func_name}" not in reference. Keeping original.')
                    line_to_write = line
                
                # dmsg 格式的指令行本身不需要前导 \t，thmsg 工具会处理
                recovered_lines.append(line_to_write)

        output_path.write_text('\n'.join(recovered_lines) + '\n', encoding=encoding, errors='ignore')