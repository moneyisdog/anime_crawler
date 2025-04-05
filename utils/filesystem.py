"""
文件系统操作工具模块
"""
import os
import shutil
import logging
from config import VIDEO_DIR

logger = logging.getLogger(__name__)

def ensure_dir_exists(directory):
    """
    确保目录存在，不存在则创建
    
    Args:
        directory: 目录路径
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"创建目录: {directory}")

def get_video_path(anime_id, episode_id, extension="mp4"):
    """
    获取视频文件的存储路径
    
    Args:
        anime_id: 动漫ID
        episode_id: 剧集ID
        extension: 文件扩展名，默认为mp4
    
    Returns:
        视频文件完整路径
    """
    anime_dir = os.path.join(VIDEO_DIR, str(anime_id))
    ensure_dir_exists(anime_dir)
    
    # 确保文件名安全
    filename = f"ep{episode_id}.{extension}"
    return os.path.join(anime_dir, filename)

def get_relative_video_path(anime_id, episode_id, extension="mp4"):
    """
    获取相对于基础目录的视频文件路径，用于URL
    
    Args:
        anime_id: 动漫ID
        episode_id: 剧集ID
        extension: 文件扩展名，默认为mp4
    
    Returns:
        视频文件的相对路径
    """
    return f"{anime_id}/ep{episode_id}.{extension}"

def file_exists(filepath):
    """
    检查文件是否存在
    
    Args:
        filepath: 文件路径
    
    Returns:
        布尔值，文件是否存在
    """
    return os.path.exists(filepath) and os.path.isfile(filepath)

def get_file_size(filepath):
    """
    获取文件大小(字节)
    
    Args:
        filepath: 文件路径
    
    Returns:
        文件大小(字节)，如果文件不存在则返回0
    """
    if file_exists(filepath):
        return os.path.getsize(filepath)
    return 0

def delete_file(filepath):
    """
    删除文件
    
    Args:
        filepath: 要删除的文件路径
    
    Returns:
        布尔值，表示是否成功删除
    """
    try:
        if file_exists(filepath):
            os.remove(filepath)
            logger.info(f"删除文件: {filepath}")
            return True
        return False
    except Exception as e:
        logger.error(f"删除文件失败: {filepath}, 错误: {str(e)}")
        return False 