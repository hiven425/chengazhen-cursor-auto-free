import os
import sys
import logging
import platform
from typing import Optional, Dict, Union, List

logger = logging.getLogger(__name__)

class CursorPathUtils:
    """Cursor路径工具类
    
    负责处理Cursor各种文件的路径解析，支持自定义安装路径
    """
    
    def __init__(self, custom_path: Optional[str] = None):
        """初始化路径工具
        
        Args:
            custom_path: 可选的自定义Cursor安装路径
        """
        self.custom_path = custom_path
        
        # 文件类型与相对路径的映射
        self.file_paths = {
            'state_db': 'User/globalStorage/state.vscdb',
            'storage_json': 'User/globalStorage/storage.json',
            'app_dir': 'resources/app' if sys.platform == 'win32' else 'Contents/Resources/app',
            'package_json': '',  # 将动态添加，依赖于app_dir
            'main_js': ''        # 将动态添加，依赖于app_dir
        }
        
        # 操作系统默认路径
        self.default_paths = {
            "win32": {
                "app_base": os.path.join(
                    os.getenv("USERAPPPATH") or os.path.join(
                        os.getenv("LOCALAPPDATA", ""), "Programs", "Cursor", "resources", "app"
                    )
                ),
                "data_base": os.path.join(os.getenv("APPDATA", ""), "Cursor")
            },
            "darwin": {
                "app_base": "/Applications/Cursor.app/Contents/Resources/app",
                "data_base": os.path.abspath(os.path.expanduser("~/Library/Application Support/Cursor"))
            },
            "linux": {
                "app_bases": ["/opt/Cursor/resources/app", "/usr/share/cursor/resources/app"],
                "data_base": os.path.abspath(os.path.expanduser("~/.config/Cursor"))
            }
        }
    
    def get_path(self, file_type: str) -> str:
        """获取Cursor文件路径
        
        Args:
            file_type: 文件类型，支持 'state_db', 'storage_json', 'package_json', 'main_js', 'app_dir'
            
        Returns:
            str: 文件的完整路径
            
        Raises:
            ValueError: 当file_type不是支持的值时抛出
            NotImplementedError: 当不支持的操作系统时抛出
            FileNotFoundError: 当找不到文件时抛出
        """
        # 验证文件类型
        if file_type not in self.file_paths:
            raise ValueError(f"不支持的文件类型: {file_type}，可选值为: {', '.join(self.file_paths.keys())}")
        
        # 系统检查
        if sys.platform not in ["win32", "darwin", "linux"]:
            raise NotImplementedError(f"不支持的操作系统: {sys.platform}")
        
        # 分情况处理路径
        if self.custom_path:
            return self._get_path_with_custom_path(file_type)
        else:
            return self._get_path_with_default_path(file_type)
    
    def _get_path_with_custom_path(self, file_type: str) -> str:
        """使用自定义路径获取文件路径
        
        Args:
            file_type: 文件类型
            
        Returns:
            str: 文件路径
        """
        assert self.custom_path, "自定义路径不能为空"
        
        if file_type in ['app_dir', 'package_json', 'main_js']:
            # 应用程序相关文件
            if sys.platform == "win32":
                # Windows系统
                app_path = os.path.join(self.custom_path, 'resources', 'app')
                if not os.path.exists(app_path):
                    app_path = self.custom_path  # 假设用户已提供完整路径
            
            elif sys.platform == "darwin":
                # macOS系统
                if "Resources/app" not in self.custom_path:
                    app_path = os.path.join(self.custom_path, "Contents", "Resources", "app")
                else:
                    app_path = self.custom_path
            
            else:  # Linux
                app_path = self.custom_path
                
            # 根据文件类型返回具体路径
            if file_type == 'app_dir':
                return app_path
            elif file_type == 'package_json':
                return os.path.join(app_path, 'package.json')
            elif file_type == 'main_js':
                return os.path.join(app_path, 'out', 'main.js')
        else:
            # 数据相关文件(state_db, storage_json等)
            return os.path.join(self.custom_path, self.file_paths[file_type])

    def _get_path_with_default_path(self, file_type: str) -> str:
        """使用默认路径获取文件路径
        
        Args:
            file_type: 文件类型
            
        Returns:
            str: 文件路径
            
        Raises:
            FileNotFoundError: 当找不到文件时抛出
            EnvironmentError: 当环境变量未设置时抛出
        """
        if sys.platform == "win32":
            # Windows系统
            if file_type in ['app_dir', 'package_json', 'main_js']:
                base_path = self.default_paths["win32"]["app_base"]
                if file_type == 'app_dir':
                    return base_path
                elif file_type == 'package_json':
                    return os.path.join(base_path, 'package.json')
                elif file_type == 'main_js':
                    return os.path.join(base_path, 'out', 'main.js')
            else:
                # 数据文件路径
                appdata = os.getenv("APPDATA")
                if appdata is None:
                    raise EnvironmentError("APPDATA 环境变量未设置")
                return os.path.join(appdata, "Cursor", self.file_paths[file_type])
        
        elif sys.platform == "darwin":
            # macOS系统
            if file_type in ['app_dir', 'package_json', 'main_js']:
                base_path = self.default_paths["darwin"]["app_base"]
                if file_type == 'app_dir':
                    return base_path
                elif file_type == 'package_json':
                    return os.path.join(base_path, 'package.json')
                elif file_type == 'main_js':
                    return os.path.join(base_path, 'out', 'main.js')
            else:
                # 数据文件路径
                return os.path.join(
                    self.default_paths["darwin"]["data_base"], 
                    self.file_paths[file_type]
                )
        
        elif sys.platform == "linux":
            # Linux系统
            if file_type in ['app_dir', 'package_json', 'main_js']:
                # 尝试多个可能的路径
                for base_path in self.default_paths["linux"]["app_bases"]:
                    if file_type == 'app_dir' and os.path.exists(base_path):
                        return base_path
                    elif file_type == 'package_json':
                        path = os.path.join(base_path, 'package.json')
                        if os.path.exists(path):
                            return path
                    elif file_type == 'main_js':
                        path = os.path.join(base_path, 'out', 'main.js')
                        if os.path.exists(path):
                            return path
                
                # 如果没有找到有效路径
                raise FileNotFoundError(f"在Linux系统上未找到Cursor的{file_type}路径")
            else:
                # 数据文件路径
                return os.path.join(
                    self.default_paths["linux"]["data_base"], 
                    self.file_paths[file_type]
                )

    def print_paths(self) -> None:
        """打印所有路径信息，用于调试"""
        for file_type in self.file_paths:
            try:
                path = self.get_path(file_type)
                exists = os.path.exists(path)
                logger.info(f"{file_type}: {path} {'[存在]' if exists else '[不存在]'}")
            except Exception as e:
                logger.error(f"获取{file_type}路径出错: {str(e)}")


# 辅助函数，供其他模块调用
def get_cursor_path(file_type: str, custom_path: Optional[str] = None) -> str:
    """获取Cursor相关文件的路径
    
    Args:
        file_type: 需要获取的文件类型，可选值：'state_db', 'storage_json', 'package_json', 'main_js', 'app_dir'
        custom_path: 可选的自定义Cursor安装路径
        
    Returns:
        str: 对应文件的完整路径
    """
    path_utils = CursorPathUtils(custom_path)
    return path_utils.get_path(file_type)


# 测试用代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 使用默认路径
    utils = CursorPathUtils()
    utils.print_paths()
    
    # 使用自定义路径
    custom_path = "D:\\Programs\\Cursor"
    print(f"\n使用自定义路径: {custom_path}")
    utils = CursorPathUtils(custom_path)
    utils.print_paths() 