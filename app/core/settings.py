# app/core/settings.py

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

class Settings:
    """
    一个健壮的设置管理类，用于加载和保存应用配置。
    它能智能地处理内置资源路径和用户自定义路径。
    """
    def __init__(self, filename: str = r"resources\settings.json"):
        """
        初始化设置管理器。
        
        Args:
            filename: 保存用户设置的文件名。
        """
        self.filepath = Path(filename)
        # --- [MODIFICATION 1] 添加新的设置键的默认值 ---
        self.data: Dict[str, Any] = {
            "user_thanm_path": "",
            "user_anmm_path": "",
            "user_thmsg_path": "",
            "user_msg_ref_path": "",
            "user_msg_syntax_path": "",
            "user_variables_path": "",
            "user_instructions_path": "",
            "user_anm_syntax_path": "",
            "user_thstd_path": "", # 添加 thstd 路径的用户设置键
            # [NEW] thecl 与 eclmap 用户路径
            "user_thecl_path": "",
            "user_eclmap_path": "",
            "user_std_ref_path": "",
            "user_ecl_ref_path": "",
        }
        
        # --- 定位并缓存所有内置资源的路径 ---
        self._internal_thanm_path = self._find_resource("thanm.exe")
        self._internal_anmm_path = self._find_resource("default.anmm")
        self._internal_thmsg_path = self._find_resource("thmsg.exe")
        self._internal_msg_ref_path = self._find_resource("thmsg_ref.json")
        self._internal_thstd_path = self._find_resource("thstd.exe")
        self._internal_std_ref_path = self._find_resource("thstd_ref.json")
        # [NEW] 可选的 thecl / eclmap 内置路径（若打包时提供）
        self._internal_thecl_path = self._find_resource("thecl.exe")
        # eclmap 文件名不固定，尝试常见命名；均未找到则为 None
        self._internal_eclmap_path = (
            self._find_resource("default.eclm") or
            self._find_resource("eclmap_th12.txt") or
            None
        )
        self._internal_ecl_ref_path = self._find_resource("thecl_ref.json")
        self._internal_instructions_path = self._find_resource("instructions.json")
        self._internal_variables_path = self._find_resource("variables.json")
        self._internal_anm_syntax_path = self._find_resource("anm_syntax_definitions.json") # 查找内置的 ANM 语法文件
        # msg_syntax_path 似乎没有默认的内置文件，所以我们不在这里查找它
    

        # --- 2. 加载用户保存在文件中的设置 ---
        self.load()

    def _get_base_path(self) -> Path:
        """
        获取基准路径，兼容开发环境和打包环境
        """
        if hasattr(sys, '_MEIPASS'):
            # 打包后的环境 - 资源在 _MEIPASS 目录下
            return Path(sys._MEIPASS)
        else:
            # 开发环境
            return Path(__file__).parent.parent.parent  # 根据你的项目结构调整

    def _find_resource(self, name: str) -> Optional[Path]:
        """
        在基准路径下的 "resources" 文件夹中查找资源文件。
        """
        res_path = self._get_base_path() / "resources" / name
        # print(res_path)
        if res_path.is_file():
            print(f"✅ 找到内置资源: {res_path}")
            return res_path
        print(f"ℹ️ 未找到内置资源: {name}")
        return None

    def load(self):
        """从 JSON 文件加载用户设置。"""
        if self.filepath.is_file():
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    user_data = json.load(f)
                    for key in self.data:
                        if key in user_data:
                            self.data[key] = user_data[key]
            except (json.JSONDecodeError, IOError) as e:
                print(f"警告: 无法加载设置文件 '{self.filepath}'。错误: {e}")

    def save(self):
        """将当前的用户设置保存到 JSON 文件。"""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"错误: 无法写入设置文件 '{self.filepath}'。错误: {e}")

    # ==================================================================
    # 公共接口 (Public API)
    # ==================================================================

    def get_thanm_path(self) -> str:
        """获取最终要使用的 thanm.exe 路径。"""
        user_path = Path(self.data.get("user_thanm_path", ""))
        if user_path.is_file():
            return str(user_path)
        if self._internal_thanm_path:
            return str(self._internal_thanm_path)
        return ""
    
    def get_anmm_path(self) -> str:
        """获取最终要使用的 .anmm 文件的路径。"""
        user_path = Path(self.data.get("user_anmm_path", ""))
        if user_path.is_file():
            return str(user_path)
        if self._internal_anmm_path:
            return str(self._internal_anmm_path)
        return ""

    def get_thmsg_path(self) -> str:
        """获取 thmsg.exe 的路径，优先用户设置。"""
        user_path = Path(self.data.get("user_thmsg_path", ""))
        if user_path.is_file():
            return str(user_path)
        if self._internal_thmsg_path:
            return str(self._internal_thmsg_path)
        return ""

    def get_msg_ref_path(self) -> str:
        """获取 thmsg_ref.json 的路径，优先用户设置。"""
        user_path = Path(self.data.get("user_msg_ref_path", ""))
        if user_path.is_file():
            return str(user_path)
        if self._internal_msg_ref_path:
            return str(self._internal_msg_ref_path)
        return ""

    def get_thstd_path(self) -> str:
        """获取 thstd.exe 的路径，优先用户设置。"""
        user_path = Path(self.data.get("user_thstd_path", ""))
        if user_path.is_file():
            return str(user_path)
        if self._internal_thstd_path:
            return str(self._internal_thstd_path)
        return ""

    def get_std_ref_path(self) -> str:
        """获取 thstd_ref.json 的路径，优先用户设置。"""
        user_path = Path(self.data.get("user_std_ref_path", ""))
        if user_path.is_file():
            return str(user_path)
        if self._internal_std_ref_path:
            return str(self._internal_std_ref_path)
        return ""

    # [NEW] ECL 相关路径
    def get_thecl_path(self) -> str:
        """获取 thecl.exe 的路径，优先用户设置。"""
        user_path = Path(self.data.get("user_thecl_path", ""))
        if user_path.is_file():
            return str(user_path)
        if getattr(self, "_internal_thecl_path", None):
            return str(self._internal_thecl_path)
        return ""

    def get_eclmap_path(self) -> str:
        """获取 eclmap 文件的路径（可选），优先用户设置。"""
        user_path = Path(self.data.get("user_eclmap_path", ""))
        if user_path.is_file():
            return str(user_path)
        if getattr(self, "_internal_eclmap_path", None):
            return str(self._internal_eclmap_path)
        return ""
    def get_ecl_ref_path(self) -> str:
        """获取 thecl_ref.json 的路径，优先用户设置。"""
        user_path = Path(self.data.get("user_ecl_ref_path", ""))
        if user_path.is_file():
            return str(user_path)
        if self._internal_ecl_ref_path:
            return str(self._internal_ecl_ref_path)
        return ""
    def get_anm_syntax_path(self) -> str:
        """获取 ANM 语法定义文件 (syntax_definitions.json) 的路径，优先用户设置。"""
        user_path = Path(self.data.get("user_anm_syntax_path", ""))
        if user_path.is_file():
            return str(user_path)
        if self._internal_anm_syntax_path:
            return str(self._internal_anm_syntax_path)
        return ""

    def get_instructions_path(self) -> str:
        """获取 instructions.json 的路径，优先用户设置。"""
        user_path = Path(self.data.get("user_instructions_path", ""))
        if user_path.is_file():
            return str(user_path)
        if self._internal_instructions_path:
            return str(self._internal_instructions_path)
        return ""

    def get_variables_path(self) -> str:
        """获取 variables.json 的路径，优先用户设置。"""
        user_path = Path(self.data.get("user_variables_path", ""))
        if user_path.is_file():
            return str(user_path)
        if self._internal_variables_path:
            return str(self._internal_variables_path)
        return ""

    def get_msg_syntax_path(self) -> str:
        """获取用户自定义的 msg_syntax.json 路径。"""
        user_path = Path(self.data.get("user_msg_syntax_path", ""))
        if user_path.is_file():
            return str(user_path)
        return ""
        
    def set_user_path(self, key: str, value: str):
        """
        设置一个用户自定义的路径并立即保存。
        
        Args:
            key: 必须是 self.data 中已定义的键。
            value: 文件的路径字符串。
        """
        if key in self.data:
            self.data[key] = value
            self.save()
        else:
            print(f"警告: 尝试设置一个未知的键 '{key}''")