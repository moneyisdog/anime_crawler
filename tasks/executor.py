"""
任务执行器模块
"""
import time
import traceback
from database import operations
from utils.logging import setup_logger
from core.crawler import get_anime_detail, get_episode_video

# 配置日志
logger = setup_logger(__name__)

def execute_task(task_id):
    """
    执行下载任务
    
    Args:
        task_id: 任务ID
    """
    try:
        # 获取任务信息
        task = operations.get_task(task_id)
        if not task:
            logger.error(f"任务 {task_id} 不存在")
            return

        logger.info(f"开始执行任务 {task_id}")
        
        # 获取动漫详情
        anime_id = task['anime_id']
        start_episode = task['start_episode']
        end_episode = task['end_episode']
        #如果是指定剧集,则直接拉取拒接详情
        #如果是非指定剧集,则拉取当前的所有剧集生成结束剧集
        if start_episode is None:
            start_episode = 1
        if end_episode is None:
            anime_detail = get_anime_detail(anime_id)
            if not anime_detail:
                logger.error(f"无法获取动漫详情: {anime_id}")
                operations.update_task_status(task_id, 'failed')
                return
                
            # 确定要下载的剧集范围
            episodes = anime_detail.get('episodes', [])
            if not episodes:
                logger.warning(f"动漫没有剧集: {anime_id}")
                operations.update_task_status(task_id, 'completed')
                return
                
            # 如果没有指定结束集数，使用最后一集
            if end_episode is None or end_episode > len(episodes):
                end_episode = len(episodes)
        # 获取动漫详情和剧集列表
       
            
        # 确保起始集数有效
        if start_episode < 1:
            start_episode = 1
       
            
        # 记录总共需要下载的剧集数
        total_episodes = end_episode - start_episode + 1
        success_count = 0
        
        # 遍历并处理每一集
        for episode_number in range(start_episode, end_episode + 1):
            
                
            logger.info(f"处理剧集: {anime_id}/{episode_number}")
            
            try:
                if operations.get_download_progress(task_id, episode_number)  == 100:
                    logger.info(f"剧集 {anime_id}/{episode_number} 已下载")
                    success_count += 1
                    continue
                # 获取视频地址
                video_info = get_episode_video(anime_id, episode_number, task_id)
                
                if not video_info or video_info.get('status_code') != 200:
                    logger.error(f"获取视频地址失败: {anime_id}/{episode_number}")
                    operations.update_download_progress(task_id, episode_number, -1)
                    continue
                    
                # 检查是否已经下载成功
                if video_info.get('local_path'):
                    logger.info(f"视频已成功下载: {video_info['local_path']}")
                    success_count += 1
                    continue
                    
                # 如果没有成功下载，记录失败状态
                logger.error(f"视频下载失败: {anime_id}/{episode_number}")
                operations.update_download_progress(task_id, episode_number, -1)
                    
            except Exception as e:
                logger.error(f"处理剧集失败: {anime_id}/{episode_number}, 错误: {str(e)}")
                logger.error(traceback.format_exc())
                operations.update_download_progress(task_id, episode_number, -1)
                
            # 避免请求频率过高
            time.sleep(3)
            
        # 根据成功率确定任务状态
        if success_count == total_episodes:
            operations.update_task_status(task_id, 'completed')
        elif success_count > 0:
            operations.update_task_status(task_id, 'partial')
        else:
            operations.update_task_status(task_id, 'failed')
            
        logger.info(f"任务执行完成: {task_id}, 总集数: {total_episodes}, 成功: {success_count}")
        
    except Exception as e:
        logger.error(f"任务 {task_id} 执行出错: {str(e)}")
        logger.error(traceback.format_exc())
        operations.update_task_status(task_id, 'failed')
    
    finally:
        # 从主应用的运行任务列表中移除
        try:
            from app import running_tasks, task_lock
            with task_lock:
                if task_id in running_tasks:
                    del running_tasks[task_id]
        except Exception as e:
            logger.error(f"清理任务状态时出错: {str(e)}")