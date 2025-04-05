"""
网络工具模块
"""
import requests
import ssl
import random
import time
import logging
import urllib3
from urllib3.util.ssl_ import create_urllib3_context
from requests.adapters import HTTPAdapter
from config import BASE_DOMAINS, USER_AGENTS, BASE_URL

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

def get_random_ua():
    """获取随机User-Agent"""
    return random.choice(USER_AGENTS)

def get_domain():
    """获取域名"""
    return BASE_URL.replace('https://', '')
    
def get_base_url():
    """获取基础URL"""
    return BASE_URL

class EOFHandlingSSLAdapter(HTTPAdapter):
    """处理EOF错误的SSL适配器"""
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        # 禁用SSL验证
        kwargs['ssl_context'] = context
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        # 设置安全协议版本
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        # 启用所有TLS协议
        context.options |= 0x4  # SSL_OP_LEGACY_SERVER_CONNECT
        kwargs['assert_hostname'] = False
        
        # 允许更宽松的SSL握手行为
        kwargs['retries'] = urllib3.Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=frozenset(['GET', 'POST', 'HEAD']),
            respect_retry_after_header=False
        )
        
        # 增加连接超时时间
        kwargs['timeout'] = urllib3.Timeout(connect=30, read=kwargs.get('timeout', 20))
        return super().init_poolmanager(*args, **kwargs)

def make_request(url, headers=None, retry=3, timeout=20, verify=False):
    """
    发起HTTP请求，自动重试
    
    Args:
        url: 请求的URL
        headers: 请求头
        retry: 重试次数
        timeout: 超时时间(秒)
        verify: 是否验证SSL证书
        
    Returns:
        字典包含status_code和response
    """
    if headers is None:
        headers = {
            'User-Agent': get_random_ua(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'close', # 使用短连接，避免持久连接可能导致的问题
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache' # 避免缓存问题
        }
    
    # 添加随机延迟
    time.sleep(random.uniform(1, 3))
    
    # 固定顺序尝试所有域名
    if not url.startswith('http'):
        # 如果相对URL，先尝试主域名
        domain_to_try = get_domain()
        base_url = f"https://{domain_to_try}"
        full_url = f"{base_url}{url if url.startswith('/') else '/' + url}"
    else:
        full_url = url
        
    # 创建一个Session以重用连接，提高效率
    session = requests.Session()
    
    # 对于每个域名尝试连接
    all_domains_to_try = BASE_DOMAINS.copy()
    tried_domains = []
    
    # 使用自定义适配器
    session.mount('https://', EOFHandlingSSLAdapter())
    
    # 设置会话级别的请求配置
    session.verify = verify
    session.headers.update(headers)
    session.timeout = timeout
    
    for attempt in range(retry * 2):  # 增加总重试次数以适应域名切换
        try:
            # 如果尝试次数超过最初设置，可能需要切换域名
            if attempt >= retry and not url.startswith('http'):
                # 切换到下一个可用域名
                if all_domains_to_try:
                    next_domain = next((d for d in all_domains_to_try if d not in tried_domains), None)
                    if next_domain:
                        tried_domains.append(next_domain)
                        base_url = f"https://{next_domain}"
                        full_url = f"{base_url}{url if url.startswith('/') else '/' + url}"
                        logger.info(f"尝试切换到新域名: {next_domain}")
                    else:
                        # 所有域名都尝试过了，放弃
                        break
            
            logger.info(f"请求URL: {full_url} (第{attempt+1}次尝试)")
            
            # 配置额外的安全选项
            ssl_options = {
                'verify': verify,
                'timeout': timeout,
                'allow_redirects': True
            }
            
            # 开启单次请求模式，每次请求后关闭连接
            session.headers.update({'Connection': 'close'})
            
            # 使用会话发起请求
            response = session.get(full_url, **ssl_options)
            
            # 如果状态码是404，立即返回，表示资源确实不存在
            if response.status_code == 404:
                logger.warning(f"资源不存在 (404): {full_url}")
                return {"status_code": 404, "response": None}
            
            # 如果请求成功，返回响应
            if response.status_code == 200:
                return {"status_code": 200, "response": response}
            
            logger.warning(f"请求失败，状态码: {response.status_code}，正在重试...")
        except (requests.exceptions.SSLError, ssl.SSLError) as e:
            # 特殊处理SSLEOFError - 意外EOF错误
            eof_error = False
            if "EOF occurred in violation of protocol" in str(e) or "UNEXPECTED_EOF_WHILE_READING" in str(e):
                eof_error = True
                logger.error(f"检测到SSL意外EOF错误: {str(e)}")
            else:
                logger.error(f"SSL错误: {str(e)}, 类型: {type(e).__name__}")
            
            # 记录更详细的SSL错误信息
            if isinstance(e, ssl.SSLError):
                logger.error(f"SSL错误详情: {e.args}")
            
            # 如果是EOF错误，增加更长的等待时间，有时候这是由于服务器正在重新加载证书
            if eof_error:
                wait_time = random.uniform(5, 10)
                logger.info(f"等待 {wait_time:.2f} 秒后重试...")
                time.sleep(wait_time)
            else:
                time.sleep(random.uniform(2, 5))
        except Exception as e:
            logger.error(f"请求出错: {str(e)}, 类型: {type(e).__name__}")
            time.sleep(random.uniform(2, 5))
    
    # 所有尝试都失败了
    logger.error(f"所有请求尝试都失败了: {url}")
    return {"status_code": -1, "response": None} 