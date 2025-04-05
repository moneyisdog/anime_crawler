"""
全局配置文件
"""
import os
import logging

# 基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据库配置
DB_PATH = os.path.join(BASE_DIR, 'anime_crawler.db')

# 视频存储配置
VIDEO_DIR = os.path.join(BASE_DIR, 'video')
if not os.path.exists(VIDEO_DIR):
    os.makedirs(VIDEO_DIR)

# 日志配置
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = os.path.join(BASE_DIR, 'crawler.log')

# 缓存配置
# 设置多个备用URL域名，以防主域名被屏蔽
BASE_DOMAINS = [
    'yhdm.one',
    # 'www.yhdm.one',
    # 'yhdm.tv',
    # 'www.yhdm.tv',
    # 'www.yehua.one'
]

BASE_URL = f'https://{BASE_DOMAINS[0]}'

# 多个User-Agent轮换
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'
]

# 示例数据目录
MOCK_DATA_DIR = os.path.join(BASE_DIR, "mock_data")

# Aria2 RPC配置
ARIA2_RPC_URL = 'http://localhost:6800/jsonrpc'
ARIA2_RPC_TOKEN = ''  # 如果设置了token，请在这里填写 