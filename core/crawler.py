"""
缓存核心功能模块
"""
import logging
import time
import re
import traceback
import requests
import random
import ssl
import urllib.parse
import os
import json
from bs4 import BeautifulSoup
from config import BASE_DOMAINS, BASE_URL, USER_AGENTS
from utils.logging import setup_logger
from database import operations
from utils.network import make_request, get_base_url, get_domain, get_random_ua
from utils.video import download_video

logger = setup_logger(__name__)

def get_anime_list(page=1):
    """
    获取动漫列表
    
    Args:
        page: 页码，默认为1
        
    Returns:
        列表，包含动漫信息字典
    """
    logger.info(f"获取动漫列表，页码: {page}")
    
    # 构建请求URL，网站URL格式为/list或/list?page=1
    url = "/list" if page == 1 else f"/list?page={page}"
    result = make_request(url)
    
    if not result or result["status_code"] != 200 or not result["response"]:
        logger.error(f"获取动漫列表失败，页码: {page}")
        return None
    
    try:
        # 解析HTML
        html_content = result["response"].text
        logger.info(f"网页内容摘要: {html_content[:200].replace(chr(10), ' ')}...")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        anime_list = []
        
        # 找到最新更新区域
        sections = soup.select("section")
        
        for section in sections:
            # 检查是否有标题元素
            title_elem = section.select_one("h5.title")
            if not title_elem:
                continue
                
            section_title = title_elem.text.strip()
            logger.info(f"找到区域: {section_title}")
            
            # 查找该区域下的所有动漫项
            anime_items = section.select("li.col-3.mb-3")
            
            if anime_items:
                logger.info(f"在区域 '{section_title}' 找到 {len(anime_items)} 个动漫项目")
                
                # 解析每个动漫项
                for item in anime_items:
                    try:
                        # 提取信息
                        a_tag = item.select_one("a")
                        if not a_tag:
                            continue
                            
                        href = a_tag.get("href", "")
                        
                        # 从链接中提取ID，格式为/vod/数字.html
                        anime_id_match = re.search(r'/vod/(\d+)\.html', href)
                        if not anime_id_match:
                            continue
                            
                        anime_id = anime_id_match.group(1)
                        
                        # 获取标题
                        title_a_tag = item.select_one("a[title]")
                        if title_a_tag:
                            title = title_a_tag.get("title", "")
                        else:
                            title_elem = item.select_one("div.small.text-truncate")
                            title = title_elem.text.strip() if title_elem else ""
                        
                        # 获取封面图片
                        img_tag = item.select_one("img")
                        cover_url = img_tag.get("src", "") if img_tag else ""
                        
                        # 处理相对路径
                        if cover_url and cover_url.startswith("/"):
                            cover_url = f"{get_base_url()}{cover_url}"
                        
                        # 获取更新信息
                        update_tag = item.select_one("div.ep-tip.small span")
                        update_info = update_tag.text.strip() if update_tag else ""
                        
                        # 创建动漫信息字典
                        anime_info = {
                            "id": anime_id,
                            "title": title,
                            "cover_url": cover_url,
                            "update_info": update_info
                        }
                        
                        anime_list.append(anime_info)
                        logger.info(f"解析到动漫: {title}, ID: {anime_id}")
                    except Exception as e:
                        logger.error(f"解析动漫项出错: {str(e)}")
                        logger.error(traceback.format_exc())
                        continue
                
                # 如果我们找到了动漫列表，返回结果
                if anime_list:
                    logger.info(f"成功提取 {len(anime_list)} 个动漫信息")
                    return anime_list
                else:
                    # 如果主要方法失败，尝试备用选择器
                    logger.warning("使用备用选择器查找动漫列表")
                    fallback_selectors = [
                        "ul.row.gutters-1.list-unstyled li",
                        ".col-3.mb-3",
                        ".row li"
                    ]
                    
                    for selector in fallback_selectors:
                        anime_items = soup.select(selector)
                        logger.info(f"使用备用选择器 '{selector}' 找到 {len(anime_items)} 个动漫项目")
                        
                        if anime_items:
                            for item in anime_items:
                                try:
                                    # 获取链接和ID
                                    a_tags = item.select("a")
                                    for a_tag in a_tags:
                                        href = a_tag.get("href", "")
                                        if "/vod/" in href:
                                            # 找到了有效链接
                                            anime_id_match = re.search(r'/vod/(\d+)\.html', href)
                                            if not anime_id_match:
                                                continue
                                                
                                            anime_id = anime_id_match.group(1)
                                            
                                            # 获取标题
                                            title = a_tag.get("title", "")
                                            if not title:
                                                text_elem = item.select_one("div.small.text-truncate")
                                                if text_elem:
                                                    title = text_elem.text.strip()
                                            
                                            # 如果还是没有标题，从图片alt属性尝试获取
                                            if not title:
                                                img_tag = item.select_one("img")
                                                if img_tag:
                                                    title = img_tag.get("alt", "")
                                            
                                            # 获取封面图片
                                            img_tag = item.select_one("img") or a_tag.select_one("img")
                                            cover_url = img_tag.get("src", "") if img_tag else ""
                                            
                                            # 处理相对路径
                                            if cover_url and cover_url.startswith("/"):
                                                cover_url = f"{get_base_url()}{cover_url}"
                                            
                                            # 创建动漫信息字典
                                            anime_info = {
                                                "id": anime_id,
                                                "title": title,
                                                "cover_url": cover_url,
                                                "update_info": ""
                                            }
                                            
                                            anime_list.append(anime_info)
                                            logger.info(f"备用方法解析到动漫: {title}, ID: {anime_id}")
                                            break  # 找到有效链接后退出循环
                                except Exception as e:
                                    logger.error(f"备用方法解析动漫项出错: {str(e)}")
                                    logger.error(traceback.format_exc())
                                    continue
                                
                                # 如果找到了动漫项，退出循环
                                if anime_list:
                                    break
                        
                        if anime_list:
                            logger.info(f"通过备用方法成功提取 {len(anime_list)} 个动漫信息")
                            return anime_list
                            
                        # 如果还是没有找到，直接解析HTML文本
                        logger.warning("直接从HTML中解析动漫列表")
                        vod_pattern = r'href="/vod/(\d+)\.html".*?title="([^"]+)"'
                        vod_matches = re.findall(vod_pattern, html_content)
                        
                        if vod_matches:
                            for anime_id, title in vod_matches:
                                anime_info = {
                                    "id": anime_id,
                                    "title": title,
                                    "cover_url": f"{get_base_url()}/cover2/{anime_id}.jpg",  # 推测封面图URL，添加基础URL
                                    "update_info": ""
                                }
                                anime_list.append(anime_info)
                                logger.info(f"正则表达式解析到动漫: {title}, ID: {anime_id}")
                            
                            logger.info(f"通过正则表达式成功提取 {len(anime_list)} 个动漫信息")
                            return anime_list
                        
                    logger.error("所有方法都未能找到动漫列表")
                    return None
            
    except Exception as e:
        logger.error(f"解析动漫列表出错: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def extract_anime_id(href):
    """
    从链接中提取动漫ID
    
    Args:
        href: 链接字符串
        
    Returns:
        字符串，动漫ID
    """
    if not href:
        return None
        
    # 使用正则表达式从URL中提取ID
    match = re.search(r'/show/([\w\d]+)(?:\.html)?', href)
    if match:
        return match.group(1)
    return None

def get_anime_detail(anime_id):
    """
    获取动漫详情
    
    Args:
        anime_id: 动漫ID
        
    Returns:
        字典，包含动漫详情信息
    """
    logger.info(f"获取动漫详情，ID: {anime_id}")
    
    url = f"/vod/{anime_id}.html"
    result = make_request(url)
    
    if not result or result["status_code"] != 200 or not result["response"]:
        logger.error(f"获取动漫详情失败，ID: {anime_id}")
        return None
    
    try:
        # 解析HTML
        html_content = result["response"].text
        logger.info(f"网页内容摘要: {html_content[:200].replace(chr(10), ' ')}...")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 获取标题 - 从h1.names元素
        title = ""
        title_elem = soup.select_one("h1.names")
        if title_elem:
            title = title_elem.text.strip()
        
        # 如果没有找到标题，尝试其他选择器
        if not title:
            title_elems = [
                soup.select_one(".detail .title"),
                soup.select_one(".detail h1"),
                soup.select_one("h1"),
                soup.select_one("title")
            ]
            
            for elem in title_elems:
                if elem and elem.text.strip():
                    title = elem.text.strip()
                    if elem.name == "title":
                        # 从页面标题中提取动漫标题（通常格式为"标题 - 网站名"）
                        title = title.split(' - ')[0] if ' - ' in title else title
                    break
        
        # 获取封面图片 - 从.detail-poster img元素
        cover_url = ""
        cover_img = soup.select_one(".detail-poster img")
        if cover_img:
            cover_url = cover_img.get("src", "")
            # 处理相对路径
            if cover_url and cover_url.startswith("/"):
                cover_url = f"{get_base_url()}{cover_url}"
        
        # 如果没有找到封面，尝试其他选择器
        if not cover_url:
            cover_imgs = [
                soup.select_one(".col-md-auto img"),
                soup.select_one(".detail img")
            ]
            
            for img in cover_imgs:
                if img and img.has_attr("src"):
                    cover_url = img.get("src", "")
                    # 处理相对路径
                    if cover_url and cover_url.startswith("/"):
                        cover_url = f"{get_base_url()}{cover_url}"
                    break
        
        # 获取动漫信息部分 - 基于提供的DOM结构
        alias = ""
        region = ""
        year = ""
        tags = []
        
        # 从.small元素中获取基本信息
        info_div = soup.select_one(".small[style*='color: #666']")
        if info_div:
            # 获取别名
            alias_div = info_div.select_one("div.mb-2:-soup-contains('别名')")
            if alias_div:
                alias = alias_div.text.replace('别名：', '').strip()
            
            # 获取地区和年代
            info_spans = info_div.select("span:-soup-contains('地区'), span:-soup-contains('年代'), span:-soup-contains('类型')")
            for span in info_spans:
                span_text = span.text.strip()
                if '地区' in span_text:
                    region = span_text.replace('地区：', '').strip()
                elif '年代' in span_text:
                    year = span_text.replace('年代：', '').strip()
                elif '类型' in span_text:
                    # 提取类型标签
                    tag_links = span.select("a")
                    for tag_link in tag_links:
                        tag = tag_link.text.strip()
                        if tag:
                            tags.append(tag)
                    
                    # 如果没有链接，可能是纯文本标签
                    if not tag_links:
                        span_content = span_text.replace('类型：', '').strip()
                        if span_content:
                            tags = [tag.strip() for tag in span_content.split() if tag.strip()]
                            
        # 如果没找到上面的元素，尝试其他选择器
        if not (alias or region or year or tags):
            info_div = soup.select_one(".detail-left .small")
            if info_div:
                # 获取别名
                alias_divs = info_div.select("div.mb-2")
                for div in alias_divs:
                    if '别名' in div.text:
                        alias = div.text.replace('别名：', '').strip()
                        break
                
                # 获取地区和年份
                spans = info_div.select("span")
                for span in spans:
                    if '地区' in span.text:
                        region = span.text.replace('地区：', '').strip()
                    elif '年代' in span.text:
                        year = span.text.replace('年代：', '').strip()
                    elif '类型' in span.text:
                        # 提取标签信息
                        tag_links = span.select("a")
                        for tag_link in tag_links:
                            tag = tag_link.text.strip()
                            if tag:
                                tags.append(tag)
        
        # 获取更新信息
        update_info = ""
        update_div = soup.select_one("div[style*='color: red']:-soup-contains('更新')")
        if update_div:
            update_info = update_div.text.strip()
        
        # 获取描述
        description = ""
        # 首先尝试获取介绍内容，位于"动漫介绍"标签之后
        intro_tab = soup.select_one(".menu-tabs li:-soup-contains('动漫介绍')")
        if intro_tab:
            # 获取下一个div，它通常包含介绍内容
            description_div = intro_tab.find_parent("div").find_next_sibling("div")
            if description_div:
                description = description_div.text.strip()
        
        # 如果上面的方法未找到描述，尝试其他选择器
        if not description:
            desc_selectors = [
                ".detail .detail-content",
                ".desc",
                ".small[style*='line-height: 1.6em']"
            ]
            
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    description = desc_elem.text.strip()
                    break
        
        # 获取播放列表，从ep-panel中的链接
        play_list = []
        episode_items = soup.select(".ep-panel .ep-col a")
        
        for item in episode_items:
            episode_title = item.get("title", "") or item.text.strip()
            play_url = item.get("href", "")
            
            # 从URL中提取集数ID
            ep_id_match = re.search(r'ep(\d+)\.html', play_url)
            ep_id = ep_id_match.group(1) if ep_id_match else ""
            
            # 处理相对路径
            if play_url and play_url.startswith("/"):
                play_url = f"{get_base_url()}{play_url}"
            
            if play_url and episode_title:
                play_info = {
                    "episode": episode_title,
                    "url": play_url,
                    "id": ep_id
                }
                play_list.append(play_info)
        
        # 如果没有找到播放列表，尝试备用选择器
        if not play_list:
            logger.warning("使用备用方法查找播放列表")
            play_items = soup.select("div.playlist-video a") or soup.select(".play-list a")
            
            for item in play_items:
                episode_title = item.text.strip()
                play_url = item.get("href", "")
                
                # 从URL中提取集数ID
                ep_id_match = re.search(r'ep(\d+)\.html', play_url)
                ep_id = ep_id_match.group(1) if ep_id_match else ""
                
                # 处理相对路径
                if play_url and play_url.startswith("/"):
                    play_url = f"{get_base_url()}{play_url}"
                
                if play_url and episode_title:
                    play_info = {
                        "episode": episode_title,
                        "url": play_url,
                        "id": ep_id
                    }
                    play_list.append(play_info)
        
        # 如果仍然没有播放列表，尝试从HTML中提取
        if not play_list:
            play_url_pattern = r'href="(/vod-play/\d+/ep\d+\.html)"[^>]*>([^<]+)<'
            play_matches = re.findall(play_url_pattern, html_content)
            
            if play_matches:
                for url, title in play_matches:
                    # 从URL中提取集数ID
                    ep_id_match = re.search(r'ep(\d+)\.html', url)
                    ep_id = ep_id_match.group(1) if ep_id_match else ""
                    
                    play_info = {
                        "episode": title.strip(),
                        "url": f"{get_base_url()}{url}",
                        "id": ep_id
                    }
                    play_list.append(play_info)
        
        # 创建动漫详情字典
        anime_detail = {
            "id": anime_id,
            "title": title,
            "cover_url": cover_url,
            "alias": alias,
            "region": region,
            "year": year,
            "tags": tags,
            "update_info": update_info,
            "description": description,
            "play_list": play_list,
            "episode_count": len(play_list)
        }
        
        # 转换play_list为episodes以符合前端期望的格式
        episodes = []
        for item in play_list:
            episode = {
                "id": item["id"],
                "title": item["episode"],
                "url": item["url"]
            }
            episodes.append(episode)
        
        anime_detail["episodes"] = episodes
        
        logger.info(f"成功获取动漫详情: {title}, 播放列表数量: {len(play_list)}")
        return anime_detail
        
    except Exception as e:
        logger.error(f"解析动漫详情出错: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def search_anime(keyword):
    """
    搜索动漫
    
    Args:
        keyword: 搜索关键词
        
    Returns:
        列表，包含搜索结果的动漫信息字典
    """
    logger.info(f"搜索动漫，关键词: {keyword}")
    
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"/search?q={encoded_keyword}"
    result = make_request(url)
    
    if not result or result["status_code"] != 200 or not result["response"]:
        logger.error(f"搜索动漫失败，关键词: {keyword}")
        return None
    
    try:
        # 解析HTML
        html_content = result["response"].text
        logger.info(f"搜索结果网页内容摘要: {html_content[:200].replace(chr(10), ' ')}...")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        search_result = []
        
        # 尝试多种可能的选择器来处理不同的搜索结果页面布局
        selectors = [
            ".search-list li",
            "ul.row.gutters-1.list-unstyled li",
            ".col-3.mb-3",
            ".row .col-3"
        ]
        
        for selector in selectors:
            search_items = soup.select(selector)
            logger.info(f"使用选择器 '{selector}' 找到 {len(search_items)} 个搜索结果")
            
            if search_items:
                for item in search_items:
                    try:
                        a_tag = item.select_one("a[href^='/vod/']") or item.select_one("a")
                        if not a_tag:
                            continue
                            
                        href = a_tag.get("href", "")
                        # 从链接中提取ID，格式为/vod/数字.html
                        anime_id_match = re.search(r'/vod/(\d+)\.html', href)
                        if not anime_id_match:
                            continue
                            
                        anime_id = anime_id_match.group(1)
                        
                        # 获取标题
                        title = a_tag.get("title", "")
                        if not title:
                            title_elem = item.select_one("div.small.text-truncate")
                            title = title_elem.text.strip() if title_elem else ""
                        
                        # 如果还是没有标题，从图片alt属性尝试获取
                        if not title:
                            img_tag = item.select_one("img")
                            if img_tag:
                                title = img_tag.get("alt", "")
                        
                        # 获取封面图片
                        img_tag = item.select_one("img")
                        cover_url = img_tag.get("src", "") if img_tag else ""
                        
                        # 处理相对路径
                        if cover_url and cover_url.startswith("/"):
                            cover_url = f"{get_base_url()}{cover_url}"
                        
                        # 获取更新信息
                        update_tag = item.select_one("div.ep-tip.small span")
                        update_info = update_tag.text.strip() if update_tag else ""
                        
                        # 创建动漫信息字典
                        anime_info = {
                            "id": anime_id,
                            "title": title,
                            "cover_url": cover_url,
                            "update_info": update_info
                        }
                        
                        search_result.append(anime_info)
                        logger.info(f"搜索到动漫: {title}, ID: {anime_id}")
                    except Exception as e:
                        logger.error(f"解析搜索结果项出错: {str(e)}")
                        logger.error(traceback.format_exc())
                        continue
                
                # 如果找到了搜索结果，退出循环
                if search_result:
                    break
        
        # 如果仍未找到结果，尝试正则表达式方法
        if not search_result:
            logger.warning("使用正则表达式解析搜索结果")
            vod_pattern = r'href="/vod/(\d+)\.html".*?title="([^"]+)"'
            vod_matches = re.findall(vod_pattern, html_content)
            
            if vod_matches:
                for anime_id, title in vod_matches:
                    anime_info = {
                        "id": anime_id,
                        "title": title,
                        "cover_url": f"{get_base_url()}/cover2/{anime_id}.jpg",  # 推测封面图URL，添加基础URL
                        "update_info": ""
                    }
                    search_result.append(anime_info)
                    logger.info(f"通过正则表达式搜索到动漫: {title}, ID: {anime_id}")
        
        if search_result:
            logger.info(f"搜索成功，共找到 {len(search_result)} 个结果")
            return search_result
        else:
            logger.warning(f"未找到任何匹配关键词 '{keyword}' 的动漫")
            return []
    
    except Exception as e:
        logger.error(f"解析搜索结果出错: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def get_episode_video(anime_id, episode_number, task_id):
    """获取视频播放地址"""
    try:
       
        api_url = f"/_get_plays/{anime_id}/ep{episode_number}"
            
        logger.info(f"使用API URL: {api_url}")
        
        # 调用API获取视频信息
        api_result = make_request(api_url, retry=3, headers={
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': f"{get_base_url()}/vod-play/{anime_id}/ep{episode_number}.html"
        })
        
       
        if not api_result["response"]:
            logger.error(f"无法获取视频API数据: {api_url}")
            return {"status_code": 500, "url": None, "local_path": None}
            
        # 解析API响应
        try:
            api_data = api_result["response"].json()
            logger.info(f"API响应数据: {json.dumps(api_data)[:200]}")
            
            # 提取视频URL - 根据示例中的JS代码，视频数据位于video_plays数组中
            video_url = None
            
            if isinstance(api_data, dict) and 'video_plays' in api_data and isinstance(api_data['video_plays'], list):
                # 新格式：数据在video_plays数组中
                for source in api_data['video_plays']:
                    if source and isinstance(source, dict) and 'play_data' in source:
                        video_url = source['play_data']
                        logger.info(f"从video_plays中提取到视频URL: {video_url}")
                        break
            elif isinstance(api_data, list):
                # 旧格式：数据直接在数组中
                for source in api_data:
                    if source and isinstance(source, dict) and 'url' in source:
                        video_url = source['url']
                        logger.info(f"从数组中提取到视频URL: {video_url}")
                        break
            
            # 如果没有提取到视频URL，尝试从html_content中提取
            if not video_url and isinstance(api_data, dict) and 'html_content' in api_data:
                html_content = api_data['html_content']
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 查找所有的a.swa标签
                for a_tag in soup.select('a.swa'):
                    if a_tag.has_attr('href') and '/_player_x_/' in a_tag['href']:
                        # 移除前缀
                        video_url = a_tag['href'].replace('/_player_x_/', '')
                        logger.info(f"从html_content中提取到视频URL: {video_url}")
                        break
            
            if not video_url:
                logger.error(f"无法从API响应中提取视频URL")
                return {"status_code": 200, "url": None, "local_path": None}
            
            # 确保URL是完整的HTTP/HTTPS URL
            if video_url.startswith('//'):
                video_url = 'https:' + video_url
            elif not video_url.startswith('http'):
                # 如果不是完整URL，可能是相对路径，添加基础URL
                if not video_url.startswith('/'):
                    video_url = '/' + video_url
                video_url = get_base_url() + video_url
            
            logger.info(f"成功获取视频URL: {video_url}")
            
            # 下载视频到本地
            local_path = download_video(video_url, anime_id, episode_number, task_id)
            if local_path:
                # 返回本地路径作为播放地址
                return {"status_code": 200, "url": video_url, "local_path": f"/video/{anime_id}/{os.path.basename(local_path)}"}
            
            return {"status_code": 200, "url": video_url, "local_path": None}
            
        except Exception as e:
            logger.error(f"解析API响应失败: {str(e)}")
            logger.error(traceback.format_exc())
            
            # 尝试直接从iframe中提取视频URL，作为后备方案
            soup = BeautifulSoup(page_html, 'html.parser')
            
            # 尝试查找视频iframe
            iframe = soup.select_one('iframe[name="p-frame"]')
            if iframe and iframe.has_attr('src'):
                video_url = iframe['src']
                if video_url.startswith('//'):
                    video_url = 'https:' + video_url
                
                logger.info(f"从iframe中提取到视频URL: {video_url}")
                
                # 下载视频到本地
                local_path = download_video(video_url, anime_id, episode_number)
                if local_path:
                    # 返回本地路径作为播放地址
                    return {"status_code": 200, "url": video_url, "local_path": f"/video/{anime_id}/{os.path.basename(local_path)}"}
                
                return {"status_code": 200, "url": video_url, "local_path": None}
            
            return {"status_code": 500, "url": None, "local_path": None}
            
    except Exception as e:
        logger.error(f"获取视频地址失败: {str(e)}")
        logger.error(traceback.format_exc())
        return {"status_code": 500, "url": None, "local_path": None}

