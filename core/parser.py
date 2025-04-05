"""
网页解析模块
"""
import re
import json
import logging
from bs4 import BeautifulSoup
from utils.logging import setup_logger

logger = setup_logger(__name__)

def extract_video_url(html_content):
    """
    从HTML内容中提取视频URL
    
    Args:
        html_content: 网页HTML内容
        
    Returns:
        字符串，视频URL
    """
    if not html_content:
        return None
    
    try:
        # 尝试使用正则表达式查找视频URL
        # 查找PlayerBase变量中的URL
        match = re.search(r'PlayerBase\s*=\s*{\s*url\s*:\s*[\'"](.*?)[\'"]', html_content)
        if match:
            return match.group(1)
        
        # 查找player_data变量中的URL
        match = re.search(r'player_data\s*=\s*{\s*.*?\s*url\s*:\s*[\'"](.*?)[\'"]', html_content, re.DOTALL)
        if match:
            return match.group(1)
        
        # 查找m3u8链接
        match = re.search(r'src="(https?://[^"]+\.m3u8)"', html_content)
        if match:
            return match.group(1)
        
        # 查找iframe中的src
        soup = BeautifulSoup(html_content, 'html.parser')
        iframe = soup.find('iframe')
        if iframe and iframe.has_attr('src'):
            return iframe['src']
        
        # 尝试查找JSON数据
        match = re.search(r'var\s+player_data\s*=\s*({.*?});', html_content, re.DOTALL)
        if match:
            try:
                player_data = json.loads(match.group(1))
                if 'url' in player_data:
                    return player_data['url']
            except Exception as e:
                logger.error(f"解析player_data JSON出错: {str(e)}")
        
        logger.error("找不到视频URL")
        return None
    except Exception as e:
        logger.error(f"提取视频URL出错: {str(e)}")
        return None

def parse_player_page(html_content):
    """
    解析播放页面，提取视频信息
    
    Args:
        html_content: 网页HTML内容
        
    Returns:
        字典，包含视频信息
    """
    if not html_content:
        return None
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 获取视频标题
        title_tag = soup.select_one("h1.title")
        title = title_tag.text.strip() if title_tag else ""
        
        # 获取当前剧集信息
        current_ep_tag = soup.select_one("div.movurl li.active")
        current_ep = current_ep_tag.text.strip() if current_ep_tag else ""
        
        # 获取视频URL
        video_url = extract_video_url(html_content)
        
        return {
            "title": title,
            "current_episode": current_ep,
            "video_url": video_url
        }
    except Exception as e:
        logger.error(f"解析播放页面出错: {str(e)}")
        return None

def extract_m3u8_url(player_url_content):
    """
    从播放器URL页面内容中提取m3u8链接
    
    Args:
        player_url_content: 播放器页面HTML内容
        
    Returns:
        字符串，m3u8 URL
    """
    if not player_url_content:
        return None
    
    try:
        # 尝试查找m3u8链接
        match = re.search(r'var\s+urls\s*=\s*[\'"](https?://[^"\']+\.m3u8)[\'"]', player_url_content)
        if match:
            return match.group(1)
        
        # 尝试查找source标签
        soup = BeautifulSoup(player_url_content, 'html.parser')
        source = soup.find('source')
        if source and source.has_attr('src'):
            src = source['src']
            if '.m3u8' in src:
                return src
        
        # 查找video标签
        video = soup.find('video')
        if video and video.has_attr('src'):
            src = video['src']
            if '.m3u8' in src:
                return src
        
        logger.error("找不到m3u8 URL")
        return None
    except Exception as e:
        logger.error(f"提取m3u8 URL出错: {str(e)}")
        return None 