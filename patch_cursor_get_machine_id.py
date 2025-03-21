#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import os
import platform
import re
import shutil
import sys
import tempfile
from typing import Tuple
from config import Config
from cursor_path_utils import get_cursor_path


# 配置日志
def setup_logging() -> logging.Logger:
    """配置并返回logger实例"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logger = setup_logging()


def get_cursor_paths() -> Tuple[str, str]:
    """
    获取 Cursor 应用程序的 package.json 和 main.js 路径
    使用cursor_path_utils模块获取路径

    Returns:
        Tuple[str, str]: (package.json路径, main.js路径)的元组

    Raises:
        OSError: 当找不到有效路径或系统不支持时抛出
    """
    try:
        # 获取配置中的自定义路径
        config = Config()
        custom_path = config.get_cursor_install_path()
        
        # 使用路径工具获取文件路径
        pkg_path = get_cursor_path('package_json', custom_path)
        main_path = get_cursor_path('main_js', custom_path)
        
        # 检查路径是否有效
        if not all(os.path.exists(path) for path in [pkg_path, main_path]):
            logger.warning(f"未找到有效的Cursor文件路径: {pkg_path}, {main_path}")
            logger.info("请确保Cursor已正确安装或在.env文件中正确配置CURSOR_INSTALL_PATH")
            raise FileNotFoundError("未找到有效的Cursor文件路径")
            
        logger.info(f"找到Cursor文件: {pkg_path}, {main_path}")
        return (pkg_path, main_path)
        
    except (ValueError, FileNotFoundError, NotImplementedError) as e:
        logger.error(f"获取Cursor路径时出错: {str(e)}")
        system = platform.system()
        
        if system == "Windows":
            logger.info('可能您的Cursor不是默认安装路径,请执行以下操作之一:')
            logger.info('1. 在.env文件中配置CURSOR_INSTALL_PATH指定自定义安装路径')
            logger.info('2. 创建软连接,命令如下:')
            logger.info('cmd /c mklink /d "C:\\Users\\<username>\\AppData\\Local\\Programs\\Cursor" "默认安装路径"')
            logger.info('例如:')
            logger.info('cmd /c mklink /d "C:\\Users\\<username>\\AppData\\Local\\Programs\\Cursor" "D:\\SoftWare\\cursor"')
            input("\n程序执行完毕，按回车键退出...")
            sys.exit(1)
        raise OSError(f"无法确定Cursor路径: {str(e)}")


def check_system_requirements(pkg_path: str, main_path: str) -> bool:
    """
    检查系统要求

    Args:
        pkg_path: package.json 文件路径
        main_path: main.js 文件路径

    Returns:
        bool: 检查是否通过
    """
    for file_path in [pkg_path, main_path]:
        if not os.path.isfile(file_path):
            logger.error(f"文件不存在: {file_path}")
            return False

        if not os.access(file_path, os.W_OK):
            logger.error(f"没有文件写入权限: {file_path}")
            return False

    return True


def version_check(version: str, min_version: str = "", max_version: str = "") -> bool:
    """
    版本号检查

    Args:
        version: 当前版本号
        min_version: 最小版本号要求
        max_version: 最大版本号要求

    Returns:
        bool: 版本号是否符合要求
    """
    version_pattern = r"^\d+\.\d+\.\d+$"
    try:
        if not re.match(version_pattern, version):
            logger.error(f"无效的版本号格式: {version}")
            return False

        def parse_version(ver: str) -> Tuple[int, ...]:
            return tuple(map(int, ver.split(".")))

        current = parse_version(version)

        if min_version and current < parse_version(min_version):
            logger.error(f"版本号 {version} 小于最小要求 {min_version}")
            return False

        if max_version and current > parse_version(max_version):
            logger.error(f"版本号 {version} 大于最大要求 {max_version}")
            return False

        return True

    except Exception as e:
        logger.error(f"版本检查失败: {str(e)}")
        return False


def modify_main_js(main_path: str) -> bool:
    """
    修改 main.js 文件

    Args:
        main_path: main.js 文件路径

    Returns:
        bool: 修改是否成功
    """
    try:
        # 获取原始文件的权限和所有者信息
        original_stat = os.stat(main_path)
        original_mode = original_stat.st_mode
        original_uid = original_stat.st_uid
        original_gid = original_stat.st_gid

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
            with open(main_path, "r", encoding="utf-8") as main_file:
                content = main_file.read()

            # 执行替换
            patterns = {
                r"async getMachineId\(\)\{return [^??]+\?\?([^}]+)\}": r"async getMachineId(){return \1}",
                r"async getMacMachineId\(\)\{return [^??]+\?\?([^}]+)\}": r"async getMacMachineId(){return \1}",
            }

            for pattern, replacement in patterns.items():
                content = re.sub(pattern, replacement, content)

            tmp_file.write(content)
            tmp_path = tmp_file.name

        # 使用 shutil.copy2 保留文件权限
        shutil.copy2(main_path, main_path + ".old")
        shutil.move(tmp_path, main_path)

        # 恢复原始文件的权限和所有者
        os.chmod(main_path, original_mode)
        if os.name != "nt":  # 在非Windows系统上设置所有者
            os.chown(main_path, original_uid, original_gid)

        logger.info("文件修改成功")
        return True

    except Exception as e:
        logger.error(f"修改文件时发生错误: {str(e)}")
        if "tmp_path" in locals():
            os.unlink(tmp_path)
        return False


def backup_files(pkg_path: str, main_path: str) -> bool:
    """
    备份原始文件

    Args:
        pkg_path: package.json 文件路径（未使用）
        main_path: main.js 文件路径

    Returns:
        bool: 备份是否成功
    """
    try:
        # 只备份 main.js
        if os.path.exists(main_path):
            backup_main = f"{main_path}.bak"
            shutil.copy2(main_path, backup_main)
            logger.info(f"已备份 main.js: {backup_main}")

        return True
    except Exception as e:
        logger.error(f"备份文件失败: {str(e)}")
        return False


def restore_backup_files(pkg_path: str, main_path: str) -> bool:
    """
    恢复备份文件

    Args:
        pkg_path: package.json 文件路径（未使用）
        main_path: main.js 文件路径

    Returns:
        bool: 恢复是否成功
    """
    try:
        # 只恢复 main.js
        backup_main = f"{main_path}.bak"
        if os.path.exists(backup_main):
            shutil.copy2(backup_main, main_path)
            logger.info(f"已恢复 main.js")
            return True

        logger.error("未找到备份文件")
        return False
    except Exception as e:
        logger.error(f"恢复备份失败: {str(e)}")
        return False


def patch_cursor_get_machine_id(restore_mode=False) -> None:
    """
    主函数

    Args:
        restore_mode: 是否为恢复模式
    """
    logger.info("开始执行脚本...")

    try:
        # 获取路径
        pkg_path, main_path = get_cursor_paths()

        # 检查系统要求
        if not check_system_requirements(pkg_path, main_path):
            sys.exit(1)

        if restore_mode:
            # 恢复备份
            if restore_backup_files(pkg_path, main_path):
                logger.info("备份恢复完成")
            else:
                logger.error("备份恢复失败")
            return

        # 获取版本号
        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                version = json.load(f)["version"]
            logger.info(f"当前 Cursor 版本: {version}")
        except Exception as e:
            logger.error(f"无法读取版本号: {str(e)}")
            sys.exit(1)

        # 检查版本
        if not version_check(version, min_version="0.45.0"):
            logger.error("版本不符合要求（需 >= 0.45.x）")
            sys.exit(1)

        logger.info("版本检查通过，准备修改文件")

        # 备份文件
        if not backup_files(pkg_path, main_path):
            logger.error("文件备份失败，终止操作")
            sys.exit(1)

        # 修改文件
        if not modify_main_js(main_path):
            sys.exit(1)

        logger.info("脚本执行完成")

    except Exception as e:
        logger.error(f"执行过程中发生错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    patch_cursor_get_machine_id()
