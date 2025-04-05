"""
数据库操作函数
"""
import sqlite3
import time
import logging
from config import DB_PATH
from datetime import datetime, timedelta,timezone
logger = logging.getLogger(__name__)

def save_anime(site_id, title, description, cover_url, total_episodes):
    """
    保存动漫信息到数据库
    
    Args:
        site_id: 网站上的动漫ID
        title: 标题
        description: 描述
        cover_url: 封面URL
        total_episodes: 总集数
        
    Returns:
        整数，数据库中的动漫ID
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        current_time = int(time.time())
        
        # 检查是否已存在
        cursor.execute("SELECT id FROM animes WHERE site_id = ?", (site_id,))
        result = cursor.fetchone()
        
        if result:
            # 更新现有记录
            cursor.execute("""
            UPDATE animes SET 
                title = ?, 
                description = ?, 
                cover_url = ?, 
                total_episodes = ?,
                updated_at = ?
            WHERE site_id = ?
            """, (title, description, cover_url, total_episodes, current_time, site_id))
            anime_id = result[0]
        else:
            # 插入新记录
            cursor.execute("""
            INSERT INTO animes (site_id, title, description, cover_url, total_episodes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (site_id, title, description, cover_url, total_episodes, current_time, current_time))
            anime_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return anime_id
    except Exception as e:
        logger.error(f"保存动漫信息失败: {str(e)}")
        return None

def save_episode(anime_db_id, episode_number, title, video_url):
    """
    保存剧集信息到数据库
    
    Args:
        anime_db_id: 数据库中的动漫ID
        episode_number: 剧集编号
        title: 剧集标题
        video_url: 视频URL
        
    Returns:
        整数，数据库中的剧集ID
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        current_time = int(time.time())
        
        # 检查是否已存在
        cursor.execute("""
        SELECT id FROM episodes 
        WHERE anime_id = ? AND episode_number = ?
        """, (anime_db_id, episode_number))
        result = cursor.fetchone()
        
        if result:
            # 更新现有记录
            cursor.execute("""
            UPDATE episodes SET 
                title = ?, 
                video_url = ?,
                updated_at = ?
            WHERE anime_id = ? AND episode_number = ?
            """, (title, video_url, current_time, anime_db_id, episode_number))
            episode_id = result[0]
        else:
            # 插入新记录
            cursor.execute("""
            INSERT INTO episodes (anime_id, episode_number, title, video_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (anime_db_id, episode_number, title, video_url, current_time, current_time))
            episode_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return episode_id
    except Exception as e:
        logger.error(f"保存剧集信息失败: {str(e)}")
        return None

def create_task(anime_id, start_episode, end_episode=None, is_periodic=False, daily_update_time=0):
    """
    创建缓存任务
    
    Args:
        anime_id: 动漫ID
        start_episode: 起始集数
        end_episode: 结束集数
        is_periodic: 是否周期性任务
        daily_update_time: 每日更新时间(秒)
        
    Returns:
        整数，任务ID
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        current_time = int(time.time())
        tz_beijing = timezone(timedelta(hours=8))
        zero_time = datetime.now(tz_beijing).replace(hour=0, minute=0, second=0, microsecond=0)
        today_update_time = int((zero_time + timedelta(seconds=daily_update_time)).timestamp())
        
        if(current_time >= today_update_time + 600):
            next_run = today_update_time + 86400
        else:
            next_run = today_update_time
        
        cursor.execute("""
        INSERT INTO tasks 
        (anime_id, start_episode, end_episode, is_periodic, daily_update_time, status, next_run, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            anime_id, 
            start_episode, 
            end_episode, 
            1 if is_periodic else 0, 
            daily_update_time,
            'pending',
            next_run if is_periodic else None,
            current_time,
            current_time
        ))
        
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return task_id
    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}")
        return None

def get_tasks():
    """
    获取所有任务
    
    Returns:
        列表，包含所有任务
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tasks ORDER BY updated_at DESC")
        tasks = cursor.fetchall()
        
        # 将tuple转换为dict
        column_names = [description[0] for description in cursor.description]
        result = []
        for task in tasks:
            result.append(dict(zip(column_names, task)))
        #如果动漫处于更新状态，则将动漫task_results表中所有task_id相同的记录的下载进度添加到result中
        for task in result:
            if task['status'] == 'updating':
                task['download_progress'] = get_download_progress(task['id'], task['episode_number'])
        
        conn.close()
        return result
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        return []

def get_task(task_id):
    """
    获取任务详情
    
    Args:
        task_id: 任务ID
        
    Returns:
        字典，任务详情
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task = cursor.fetchone()
        
        if not task:
            conn.close()
            return None
        
        # 将tuple转换为dict
        column_names = [description[0] for description in cursor.description]
        result = dict(zip(column_names, task))
        
        conn.close()
        return result
    except Exception as e:
        logger.error(f"获取任务详情失败: {str(e)}")
        return None

def update_task_status(task_id, status):
    """
    更新任务状态
    
    Args:
        task_id: 任务ID
        status: 新状态
        
    Returns:
        布尔值，是否成功
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        current_time = int(time.time())
        
        cursor.execute("""
        UPDATE tasks SET 
            status = ?, 
            updated_at = ?
        WHERE id = ?
        """, (status, current_time, task_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"更新任务状态失败: {str(e)}")
        return False

def update_task_next_run(task_id, next_run):
    """
    更新任务下次运行时间
    
    Args:
        task_id: 任务ID
        next_run: 下次运行时间戳
        
    Returns:
        布尔值，是否成功
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        current_time = int(time.time())
        
        cursor.execute("""
        UPDATE tasks SET 
            next_run = ?, 
            updated_at = ?
        WHERE id = ?
        """, (next_run, current_time, task_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"更新任务下次运行时间失败: {str(e)}")
        return False

def update_download_progress(task_id, episode_number, progress, file_path=None, file_size=None):
    """
    更新下载进度
    
    Args:
        task_id: 任务ID
        episode_number: 剧集编号
        progress: 进度值(0-100)
        file_path: 文件相对路径，仅在progress=100时需要
        file_size: 文件大小(字节)，仅在progress=100时需要
        
    Returns:
        布尔值，是否成功
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        print(f"更新下载进度: task_id={task_id}, episode_number={episode_number}, progress={progress}, file_path={file_path}, file_size={file_size}")
        
        current_time = int(time.time())
        
        # 检查是否存在记录
        cursor.execute("""
        SELECT id FROM task_results
        WHERE task_id = ? AND episode_number = ?
        """, (task_id, episode_number))
        
        result = cursor.fetchone()
        
        if result:
            # 下载完成时更新file_path和file_size
            if progress == 100 and file_path:
                # 生成完整的缓存URL
                cache_url = f"/video/{file_path}" if file_path else None
                
                cursor.execute("""
                UPDATE task_results SET 
                    download_progress = ?,
                    file_path = ?,
                    file_size = ?,
                    cache_url = ?,
                    updated_at = ?
                WHERE task_id = ? AND episode_number = ?
                """, (progress, file_path, file_size, cache_url, current_time, task_id, episode_number))
            else:
                # 普通进度更新
                cursor.execute("""
                UPDATE task_results SET 
                    download_progress = ?,
                    updated_at = ?
                WHERE task_id = ? AND episode_number = ?
                """, (progress, current_time, task_id, episode_number))
        else:
            # 创建新记录
            if progress == 100 and file_path:
                # 生成完整的缓存URL
                cache_url = f"/video/{file_path}" if file_path else None
                
                cursor.execute("""
                INSERT INTO task_results 
                (task_id, episode_number, status, download_progress, file_path, file_size, cache_url, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (task_id, episode_number, 'completed', progress, file_path, file_size, cache_url, current_time, current_time))
            else:
                cursor.execute("""
                INSERT INTO task_results 
                (task_id, episode_number, status, download_progress, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (task_id, episode_number, 'downloading', progress, current_time, current_time))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"更新下载进度失败: {str(e)}")
        return False

def get_anime_by_site_id(site_id):
    """
    根据站点ID获取动漫信息
    
    Args:
        site_id: 站点动漫ID
        
    Returns:
        字典，动漫信息
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM animes WHERE site_id = ?", (site_id,))
        anime = cursor.fetchone()
        
        if not anime:
            conn.close()
            return None
        
        # 将tuple转换为dict
        column_names = [description[0] for description in cursor.description]
        result = dict(zip(column_names, anime))
        
        conn.close()
        return result
    except Exception as e:
        logger.error(f"获取动漫信息失败: {str(e)}")
        return None

def delete_task(task_id):
    """
    删除任务
    
    Args:
        task_id: 任务ID
        
    Returns:
        布尔值，是否成功
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 删除任务相关的结果记录
        cursor.execute("DELETE FROM task_results WHERE task_id = ?", (task_id,))
        
        # 删除任务
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"删除任务失败: {str(e)}")
        return False

def get_download_progress(task_id, episode_number):
    """
    获取下载进度
    
    Args:
        task_id: 任务ID
        episode_number: 剧集编号
        
    Returns:
        整数，下载进度(0-100)，None表示没有记录
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT download_progress FROM task_results
        WHERE task_id = ? AND episode_number = ?
        """, (task_id, episode_number))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        return None
    except Exception as e:
        logger.error(f"获取下载进度失败: {str(e)}")
        return None

def update_download_size(task_id, episode_number, file_size):
    """
    更新下载文件大小
    
    Args:
        task_id: 任务ID
        episode_number: 剧集编号
        file_size: 文件大小(字节)
        
    Returns:
        布尔值，是否成功
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        current_time = int(time.time())
        
        # 检查是否存在记录
        cursor.execute("""
        SELECT id FROM task_results
        WHERE task_id = ? AND episode_number = ?
        """, (task_id, episode_number))
        
        result = cursor.fetchone()
        
        if result:
            # 更新已有记录
            cursor.execute("""
            UPDATE task_results SET 
                file_size = ?,
                updated_at = ?
            WHERE task_id = ? AND episode_number = ?
            """, (file_size, current_time, task_id, episode_number))
        else:
            # 创建新记录
            cursor.execute("""
            INSERT INTO task_results 
            (task_id, episode_number, status, download_progress, file_size, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (task_id, episode_number, 'downloading', 0, file_size, current_time, current_time))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"更新文件大小失败: {str(e)}")
        return False

def get_task_by_anime_id(anime_id):
    """
    根据动漫ID获取任务
    
    Args:
        anime_id: 动漫ID
        
    Returns:
        字典，最新的任务信息
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT * FROM tasks 
        WHERE anime_id = ? 
        ORDER BY created_at DESC 
        LIMIT 1
        """, (anime_id,))
        
        task = cursor.fetchone()
        
        if not task:
            conn.close()
            return None
        
        # 将tuple转换为dict
        column_names = [description[0] for description in cursor.description]
        result = dict(zip(column_names, task))
        
        conn.close()
        return result
    except Exception as e:
        logger.error(f"根据动漫ID获取任务失败: {str(e)}")
        return None

def update_task_last_run(task_id, timestamp):
    """
    更新任务最后执行时间
    
    Args:
        task_id: 任务ID
        timestamp: 时间戳
        
    Returns:
        布尔值，是否成功
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE tasks SET 
            last_run = ?,
            updated_at = ?
        WHERE id = ?
        """, (timestamp, int(time.time()), task_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"更新任务最后执行时间失败: {str(e)}")
        return False

def get_downloaded_videos():
    """
    获取已下载的视频列表
    
    Returns:
        列表，包含已下载的视频信息
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # 使用Row工厂，可以按名称访问列
        cursor = conn.cursor()
        
        # 查询已下载的视频
        # 关联task_results、animes和tasks表，获取完整的视频信息
        cursor.execute("""
        SELECT 
            tr.id, tr.task_id, tr.episode_number, tr.download_progress, tr.file_path, tr.file_size, tr.cache_url,
            t.anime_id, a.title as anime_title
        FROM 
            task_results tr
        JOIN 
            tasks t ON tr.task_id = t.id
        JOIN 
            animes a ON t.anime_id = a.site_id
        WHERE 
            tr.download_progress = 100 AND tr.file_path IS NOT NULL
        ORDER BY 
            a.title, tr.episode_number
        """)
        
        results = cursor.fetchall()
        
        # 将结果转换为字典列表
        videos = []
        for row in results:
            # 生成正确的缓存URL
            cache_url = None
            if row['file_path']:
                # 如果数据库中已有完整URL，则使用它
                if row['cache_url'] and row['cache_url'].startswith('/video/'):
                    cache_url = row['cache_url']
                else:
                    # 否则根据file_path构建URL
                    cache_url = f"/video/{row['file_path']}"
            
            videos.append({
                'id': row['id'],
                'task_id': row['task_id'],
                'anime_id': row['anime_id'],
                'anime_title': row['anime_title'],
                'episode_number': row['episode_number'],
                'cache_url': cache_url,
                'file_size': row['file_size']
            })
        
        conn.close()
        return videos
    except Exception as e:
        logger.error(f"获取已下载视频列表失败: {str(e)}")
        logger.exception(e)
        return None

def get_tasks_by_status(status):
    """
    获取指定状态的任务列表
    
    Args:
        status: 任务状态
        
    Returns:
        列表，任务列表
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT * FROM tasks 
        WHERE status = ?
        ORDER BY created_at DESC
        """, (status,))
        
        tasks = cursor.fetchall()
        
        if not tasks:
            conn.close()
            return []
            
        # 将tuple转换为dict
        column_names = [description[0] for description in cursor.description]
        result = [dict(zip(column_names, task)) for task in tasks]
        
        conn.close()
        return result
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        return [] 