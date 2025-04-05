"""
数据库模型定义
"""
import sqlite3
import time
from config import DB_PATH
import logging

logger = logging.getLogger(__name__)

def init_db():
    """
    初始化数据库表结构
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        # 创建动漫表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS animes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            cover_url TEXT,
            total_episodes INTEGER DEFAULT 0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )
        ''')
        
        # 创建剧集表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_id INTEGER NOT NULL,
            episode_number INTEGER NOT NULL,
            title TEXT,
            video_url TEXT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            FOREIGN KEY (anime_id) REFERENCES animes (id)
        )
        ''')
        
        # 创建任务表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_id TEXT NOT NULL,
            start_episode INTEGER NOT NULL,
            end_episode INTEGER,
            -- 状态: pending(待处理), running(进行中), completed(已完成), failed(失败), terminated(异常终止)
            status TEXT DEFAULT 'pending',
            is_periodic BOOLEAN DEFAULT 0,
            daily_update_time INTEGER DEFAULT 0,
            next_run INTEGER,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )
        ''')
        
        # 创建任务结果表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            episode_number INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            cache_url TEXT,
            error_message TEXT,
            download_progress INTEGER DEFAULT 0,
            file_size INTEGER DEFAULT 0,
            file_path TEXT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        )
        ''')
        
        # 检查是否需要更新表结构（添加新字段）
        check_and_add_column(cursor, 'task_results', 'download_progress', 'INTEGER DEFAULT 0')
        check_and_add_column(cursor, 'task_results', 'file_size', 'INTEGER DEFAULT 0')
        check_and_add_column(cursor, 'task_results', 'file_path', 'TEXT')
        check_and_add_column(cursor, 'task_results', 'cache_url', 'TEXT')
        
        # 检查task表是否需要更新（添加last_run字段）
        check_and_add_column(cursor, 'tasks', 'last_run', 'INTEGER')
        
        conn.commit()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"初始化数据库失败: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

def check_and_add_column(cursor, table, column, type_def):
    """
    检查表是否有指定列，如果没有则添加
    
    Args:
        cursor: 数据库游标
        table: 表名
        column: 列名
        type_def: 列类型定义
        
    Returns:
        布尔值，表示是否添加了新列
    """
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [col[1] for col in cursor.fetchall()]
    
    if column not in columns:
        logger.info(f"为表 {table} 添加列 {column}")
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {type_def}")
        return True
    return False 