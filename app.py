"""
Flask应用主入口
"""
from flask import Flask, request, jsonify, render_template,  Response
import os
import json
import traceback
from urllib.error import HTTPError
from config import VIDEO_DIR, MOCK_DATA_DIR
from database.models import init_db
from database import operations
from utils.logging import setup_logger
from core.crawler import get_anime_list, get_anime_detail, search_anime
from tasks.scheduler import init_scheduler
import re
import mimetypes
import time
import signal
import threading
import sys

# 配置日志
logger = setup_logger(__name__)

# 创建Flask应用
app = Flask(__name__)

# 全局变量
running_tasks = {}  # 记录正在运行的任务
task_lock = threading.Lock()  # 任务锁
watchdog_timer = None  # 看门狗定时器
WATCHDOG_TIMEOUT = 300  # 看门狗超时时间（秒）
ffmpeg_initialized = False  # static_ffmpeg初始化状态标记
ffmpeg_init_lock = threading.Lock()  # static_ffmpeg初始化锁
is_shutting_down = False  # 关闭标志

def feed_watchdog():
    """重置看门狗定时器"""
    global watchdog_timer
    if watchdog_timer:
        watchdog_timer.cancel()
    watchdog_timer = threading.Timer(WATCHDOG_TIMEOUT, handle_watchdog_timeout)
    watchdog_timer.daemon = True
    watchdog_timer.start()

def handle_watchdog_timeout():
    """处理看门狗超时"""
    global is_shutting_down
    if is_shutting_down:
        return
        
    logger.warning("看门狗超时，检查运行中的任务...")
    with task_lock:
        for task_id in list(running_tasks.keys()):
            logger.warning(f"任务 {task_id} 可能已经停止响应")
            operations.update_task_status(task_id, 'terminated')
            del running_tasks[task_id]

def monitor_tasks():
    """监控任务状态的后台线程"""
    global is_shutting_down
    while not is_shutting_down:
        try:
            with task_lock:
                for task_id in list(running_tasks.keys()):
                    if is_shutting_down:
                        break
                    # 检查任务是否仍在运行
                    task = operations.get_task(task_id)
                    if task and task['status'] == 'running':
                        # 任务仍在运行，喂狗
                        feed_watchdog()
                    else:
                        # 任务已经停止，从运行列表中移除
                        logger.info(f"任务 {task_id} 已完成或停止")
                        del running_tasks[task_id]
        except Exception as e:
            if not is_shutting_down:
                logger.error(f"监控任务时出错: {str(e)}")
        
        # 每5秒检查一次
        for _ in range(5):  # 分解等待时间,便于快速响应关闭
            if is_shutting_down:
                break
            time.sleep(1)

def cleanup_tasks():
    """清理所有运行中的任务"""
    global is_shutting_down
    is_shutting_down = True
    
    logger.info("开始清理任务...")
    try:
        # 取消看门狗定时器
        if watchdog_timer:
            watchdog_timer.cancel()
        
        # 标记所有运行中的任务为终止状态
        with task_lock:
            for task_id in list(running_tasks.keys()):
                try:
                    logger.info(f"正在终止任务 {task_id}")
                    operations.update_task_status(task_id, 'terminated')
                    del running_tasks[task_id]
                except Exception as e:
                    logger.error(f"终止任务 {task_id} 时出错: {str(e)}")
                    
        logger.info("任务清理完成")
    except Exception as e:
        logger.error(f"清理任务时出错: {str(e)}")
    finally:
        # 确保程序退出
        os._exit(0)

def init_ffmpeg():
    """初始化static_ffmpeg"""
    global ffmpeg_initialized
    
    # 如果已经初始化过，直接返回
    if ffmpeg_initialized:
        return True
        
    # 使用锁确保只有一个线程进行初始化
    with ffmpeg_init_lock:
        # 双重检查，避免在等待锁的过程中被其他线程初始化
        if ffmpeg_initialized:
            return True
            
        try:
            import static_ffmpeg
            from static_ffmpeg import run
            logger.info("开始初始化static_ffmpeg，这可能需要一些时间...")
            
            # 获取ffmpeg路径
            ffmpeg_path, _ = run.get_or_fetch_platform_executables_else_raise()
            logger.info(f"static_ffmpeg初始化成功，路径: {ffmpeg_path}")
            
            # 标记初始化成功
            ffmpeg_initialized = True
            return True
        except Exception as e:
            logger.error(f"初始化static_ffmpeg失败: {str(e)}")
            return False

def init_app():
    """
    初始化应用
    - 初始化数据库
    - 检查异常终止的任务
    - 设置信号处理
    """
    try:
        # 初始化static_ffmpeg
        logger.info("正在初始化static_ffmpeg...")
        if init_ffmpeg():
            logger.info("static_ffmpeg初始化完成")
        else:
            logger.warning("static_ffmpeg初始化失败，将使用系统ffmpeg")
        
        # 初始化数据库
        init_db()
        
        # 检查并处理异常终止的任务
        try:
            # 获取所有状态为"running"的任务
            running_tasks_db = operations.get_tasks_by_status('running')
            if running_tasks_db:
                logger.warning(f"发现 {len(running_tasks_db)} 个异常终止的任务")
                for task in running_tasks_db:
                    task_id = task['id']
                    logger.info(f"将任务 {task_id} 标记为异常终止")
                    operations.update_task_status(task_id, 'terminated')
        except Exception as e:
            logger.error(f"处理异常终止任务时出错: {str(e)}")
        
        # 启动任务监控线程
        monitor_thread = threading.Thread(target=monitor_tasks)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # 设置信号处理器（只在主线程中设置）
        if threading.current_thread() is threading.main_thread():
            def signal_handler(signum, frame):
                logger.info("收到终止信号，开始清理...")
                cleanup_tasks()  # 这个函数会确保程序退出
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        
    except Exception as e:
        logger.error(f"初始化应用时出错: {str(e)}")
        sys.exit(1)

# 初始化应用
init_app()

# 添加视频文件访问路径
@app.route('/video/<path:filename>')
def serve_video(filename):
    """提供视频文件访问，支持范围请求"""
    logger.info(f"请求视频文件: {filename}")
    
    # 检查文件是否存在
    video_path = os.path.join(VIDEO_DIR, filename)
    if not os.path.exists(video_path):
        logger.error(f"视频文件不存在: {filename}")
        return "视频文件不存在", 404
    
    # 获取文件大小
    file_size = os.path.getsize(video_path)
    logger.info(f"视频文件大小: {file_size} 字节")
    
    # 基于文件内容检测真实的MIME类型
    file_ext = os.path.splitext(filename)[1].lower()
    content_type = None
    
    # 检查文件头部来判断真实类型
    try:
        with open(video_path, 'rb') as f:
            header = f.read(188)  # 读取前188个字节 (MPEG-TS包长度)
            
            # 检查MPEG-TS标记 (0x47 同步字节)
            # MPEG-TS文件通常以0x47开头，每188字节一个包
            if header[0] == 0x47 and (len(header) >= 188 and header[188-1] == 0x47):
                content_type = 'video/mp2t'
                logger.info("文件头检测为MPEG-TS格式")
            # 检查MP4文件头 (ftyp...)
            elif len(header) >= 8 and header[4:8] == b'ftyp':
                content_type = 'video/mp4'
                logger.info("文件头检测为MP4格式")
            # 检查WebM文件头 (1A 45 DF A3 - EBML开头)
            elif len(header) >= 4 and header[0:4] == b'\x1a\x45\xdf\xa3':
                content_type = 'video/webm'
                logger.info("文件头检测为WebM格式")
            # 检查Ogg文件头 (OggS...)
            elif len(header) >= 4 and header[0:4] == b'OggS':
                content_type = 'video/ogg'
                logger.info("文件头检测为Ogg格式")
            # 检查MKV文件头 (也是以EBML开头)
            elif len(header) >= 4 and header[0:4] == b'\x1a\x45\xdf\xa3':
                content_type = 'video/x-matroska'
                logger.info("文件头检测为MKV格式")
            # 检查是否为HLS流媒体 (.m3u8文本文件)
            elif len(header) >= 7 and header.startswith(b'#EXTM3U'):
                content_type = 'application/vnd.apple.mpegurl'
                logger.info("文件头检测为HLS流媒体")
            # 如果以上都不匹配，则尝试使用文件后缀判断
            else:
                # 基于文件后缀判断
                if file_ext == '.mp4':
                    content_type = 'video/mp4'
                elif file_ext == '.webm':
                    content_type = 'video/webm'
                elif file_ext == '.ogg':
                    content_type = 'video/ogg'
                elif file_ext == '.m3u8':
                    content_type = 'application/vnd.apple.mpegurl'
                elif file_ext == '.ts':
                    content_type = 'video/mp2t'
                else:
                    content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                
                logger.info(f"基于文件后缀判断为: {content_type}")
    except Exception as e:
        # 如果检测失败，回退到使用后缀判断
        logger.error(f"检测文件类型出错: {str(e)}")
        if file_ext == '.mp4':
            content_type = 'video/mp4'
        elif file_ext == '.webm':
            content_type = 'video/webm'
        elif file_ext == '.ogg':
            content_type = 'video/ogg'
        elif file_ext == '.m3u8':
            content_type = 'application/vnd.apple.mpegurl'
        elif file_ext == '.ts':
            content_type = 'video/mp2t'
        else:
            content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    
    logger.info(f"最终使用的视频文件类型: {content_type}")
    content_disposition = f'inline; filename="{os.path.basename(filename)}"'
    
    # 如果检测到MPEG-TS格式，考虑修改Content-Disposition以使用.ts扩展名
    if content_type == 'video/mp2t' and file_ext != '.ts':
        base_name = os.path.basename(filename)
        name_without_ext = os.path.splitext(base_name)[0]
        content_disposition = f'inline; filename="{name_without_ext}.ts"'
        logger.info(f"调整内容处置头为TS格式: {content_disposition}")
    
    # 处理范围请求
    range_header = request.headers.get('Range', None)
    
    # 定义流式传输的生成器函数
    def generate(start, end):
        # 增加大块读取的缓冲区
        chunk_size = 1024 * 1024  # 1MB
        
        with open(video_path, 'rb') as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                read_size = min(chunk_size, remaining)
                data = f.read(read_size)
                if not data:
                    break
                remaining -= len(data)
                yield data
    
    # 如果是范围请求
    if range_header:
        logger.info(f"处理范围请求: {range_header}")
        byte_start, byte_end = 0, file_size - 1
        
        # 解析Range头
        match = re.search(r'bytes=(\d+)-(\d*)', range_header)
        if match:
            groups = match.groups()
            if groups[0]:
                byte_start = int(groups[0])
            if groups[1]:
                byte_end = int(groups[1])
            else:
                byte_end = file_size - 1
        
        # 确保范围有效
        if byte_start >= file_size:
            logger.error(f"请求范围无效: {byte_start}-{byte_end}, 文件大小: {file_size}")
            return Response(
                status=416,  # Range Not Satisfiable
                headers={
                    'Content-Range': f'bytes */{file_size}'
                }
            )
        
        # 限制结束位置不超过文件大小
        byte_end = min(byte_end, file_size - 1)
        
        # 计算实际长度
        content_length = byte_end - byte_start + 1
        logger.info(f"返回部分内容: {byte_start}-{byte_end}/{file_size}, 大小: {content_length} 字节")
        
        # 创建响应
        resp = Response(
            generate(byte_start, byte_end),
            206,  # Partial Content
            mimetype=content_type,
            direct_passthrough=True
        )
        
        # 设置响应头
        resp.headers.add('Content-Range', f'bytes {byte_start}-{byte_end}/{file_size}')
        resp.headers.add('Accept-Ranges', 'bytes')
        resp.headers.add('Content-Length', str(content_length))
        resp.headers.add('Access-Control-Allow-Origin', '*')
        resp.headers.add('Cache-Control', 'public, max-age=86400')
        resp.headers.add('Content-Disposition', content_disposition)
        
        return resp
    
    # 不是范围请求，返回全部内容
    logger.info(f"返回完整内容: {file_size} 字节")
    resp = Response(
        generate(0, file_size - 1),
        200,
        mimetype=content_type,
        direct_passthrough=True
    )
    
    # 设置响应头
    resp.headers.add('Accept-Ranges', 'bytes')
    resp.headers.add('Content-Length', str(file_size))
    resp.headers.add('Access-Control-Allow-Origin', '*')
    resp.headers.add('Cache-Control', 'public, max-age=86400')
    resp.headers.add('Content-Disposition', content_disposition)
    
    return resp

# 初始化数据库
init_db()

# 初始化任务调度器
try:
    init_scheduler()
    logger.info("任务调度器初始化成功")
except Exception as e:
    logger.error(f"初始化任务调度器失败: {str(e)}")

def load_mock_data(filename):
    """从示例数据文件加载数据"""
    try:
        filepath = os.path.join(MOCK_DATA_DIR, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError as je:
                    logger.error(f"解析JSON文件失败 {filename}: {str(je)}")
                    return None
    except Exception as e:
        logger.error(f"加载示例数据失败: {str(e)}")
    return None

# 首页路由 - 动漫缓存器
@app.route('/', methods=['GET'])
def index():
    return render_template('crawler.html')

# API接口：获取动漫列表
@app.route('/api/anime/list', methods=['GET'])
def api_anime_list():
    page = request.args.get('page', 1, type=int)
    
    try:
        # 尝试获取真实数据
        # anime_list = get_anime_list(page)
        anime_list = None
        
        # 如果没有获取到真实数据，使用示例数据
        if not anime_list:
            logger.info("使用示例动漫列表数据")
            anime_list = load_mock_data("anime_list.json")
            if not anime_list:
                return jsonify({"error": "无法获取动漫列表"}), 500
        
        return jsonify({"success": True, "data": anime_list})
    except Exception as e:
        logger.error(f"获取动漫列表出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": f"获取动漫列表出错: {str(e)}"}), 500

# API接口：获取动漫详情和剧集列表
@app.route('/api/anime/detail/<anime_id>', methods=['GET'])
def api_anime_detail(anime_id):
    if not anime_id:
        return jsonify({"success": False, "error": "缺少参数: id"})
    
    try:
        # 尝试获取真实数据
        detail = get_anime_detail(anime_id)
        
        # 如果没有获取到真实数据，使用示例数据
        if not detail:
            # logger.info(f"使用示例动漫详情数据: {anime_id}")
            # detail = load_mock_data(f"anime_detail_{anime_id}.json")
            
            # 如果没有特定ID的示例数据，使用通用示例数据
            return jsonify({"success": False, "error": "无法获取动漫详情"}), 500
            # if not detail:
            #     generic_detail = load_mock_data("anime_detail_40001.json")
            #     if generic_detail:
            #         generic_detail["id"] = anime_id
            #         generic_detail["title"] = f"示例动漫 {anime_id}"
            #         return jsonify({"success": True, "data": generic_detail})
            #     else:
                    
        
        return jsonify({"success": True, "data": detail})
    except Exception as e:
        logger.error(f"获取动漫详情出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": f"获取动漫详情出错: {str(e)}"}), 500

# API接口：搜索动漫
@app.route('/api/anime/search', methods=['GET'])
def api_search_anime():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"success": False, "error": "缺少搜索关键词"})
    
    try:
        # 尝试搜索真实数据
        results = search_anime(query)
        
        # 如果没有获取到真实数据，使用示例数据
        if not results:
            # logger.info(f"使用示例搜索结果数据: {query}")
            # results = load_mock_data("search_results.json")
            # if not results:
                # 返回空结果
            return jsonify({"success": True, "data": []})
        
        return jsonify({"success": True, "data": results})
    except Exception as e:
        logger.error(f"搜索动漫出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": f"搜索动漫出错: {str(e)}"}), 500

# API接口：获取任务列表
@app.route('/api/tasks', methods=['GET'])
def api_tasks_list():
    try:
        # 从数据库获取任务列表
        tasks = operations.get_tasks()
        if tasks is None:
            tasks = []
            
        # 为每个任务获取动漫标题
        for task in tasks:
            anime_id = task.get('anime_id')
            if anime_id:
                anime = operations.get_anime_by_site_id(anime_id)
                if anime:
                    task['anime_title'] = anime.get('title', '未知动漫')
                else:
                    task['anime_title'] = '未知动漫'
        
        return jsonify({"success": True, "data": tasks})
    except Exception as e:
        logger.error(f"获取任务列表出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": f"获取任务列表出错: {str(e)}"}), 500

# API接口：获取任务详情
@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def api_task_detail(task_id):
    try:
        # 从数据库获取任务详情
        task = operations.get_task(task_id)
        if task is None:
            return jsonify({"success": False, "error": "任务不存在"}), 404
        
        # 获取动漫标题
        anime_id = task.get('anime_id')
        if anime_id:
            anime = operations.get_anime_by_site_id(anime_id)
            if anime:
                task['anime_title'] = anime.get('title', '未知动漫')
            else:
                task['anime_title'] = '未知动漫'
        
        return jsonify({"success": True, "data": task})
    except Exception as e:
        logger.error(f"获取任务详情出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": f"获取任务详情出错: {str(e)}"}), 500

# API接口：执行任务
@app.route('/api/tasks/<int:task_id>/execute', methods=['POST'])
def api_execute_task(task_id):
    try:
        # 获取任务信息
        task = operations.get_task(task_id)
        if task is None:
            return jsonify({"success": False, "error": "任务不存在"}), 404
        
        # 导入并调用任务执行器
        from tasks.executor import execute_task
        import threading
        
        # 将任务状态改为running
        operations.update_task_status(task_id, 'running')
        
        # 记录任务到运行列表
        with task_lock:
            running_tasks[task_id] = True
        
        # 创建新线程异步执行任务
        task_thread = threading.Thread(target=execute_task, args=(task_id,))
        task_thread.daemon = True
        task_thread.start()
        
        return jsonify({"success": True, "message": "任务已开始执行"})
    except Exception as e:
        logger.error(f"执行任务出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": f"执行任务出错: {str(e)}"}), 500

# API接口：删除任务
@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def api_delete_task(task_id):
    try:
        # 获取任务信息
        task = operations.get_task(task_id)
        if task is None:
            return jsonify({"success": False, "error": "任务不存在"}), 404
        
        # 删除任务
        if operations.delete_task(task_id):
            return jsonify({"success": True, "message": "任务已删除"})
        else:
            return jsonify({"success": False, "error": "删除任务失败"}), 500
    except Exception as e:
        logger.error(f"删除任务出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": f"删除任务出错: {str(e)}"}), 500

# API接口：创建任务
@app.route('/api/tasks', methods=['POST'])
def api_create_task():
    try:
        task_data = request.json
        if not task_data:
            return jsonify({"success": False, "error": "缺少任务数据"}), 400
        
        # 检查必要参数
        if 'anime_id' not in task_data:
            return jsonify({"success": False, "error": "缺少参数: anime_id"}), 400
        
        anime_id = task_data.get('anime_id')
        anime_title = task_data.get('anime_title', '')
        
        # 先检查数据库中是否已存在该动漫信息
        anime = operations.get_anime_by_site_id(anime_id)
        
        # 如果数据库中没有该动漫信息或标题为空，先获取动漫详情并保存
        if not anime or not anime.get('title'):
            logger.info(f"数据库中没有动漫信息或标题为空，获取动漫详情: {anime_id}")
            
            # 如果API请求提供了标题，直接使用
            if anime_title:
                # 保存基本动漫信息到数据库
                operations.save_anime(
                    site_id=anime_id, 
                    title=anime_title,
                    description='',  # 暂无描述
                    cover_url='',  # 暂无封面
                    total_episodes=task_data.get('end_episode', 0) or 0  # 使用任务结束集数作为总集数估计
                )
                logger.info(f"使用请求中提供的标题保存动漫信息: {anime_title}")
            else:
                # 尝试获取动漫详情
                try:
                    anime_detail = get_anime_detail(anime_id)
                    if anime_detail:
                        # 保存动漫信息到数据库
                        operations.save_anime(
                            site_id=anime_id,
                            title=anime_detail.get('title', f'未知动漫 {anime_id}'),
                            description=anime_detail.get('description', ''),
                            cover_url=anime_detail.get('cover_url', ''),
                            total_episodes=len(anime_detail.get('episodes', []))
                        )
                        logger.info(f"成功获取并保存动漫信息: {anime_detail.get('title')}")
                except Exception as e:
                    logger.error(f"获取动漫详情失败: {str(e)}")
                    # 保存一个基本记录，确保至少有一个标题
                    operations.save_anime(
                        site_id=anime_id,
                        title=f'未知动漫 {anime_id}',
                        description='',
                        cover_url='',
                        total_episodes=0
                    )
                    logger.info(f"保存基本动漫信息: 未知动漫 {anime_id}")
        
        # 创建任务
        task_id = operations.create_task(
            anime_id=anime_id,
            start_episode=task_data.get('start_episode', 1),
            end_episode=task_data.get('end_episode'),
            is_periodic=task_data.get('is_periodic', False),
            daily_update_time=task_data.get('daily_update_time', 0)
        )
        
        if not task_id:
            return jsonify({"success": False, "error": "创建任务失败"}), 500
        
        # 获取新创建的任务，包含动漫标题
        task = operations.get_task(task_id)
        if task:
            # 添加动漫标题
            anime = operations.get_anime_by_site_id(anime_id)
            if anime:
                task['anime_title'] = anime.get('title', '未知动漫')
            else:
                task['anime_title'] = anime_title or f'未知动漫 {anime_id}'
        
        return jsonify({"success": True, "data": task, "message": "任务创建成功"})
    except Exception as e:
        logger.error(f"创建任务出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": f"创建任务出错: {str(e)}"}), 500

# 播放页面路由
@app.route('/player', methods=['GET'])
def player_page():
    return render_template('player.html')

# API接口：获取缓存视频列表
@app.route('/api/videos/cached', methods=['GET'])
def api_cached_videos():
    try:
        # 从数据库获取已下载的视频列表
        videos = operations.get_downloaded_videos()
        if videos is None:
            videos = []
            
        return jsonify({"success": True, "data": videos})
    except Exception as e:
        logger.error(f"获取缓存视频列表失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": f"获取缓存视频列表失败: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 