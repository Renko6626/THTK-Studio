# app/core/parser.py

import re
from typing import Dict, Any

class ScriptParser:
    """
    一个健壮的 ANM 脚本解析器。
    使用分割策略配合贪婪匹配，确保完整捕获包含嵌套括号的块。
    """
    def parse(self, text: str) -> Dict[str, Any]:
        parsed_data = {"entries": {}, "scripts": {}}

        # --- 解析 Scripts ---
        script_pattern = re.compile(r'script\s+(\w+)\s*{')
        for match in script_pattern.finditer(text):
            script_name = match.group(1)
            line_num = text.count('\n', 0, match.start()) + 1
            parsed_data["scripts"][script_name] = {'line': line_num}

        # --- 使用分割策略来独立解析每个 Entry ---
        entry_sections = re.split(r'(?=entry\s+\w+\s*{)', text)

        for section in entry_sections:
            section = section.strip()
            if not section.startswith('entry'):
                continue
            
            # 对每个独立的 entry section 进行贪婪匹配 `((.|\n)*)`
            entry_match = re.match(r'entry\s+(\w+)\s*{((.|\n)*)}', section)
            if not entry_match:
                continue

            entry_name = entry_match.group(1)
            entry_content = entry_match.group(2)

            try:
                start_pos = text.find(section)
                line_num = text.count('\n', 0, start_pos) + 1
            except:
                line_num = -1

            entry_data = {'line': line_num, 'sprites': {}}
            
            # 提取 image_path
            name_match = re.search(r'name:\s*"([^"]+)"', entry_content)
            if name_match:
                entry_data['image_path'] = name_match.group(1)

            # 提取可选的宽高 / 偏移 / 其他数值字段（允许负号）
            int_field_patterns = {
                'width': r'width:\s*(-?\d+)',
                'height': r'height:\s*(-?\d+)',
                'xOffset': r'xOffset:\s*(-?\d+)',
                'yOffset': r'yOffset:\s*(-?\d+)',
                # 兼容下划线命名（若脚本使用不同风格）
                'x_offset': r'x_offset:\s*(-?\d+)',
                'y_offset': r'y_offset:\s*(-?\d+)',
            }
            for key, pattern in int_field_patterns.items():
                m = re.search(pattern, entry_content)
                if m:
                    try:
                        entry_data[key] = int(m.group(1))
                    except ValueError:
                        pass

            # 提取 sprites 块
            sprites_block_match = re.search(r'sprites:\s*{((.|\n)*)}', entry_content)
            if sprites_block_match:
                sprites_content = sprites_block_match.group(1)
                # 这个 pattern 匹配单个 sprite 定义
                sprite_pattern = re.compile(r'(\w+):\s*{\s*x:\s*(\d+),\s*y:\s*(\d+),\s*w:\s*(\d+),\s*h:\s*(\d+)\s*}')
                for sprite_match in sprite_pattern.finditer(sprites_content):
                    sprite_name = sprite_match.group(1)
                    entry_data['sprites'][sprite_name] = {
                        'x': int(sprite_match.group(2)), 'y': int(sprite_match.group(3)),
                        'w': int(sprite_match.group(4)), 'h': int(sprite_match.group(5)),
                    }
            
            parsed_data["entries"][entry_name] = entry_data
            
        return parsed_data

    def get_all_sprite_locations(self, text: str) -> Dict[str, int]:
        """
        使用健壮的分割策略来解析文本，以查找每个 sprite 定义的行号。
        """
        locations = {}
        entry_sections = re.split(r'(?=entry\s+\w+\s*{)', text)
        entry_name_pattern = re.compile(r'entry\s+(\w+)')
        sprite_pattern = re.compile(r'(\w+):\s*{')

        for section in entry_sections:
            section = section.strip()
            if not section.startswith('entry'): continue

            entry_match = entry_name_pattern.match(section)
            if not entry_match: continue
            entry_name = entry_match.group(1)

            section_offset = text.find(section)
            if section_offset == -1: continue
            
            for sprite_match in sprite_pattern.finditer(section):
                sprite_name = sprite_match.group(1)
                if sprite_name == 'sprites': continue

                absolute_sprite_pos = section_offset + sprite_match.start()
                line_number = text.count('\n', 0, absolute_sprite_pos) + 1
                full_sprite_name = f"{entry_name}/{sprite_name}"
                locations[full_sprite_name] = line_number
                
        return locations