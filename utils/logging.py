"""
日志工具模块
"""
import logging
from config import LOG_LEVEL, LOG_FORMAT, LOG_FILE

def setup_logger(name=None):
    """
    设置并返回一个配置好的logger
    
    Args:
        name: logger名称，默认为None，使用root logger
        
    Returns:
        已配置的logger实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    
    # 清除已存在的处理器
    if logger.handlers:
        logger.handlers.clear()
    
    # 创建文件处理器
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file_handler)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console_handler)
    
    return logger 