# touhou_script_editor/app/core/image_manager.py

import os
from typing import Dict, Optional
from PIL import Image, UnidentifiedImageError

# 'Image.Image' 是 Pillow 库中图像对象的类型注解
ImageType = Image.Image 

class ImageManager:
    """
    负责加载、缓存和裁剪精灵图集（spritesheet）。

    这个类维护一个内存缓存，以避免对同一图像文件进行重复的磁盘I/O操作，
    从而在UI频繁刷新时提升性能。
    """
    def __init__(self, base_path: str = ''):
        """
        初始化 ImageManager。
        
        Args:
            base_path: 脚本文件所在的目录，用于解析相对图像路径。
        """
        self.base_path = base_path
        self.image_cache: Dict[str, Optional[ImageType]] = {}

    def set_base_path(self, path: str):
        """设置用于解析相对路径的基准目录。"""
        self.base_path = path

    def _get_full_path(self, relative_path: str) -> str:
        """根据基准目录计算图像的完整绝对路径。"""
        return os.path.join(self.base_path, relative_path)

    def load_spritesheet(self, relative_path: str) -> Optional[ImageType]:
        """
        加载指定的精灵图集到缓存中（如果尚未加载）。

        Args:
            relative_path: 相对于基准目录的图像文件路径。

        Returns:
            Pillow 的 Image 对象，如果加载失败则返回 None。
        """
        full_path = self._get_full_path(relative_path)
        
        if full_path in self.image_cache:
            return self.image_cache[full_path]
        
        try:
            print(f"正在从硬盘加载图像: {full_path}")
            image = Image.open(full_path)
            # 立即加载图像数据，以便可以关闭文件句柄
            image.load() 
            self.image_cache[full_path] = image
            return image
        except (FileNotFoundError, UnidentifiedImageError, IOError) as e:
            print(f"错误：无法加载图像 '{full_path}'. 原因: {e}")
            # 存入 None 以防止后续重复尝试加载这个不存在或损坏的文件
            self.image_cache[full_path] = None
            return None

    def get_sprite_image(self, relative_path: str, rect: Dict[str, int]) -> Optional[ImageType]:
        """
        从指定的精灵图集中裁剪出单个精灵的图像。

        Args:
            relative_path: 图像文件的相对路径。
            rect: 一个包含 'x', 'y', 'w', 'h' 键的字典，定义了裁剪区域。

        Returns:
            裁剪后的 Pillow Image 对象，如果失败则返回 None。
        """
        spritesheet = self.load_spritesheet(relative_path)
        if not spritesheet:
            return None

        # 定义裁剪区域: (left, upper, right, lower)
        box = (
            rect['x'],
            rect['y'],
            rect['x'] + rect['w'],
            rect['y'] + rect['h']
        )
        
        try:
            sprite = spritesheet.crop(box)
            return sprite
        except Exception as e:
            print(f"错误：裁剪精灵时出错。路径: {relative_path}, 区域: {box}. 原因: {e}")
            return None

    def clear_cache(self):
        """清空所有已缓存的图像，用于在关闭或切换项目时释放内存。"""
        print("正在清空图像缓存...")
        self.image_cache.clear()

# --- 使用示例和测试 ---
if __name__ == '__main__':
    # 为了让这个示例能独立运行，我们需要模拟一个环境
    # 1. 导入我们之前写的解析器
    from parser import ScriptParser

    # 2. 准备一个测试脚本
    # 注意：我们将 'name' 字段指向一个我们实际拥有的文件
    # 请在 core 文件夹旁边创建一个名为 'test_assets' 的文件夹，
    # 并在其中放入一张名为 'test_player.png' 的图片。
    sample_script = """
    entry entry0 {
    version: 8,
    name: "test_assets\pl00\pl00.png",
    format: 1,
    width: 256,
    height: 256,
    memoryPriority: 10,
    lowResScale: 0,
    hasData: 1,
    THTXFormat: 1,
    THTXWidth: 256,
    THTXHeight: 144,
    THTXZero: 0,
    w_max: 256,
    h_max: 144,
    sprites: {
        sprite0: { x: 1, y: 1, w: 30, h: 46 },
        sprite1: { x: 33, y: 1, w: 30, h: 46 },
        sprite2: { x: 65, y: 1, w: 30, h: 46 },
        sprite3: { x: 97, y: 1, w: 30, h: 46 },
        sprite4: { x: 129, y: 1, w: 30, h: 46 },
        sprite5: { x: 161, y: 1, w: 30, h: 46 },
        sprite6: { x: 193, y: 1, w: 30, h: 46 },
        sprite7: { x: 225, y: 1, w: 30, h: 46 },
        sprite8: { x: 1, y: 49, w: 30, h: 46 },
        sprite9: { x: 33, y: 49, w: 30, h: 46 },
        sprite10: { x: 65, y: 49, w: 30, h: 46 },
        sprite11: { x: 97, y: 49, w: 30, h: 46 },
        sprite12: { x: 129, y: 49, w: 30, h: 46 },
        sprite13: { x: 161, y: 49, w: 30, h: 46 },
        sprite14: { x: 193, y: 49, w: 30, h: 46 },
        sprite15: { x: 225, y: 49, w: 30, h: 46 },
        sprite16: { x: 1, y: 97, w: 30, h: 46 },
        sprite17: { x: 33, y: 97, w: 30, h: 46 },
        sprite18: { x: 65, y: 97, w: 30, h: 46 },
        sprite19: { x: 97, y: 97, w: 30, h: 46 },
        sprite20: { x: 129, y: 97, w: 30, h: 46 },
        sprite21: { x: 161, y: 97, w: 30, h: 46 },
        sprite22: { x: 193, y: 97, w: 30, h: 46 },
        sprite23: { x: 225, y: 97, w: 30, h: 46 }
    }
}
    """

    # 3. 创建一个虚拟的图片文件用于测试



    # 4. 开始测试流程
    # 假设我们的脚本文件位于 'touhou_script_editor/app/core/' 目录
    # 那么基准路径就是上一级目录 'touhou_script_editor/app/'
    script_base_path = os.path.dirname(os.getcwd()) # 获取上一级目录
    
    parser = ScriptParser()
    image_manager = ImageManager(base_path=script_base_path)

    parsed_data = parser.parse(sample_script)
    
    if parsed_data:
        print("\n--- 开始从解析结果中提取并裁剪精灵 ---")
        for entry_name, entry_data in parsed_data.items():
            image_path = entry_data['image_path']
            print(f"\n处理 Entry '{entry_name}' (图像: {image_path})")
            
            for sprite_name, sprite_rect in entry_data['sprites'].items():
                print(f"  -> 正在获取 '{sprite_name}'...")
                
                # 获取裁剪后的精灵图像
                sprite_image = image_manager.get_sprite_image(image_path, sprite_rect)
                
                if sprite_image:
                    print(f"     成功裁剪! 图像尺寸: {sprite_image.size}")
                    # 你可以在这里取消注释来保存或显示图片，以进行验证
                    # sprite_image.save(f"sprite_{sprite_name}.png")
                    # sprite_image.show()
                else:
                    print(f"     裁剪失败!")
    
    # 测试缓存功能：再次获取同一个精灵
    print("\n--- 测试缓存 ---")
    print("第二次获取 'sprite_idle_1' (应直接从缓存读取，不会显示'正在从硬盘加载...')")
    image_manager.get_sprite_image("test_assets/test_player.png", {"x": 1, "y": 1, "w": 30, "h": 46})