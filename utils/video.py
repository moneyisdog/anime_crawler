"""
视频处理工具模块
"""
import os
import re
import time
import json
import shutil
import logging
import traceback
import subprocess
from urllib.parse import urlparse
import requests
from config import VIDEO_DIR, ARIA2_RPC_URL, ARIA2_RPC_TOKEN
from utils.network import get_random_ua, get_base_url
from utils.logging import setup_logger
from concurrent.futures import ThreadPoolExecutor, as_completed
from database import operations  # 添加operations模块的导入
from utils.m3u8 import M3u8Download

# 配置日志
logger = setup_logger(__name__)

def download_with_ytdlp(url, output_path, progress_callback=None):
    """使用yt-dlp下载视频
    
    Args:
        url: 视频URL
        output_path: 保存路径
        progress_callback: 进度回调函数，接收进度百分比参数
        
    Returns:
        bool: 下载是否成功
    """
    try:
        # 安装依赖提示
        try:
            import yt_dlp
        except ImportError:
            logger.error("yt-dlp未安装，请使用'pip install yt-dlp'安装此库")
            return False
            
        logger.info(f"使用yt-dlp开始下载: {url} 到 {output_path}")
        
        # 确保输出目录存在
        os.makedirs(output_path, exist_ok=True)        
        try:
            file = os.listdir(output_path)
            for item in file:
                logger.info(f"删除文件: {os.path.join(output_path, item)}")
                os.remove(os.path.join(output_path, item))
        except FileNotFoundError:
            logger.warning(f"目录不存在，将创建新目录: {output_path}")
            os.makedirs(output_path, exist_ok=True)
        
        
        class MyLogger:
            def debug(self, msg):
                if msg.startswith('[download]'):
                    # 从日志中提取进度信息
                    progress_match = re.search(r'(\d+\.\d+)%', msg)
                    if progress_match and progress_callback:
                        progress = float(progress_match.group(1))
                        progress_callback(progress)
                
            def info(self, msg):
                logger.info(msg)
                
            def warning(self, msg):
                logger.warning(msg)
                
            def error(self, msg):
                logger.error(msg)
        
        def progress_hook(d):
            if d['status'] == 'downloading':
                # 处理ANSI颜色代码：如果百分比字符串包含ANSI代码，先去除
                percent_str = d.get('_percent_str', '0%')
                # 去除ANSI颜色代码
                if '\x1b[' in percent_str:
                    # 使用正则表达式移除ANSI转义序列
                    clean_percent = re.sub(r'\x1b\[[0-9;]*m', '', percent_str)
                    percent_str = clean_percent
                
                # 提取百分比数值
                try:
                    progress = float(percent_str.replace('%', '').strip())
                except ValueError:
                    # 如果转换失败，尝试用正则提取数字
                    match = re.search(r'(\d+(\.\d+)?)', percent_str)
                    progress = float(match.group(1)) if match else 0.0
                
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                speed = d.get('speed', 0) or 0  # 修复NoneType除法错误
                eta = d.get('eta', 0) or 0  # 修复NoneType除法错误
                
                if progress_callback:
                    progress_callback(progress)
                    
                if total > 0:
                    logger.info(f"下载进度: {progress:.2f}% ({downloaded / 1024 / 1024:.2f}MB / {total / 1024 / 1024:.2f}MB) "
                               f"速度: {speed / 1024 / 1024:.2f}MB/s ETA: {eta / 60:.1f}分钟")
            
            elif d['status'] == 'finished':
                logger.info(f"下载完成: {output_path}")
        
        # 配置选项
        ydl_opts = {
            'format': 'worst',
            'outtmpl': os.path.join(output_path, '%(fragment_index)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'logger': MyLogger(),
            'progress_hooks': [progress_hook],
            # 重试次数
            'retries': 15,
            # 片段重试次数
            'fragment_retries': 15,
            # 允许HTTP错误重试
            'skip_unavailable_fragments': True,
            # 增加超时设置
            'socket_timeout': 120,  # 增加到120秒
            # 跳过SSL验证（注意：这会降低安全性）
            'nocheckcertificate': True,
            'keepvideo': True,
            'continuedl': True,
            'merge_output_format': None,            
            # 禁用控制台彩色输出，避免ANSI颜色代码导致解析错误
            'no_color': True,
            # 自定义HTTP头
            'http_headers': {
                'User-Agent': get_random_ua(),
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': get_base_url(),
            },
            # 特别为m3u8添加以下选项
            'hls_prefer_native': True,  # 使用python的原生HLS下载器而非ffmpeg
            'hls_use_mpegts': True,     # 使用MPEG-TS格式
            'buffersize': 1024*1024*8,  # 16MB缓冲区
            'N': 8  # 并行下载片段数
        }
        
        # 如果存在代理配置，添加代理
        proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
        if proxy:
            logger.info(f"使用代理: {proxy}")
            ydl_opts['proxy'] = proxy
        
        # 尝试下载
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except yt_dlp.utils.DownloadError as e:
            if "SSL" in str(e) or "handshake" in str(e) or "timeout" in str(e):
                logger.warning(f"SSL/超时错误，尝试使用不同配置重新下载...")
                # 第二次尝试：关闭SSL验证，使用不同的HTTP头
                ydl_opts.update({
                    'nocheckcertificate': True,
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    },
                    'socket_timeout': 180,  # 增加到180秒
                })
                
                # 重新尝试
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            else:
                # 其他错误，重新抛出
                raise
            
        # 检查文件是否存在和有效
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"yt-dlp下载成功: {output_path}")
            return True
        else:
            logger.error(f"yt-dlp下载失败: 文件不存在或大小为0")
            return False
            
    except Exception as e:
        logger.error(f"yt-dlp下载异常: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def download_with_ffmpeg(url, output_path, progress_callback=None):
    """使用ffmpeg下载视频流，特别适用于m3u8格式
    
    Args:
        url: 视频URL
        output_path: 输出文件路径
        progress_callback: 进度回调函数
        
    Returns:
        bool: 是否成功下载
    """
    try:
        # 尝试使用static_ffmpeg库获取ffmpeg路径
        try:
            # 尝试导入static_ffmpeg模块
            import static_ffmpeg
            
            logger.info("开始初始化static_ffmpeg，这可能需要一些时间...")
            
            # 获取ffmpeg可执行文件路径
            from static_ffmpeg import run
            
            # 获取ffmpeg路径
            ffmpeg_path, _ = run.get_or_fetch_platform_executables_else_raise()
            
            logger.info(f"使用static_ffmpeg获取到ffmpeg路径: {ffmpeg_path}")
            
        except ImportError:
            # 回退到检查系统安装的ffmpeg
            logger.warning("static_ffmpeg未安装，尝试使用系统安装的ffmpeg")
            # 检查ffmpeg-python库是否已安装
            try:
                import ffmpeg
            except ImportError:
                logger.error("ffmpeg-python库未安装。请运行: pip install ffmpeg-python")
                return False
                
            # 检查ffmpeg是否在系统中可用
            if not shutil.which('ffmpeg'):
                logger.error("未找到ffmpeg命令。请安装static_ffmpeg或确保系统ffmpeg已安装。")
                logger.error("可以运行: pip install static-ffmpeg 来安装内置ffmpeg")
                return False
                
            ffmpeg_path = 'ffmpeg'  # 使用系统路径
            
        # 防止ANSI颜色代码干扰进度解析
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        
        logger.info(f"使用ffmpeg下载: {url} 到 {output_path}")
        
        # 创建输出目录（如果不存在）
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 预检查m3u8文件
        try:
            logger.info("预检查m3u8文件...")
            response = requests.get(url, headers={'User-Agent': get_random_ua()}, timeout=10, verify=False)
            logger.info(f"m3u8文件响应状态码: {response.status_code}")
            logger.info(f"m3u8文件响应头: {dict(response.headers)}")
            
            if response.status_code != 200:
                logger.error(f"无法访问m3u8文件，状态码: {response.status_code}")
                logger.error(f"响应内容: {response.text[:500]}")  # 只记录前500个字符
                return False
                
            m3u8_content = response.text
            logger.info(f"m3u8文件内容预览: {m3u8_content[:200]}")  # 记录前200个字符
            
            if '#EXTM3U' not in m3u8_content:
                logger.error("m3u8文件格式无效")
                return False
                
            logger.info("m3u8文件预检查通过")
        except Exception as e:
            logger.error(f"预检查m3u8文件失败: {str(e)}")
            logger.error(traceback.format_exc())
            return False
            
        # 构建ffmpeg命令
        cmd = [
            ffmpeg_path,  # 使用获取到的ffmpeg路径
            '-y',  # 自动覆盖输出文件
            '-loglevel', 'debug',  # 改为debug级别以获取更多信息
            '-protocol_whitelist', 'file,http,https,tcp,tls,crypto,data',  # 允许的协议列表
            '-allowed_extensions', 'ALL',  # 允许所有扩展名
            '-reconnect', '1',
            '-reconnect_streamed', '1',
            '-reconnect_delay_max', '20',
            '-timeout', '60000000',  # 超时时间（微秒）
            '-tls_verify', '0',  # 禁用SSL验证
            '-ca_file', '',  # 不使用CA证书
            '-http_persistent', '1',  # 启用持久连接
            '-user_agent', f'"{get_random_ua()}"',  # 设置User-Agent，添加引号
            '-headers', f'Referer: {get_base_url()}',  # 设置Referer，移除\r\n
            # 添加HLS特定参数
            '-hls_time', '10',  # 设置每个分片的时长为10秒
            '-hls_list_size', '0',  # 保留所有分片
            '-hls_segment_type', 'mpegts',  # 使用MPEG-TS格式
            '-hls_flags', 'independent_segments',  # 启用独立分片
            '-i', url,  # 输入URL
            '-c', 'copy',  # 直接复制流，不重新编码
            '-bsf:a', 'aac_adtstoasc',  # 修复某些AAC音频流的问题
            '-progress', 'pipe:1',  # 输出进度信息到stdout
            '-stats',  # 显示统计信息
            '-f', 'mp4',  # 强制输出格式为mp4
            # 添加性能优化参数
            '-thread_queue_size', '1024',  # 增加线程队列大小
            '-threads', '0',  # 使用所有可用CPU线程
            '-bufsize', '8192k',  # 增加缓冲区大小
            '-max_muxing_queue_size', '1024',  # 增加复用队列大小
            '-analyzeduration', '1000000',  # 减少分析时间
            '-probesize', '1000000',  # 减少探测大小
            f'"{output_path}"'  # 输出文件路径，添加引号
        ]
        
        # 如果存在代理，添加代理设置
        proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
        if proxy:
            logger.info(f"使用代理: {proxy}")
            cmd.insert(1, '-http_proxy')
            cmd.insert(2, proxy)
        
        # 运行命令
        logger.info(f"执行ffmpeg命令: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1,  # 行缓冲
            creationflags=subprocess.CREATE_NO_WINDOW  # Windows下隐藏控制台窗口
        )
        
        # 用于解析进度的变量
        duration = 0
        out_time_ms = 0
        progress = 0
        last_progress = -1
        last_progress_time = 0
        start_time = time.time()
        timeout = 300  # 5分钟超时
        
        import select
        import threading
        from queue import Queue, Empty  # 正确导入Empty异常
        
        def read_output(pipe, queue):
            """从管道读取输出并放入队列"""
            try:
                with pipe:
                    for line in iter(pipe.readline, ''):
                        queue.put(line)
                        # 立即记录stderr输出
                        if pipe == process.stderr:
                            logger.debug(f"FFMPEG stderr: {line.strip()}")
            except Exception as e:
                logger.error(f"读取输出异常: {str(e)}")
                logger.error(traceback.format_exc())
            finally:
                queue.put(None)  # 表示结束
        
        stdout_queue = Queue()
        stderr_queue = Queue()
        
        # 启动读取线程
        threading.Thread(target=read_output, args=(process.stdout, stdout_queue), daemon=True).start()
        threading.Thread(target=read_output, args=(process.stderr, stderr_queue), daemon=True).start()
        
        stderr_output = []
        
        while process.poll() is None:  # 当进程还在运行时
            # 检查是否超时
            if time.time() - start_time > timeout:
                logger.error(f"下载超时（{timeout}秒），终止进程")
                process.terminate()
                process.wait(timeout=5)  # 等待进程结束
                if process.poll() is None:
                    process.kill()  # 如果进程还在运行，强制结束
                return False
                
            # 处理stdout
            try:
                while True:  # 尽可能多地处理队列中的数据
                    try:
                        line = stdout_queue.get_nowait()
                        if line is None:
                            break
                        
                        # 移除ANSI颜色代码
                        line = ansi_escape.sub('', line).strip()
                        
                        # 解析进度信息
                        if line.startswith('Duration:'):
                            try:
                                time_str = line.split('Duration:')[1].split(',')[0].strip()
                                h, m, s = map(float, time_str.split(':'))
                                duration = h * 3600 + m * 60 + s
                                logger.info(f"视频持续时间: {duration:.2f}秒")
                            except Exception as e:
                                logger.warning(f"解析视频时长失败: {str(e)}")
                                logger.warning(f"原始行: {line}")
                        
                        elif 'time=' in line and 'bitrate=' in line:
                            try:
                                time_part = line.split('time=')[1].split(' ')[0]
                                h, m, s = map(float, time_part.split(':'))
                                current_time = h * 3600 + m * 60 + s
                                
                                if duration > 0:
                                    progress = min(100, current_time / duration * 100)
                                    current_time = time.time()
                                    int_progress = int(progress)
                                    
                                    if (int_progress > last_progress or current_time - last_progress_time >= 5):
                                        last_progress = int_progress
                                        last_progress_time = current_time
                                        
                                        # 更新进度回调
                                        if progress_callback and int_progress > 0:
                                            progress_callback(progress)
                                            
                                        logger.info(f"下载进度: {progress:.2f}%")
                            except Exception as e:
                                logger.warning(f"解析进度失败: {str(e)}")
                                logger.warning(f"原始行: {line}")
                                
                    except Empty:  # 使用正确的Empty异常
                        break
                        
                # 处理stderr
                try:
                    while True:
                        line = stderr_queue.get_nowait()
                        if line is None:
                            break
                        line = line.strip()
                        stderr_output.append(line)
                        logger.debug(f"FFMPEG stderr: {line}")
                except Empty:  # 使用正确的Empty异常
                    pass
                    
            except Exception as e:
                logger.error(f"处理ffmpeg输出异常: {str(e)}")
                logger.error(traceback.format_exc())
                
            # 短暂休眠以避免CPU过度使用
            time.sleep(0.1)
            
        # 等待进程完成
        process.wait()
        
        # 检查是否成功
        if process.returncode == 0:
            # 确认文件已经创建并具有足够大小
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:  # 至少1KB
                logger.info(f"ffmpeg下载成功: {output_path}")
                
                # 确保进度设置为100%
                if progress_callback:
                    progress_callback(100.0)
                
                return True
            else:
                logger.error(f"ffmpeg下载异常: 输出文件大小异常 {os.path.getsize(output_path) if os.path.exists(output_path) else 'file not found'}")
                return False
        else:
            # 记录错误详情
            error_text = "\n".join(stderr_output[-20:]) if stderr_output else "未知错误"
            logger.error(f"ffmpeg下载失败: 返回码={process.returncode}, 错误={error_text}")
            
            # 如果是SSL/TLS错误，尝试使用二次尝试
            if any(("tls" in line.lower() and "error" in line.lower()) for line in stderr_output):
                logger.info("检测到SSL/TLS错误，尝试使用备用命令...")
                # 使用不同的TLS设置尝试再次下载
                try:
                    # 创建一个临时脚本文件，使用不同的TLS设置
                    temp_script = os.path.join(os.path.dirname(output_path), f"download_script_{int(time.time())}.bat")
                    with open(temp_script, 'w') as f:
                        ua = get_random_ua().replace('"', '\\"')
                        # 使用获取到的ffmpeg路径
                        f.write(f'"{ffmpeg_path}" -y -loglevel info -user_agent "{ua}" -http_proxy "" -tls_verify 0 -allowed_extensions ALL -protocol_whitelist "file,http,https,tcp,tls,crypto" -reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 60 -i "{url}" -c copy "{output_path}"')
                    
                    # 执行脚本
                    logger.info(f"执行备用下载脚本: {temp_script}")
                    alt_result = subprocess.run(temp_script, shell=True, check=False)
                    
                    # 清理临时脚本
                    try:
                        os.remove(temp_script)
                    except:
                        pass
                    
                    # 检查结果
                    if alt_result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                        logger.info(f"备用方法下载成功: {output_path}")
                        if progress_callback:
                            progress_callback(100.0)
                        return True
                    else:
                        logger.error(f"备用方法下载失败: 返回码={alt_result.returncode}")
                except Exception as e:
                    logger.error(f"备用下载方法异常: {str(e)}")
                    logger.error(traceback.format_exc())
            
            return False
            
    except Exception as e:
        logger.error(f"ffmpeg下载异常: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def download_with_aria2(url, output_path, progress_callback=None):
    """使用Aria2 RPC下载视频
    
    Args:
        url: 视频URL
        output_path: 保存路径
        progress_callback: 进度回调函数，接收进度百分比参数
        
    Returns:
        bool: 下载是否成功
        
    注意:
        Aria2本身不直接支持m3u8格式的完整下载，它只能下载m3u8索引文件，
        不会处理分片并合并成完整视频。对于m3u8格式，推荐使用ffmpeg或yt-dlp。
    """
    try:
        import time
        import uuid
        
        logger.info(f"使用Aria2 RPC开始下载: {url} 到 {output_path}")
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 构建Aria2 RPC请求
        rpc_url = ARIA2_RPC_URL
        gid = str(uuid.uuid4())
        
        # 构建请求头
        headers = {
            'User-Agent': get_random_ua(),
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': get_base_url()
        }
        header_list = [f"{key}: {value}" for key, value in headers.items()]
        
        # 构建参数
        params = {
            "dir": os.path.dirname(os.path.abspath(output_path)),
            "out": os.path.basename(output_path),
            "header": header_list,
            "allow-overwrite": "true",
            "max-connection-per-server": "16",
            "split": "16",
            "min-split-size": "1M",
            "continue": "true",
            "max-tries": "5"
        }
        
        # 如果设置了token，添加到请求中
        token_param = f"token:{ARIA2_RPC_TOKEN}" if ARIA2_RPC_TOKEN else ""
        
        # 构建RPC请求体
        rpc_data = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "aria2.addUri",
            "params": [token_param, [url], params] if token_param else [[url], params]
        }
        
        # 发送RPC请求
        response = requests.post(rpc_url, json=rpc_data)
        if response.status_code != 200:
            logger.error(f"Aria2 RPC请求失败: {response.status_code} {response.text}")
            return False
        
        response_data = response.json()
        if 'error' in response_data:
            logger.error(f"Aria2 RPC错误: {response_data['error']}")
            return False
            
        # 获取下载GID
        gid = response_data.get('result', gid)
        logger.info(f"Aria2下载已启动，GID: {gid}")
        
        # 监控下载进度
        completed = False
        retries = 0
        max_retries = 60  # 最多等待60次，每次10秒
        last_progress = -1  # 初始为-1确保首次更新
        
        while not completed and retries < max_retries:
            try:
                # 构建查询进度的RPC请求
                status_data = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "aria2.tellStatus",
                    "params": [token_param, gid] if token_param else [gid]
                }
                
                status_response = requests.post(rpc_url, json=status_data)
                status_result = status_response.json()
                
                if 'error' in status_result:
                    logger.warning(f"获取下载状态错误: {status_result['error']}")
                    retries += 1
                    time.sleep(10)
                    continue
                
                # 解析下载状态
                status = status_result.get('result', {})
                download_status = status.get('status', '')
                
                if download_status == 'complete':
                    logger.info(f"Aria2下载完成: {output_path}")
                    completed = True
                    if progress_callback:
                        progress_callback(100.0)
                    break
                elif download_status == 'error':
                    error_msg = status.get('errorMessage', 'Unknown error')
                    logger.error(f"Aria2下载错误: {error_msg}")
                    return False
                elif download_status == 'removed':
                    logger.error("Aria2下载被移除")
                    return False
                elif download_status == 'active' or download_status == 'waiting' or download_status == 'paused':
                    # 计算进度
                    total_length = int(status.get('totalLength', '0'))
                    completed_length = int(status.get('completedLength', '0'))
                    download_speed = int(status.get('downloadSpeed', '0'))
                    
                    if total_length > 0:
                        progress = (completed_length / total_length) * 100
                        int_progress = int(progress)
                        
                        # 只在进度变化时更新
                        if int_progress > last_progress:
                            last_progress = int_progress
                            
                            # 估算剩余时间
                            eta = 0
                            if download_speed > 0:
                                eta = (total_length - completed_length) / download_speed
                                
                            logger.info(f"下载进度: {progress:.2f}% ({completed_length/1024/1024:.2f}MB / {total_length/1024/1024:.2f}MB) "
                                      f"速度: {download_speed/1024/1024:.2f}MB/s ETA: {eta/60:.1f}分钟")
                                      
                            # 调用进度回调
                            if progress_callback:
                                progress_callback(progress)
                
                # 等待10秒后再次查询
                time.sleep(10)
                
                # 如果状态不是active或waiting，增加重试计数
                if download_status not in ['active', 'waiting']:
                    retries += 1
                    
            except Exception as e:
                logger.error(f"监控Aria2下载状态异常: {str(e)}")
                retries += 1
                time.sleep(10)
        
        # 检查文件是否存在和有效
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"Aria2下载成功: {output_path}")
            return True
        else:
            if retries >= max_retries:
                logger.error(f"Aria2下载超时: 达到最大重试次数 {max_retries}")
            else:
                logger.error(f"Aria2下载失败: 文件不存在或大小为0")
            return False
            
    except Exception as e:
        logger.error(f"Aria2下载异常: {str(e)}")
        logger.error(traceback.format_exc())
        return False


def download_video(video_url, anime_id, episode_number, task_id=None):
    """下载视频到本地
    
    下载策略:
    1. 使用yt-dlp下载m3u8文件
    2. 使用ffmpeg将m3u8转换为MP4
    3. 如果上述方法失败，尝试其他下载方法作为备选
    
    Args:
        video_url: 视频URL
        anime_id: 动画ID
        episode_number: 剧集号
        task_id: 任务ID
        
    Returns:
        str: 下载成功的文件路径，失败返回None
    """
    try:
        # 视频URL检查
        if not video_url or not video_url.startswith('http'):
            logger.error(f"无效的视频URL: {video_url}")
            return None
        
        # 检查是否为m3u8格式
        if '.m3u8' not in video_url.lower():
            logger.error(f"非m3u8格式视频: {video_url}")
            raise ValueError(f"目前只支持m3u8格式视频，当前URL: {video_url}")
            
        # 创建存储子目录
        anime_dir = os.path.join(VIDEO_DIR, anime_id)
        if not os.path.exists(anime_dir):
            os.makedirs(anime_dir)
            
        # 确定视频文件名（去掉可能存在的ep前缀，避免双重前缀）
        episode_id_clean = str(episode_number).replace('ep', '')
        
        # 创建m3u8目录
        m3u8_dir = os.path.join(anime_dir, f"ep{episode_id_clean}")
        output_path = os.path.join(anime_dir, f"ep{episode_id_clean}.mp4")
        
        
        # 定义进度回调函数
        def update_progress(progress):
            if task_id:
                # 转为整数进度
                int_progress = int(progress)
                # 每2%或接近完成时更新数据库
                if int_progress % 2 == 0 or int_progress >= 98:
                    operations.update_download_progress(task_id, episode_number, int_progress)
                    logger.info(f"更新下载进度: {int_progress}% - 任务={task_id}, 剧集={episode_number}")
        
        #首先尝试使用m3u8下载
        logger.info(f"尝试使用m3u8下载...{video_url} {anime_id} {episode_number} {task_id}")
        downloaer = M3u8Download(video_url, anime_id, episode_id_clean, task_id, episode_number, max_workers=64, num_retries=10)
        if downloaer._progress == 100:
            return os.path.join(f"{anime_id}", f"ep{episode_id_clean}.m3u8")
        logger.error(f"下载视频异常: {str(e)}")
        logger.error(traceback.format_exc())
        return None
        # 1. 首先尝试使用yt-dlp下载m3u8
        logger.info("尝试使用yt-dlp下载m3u8...")
        success = download_with_ytdlp(video_url, m3u8_dir, update_progress)

        if success:
            logger.info("yt-dlp下载m3u8成功，开始使用ffmpeg转换...")
            # 使用ffmpeg将m3u8转换为MP4
            try:
                from static_ffmpeg import run
                ffmpeg_path, _ = run.get_or_fetch_platform_executables_else_raise()
            except ImportError:
                if not shutil.which('ffmpeg'):
                    logger.error("未找到ffmpeg命令。请安装static_ffmpeg或确保系统ffmpeg已安装。")
                    return None
                ffmpeg_path = 'ffmpeg'
            
            # 构建ffmpeg命令
            cmd = [
                ffmpeg_path,
                '-y',
                '-i', os.path.join(m3u8_dir, 'index.m3u8'),
                '-c', 'copy',
                '-bsf:a', 'aac_adtstoasc',
                output_path
            ]
            
            # 执行ffmpeg转换
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # 等待转换完成
            _, stderr = process.communicate()
            
            if process.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info("ffmpeg转换成功")
                if task_id:
                    relative_path = os.path.join(f"{anime_id}", f"ep{episode_id_clean}.mp4")
                    file_size = os.path.getsize(output_path)
                    operations.update_download_progress(task_id, episode_number, 100, relative_path, file_size)
                    logger.info(f"更新下载进度为100%: 任务={task_id}, 剧集={episode_number}")
                return output_path
            else:
                logger.error(f"ffmpeg转换失败: {stderr}")
        
        # 2. 如果yt-dlp下载失败，尝试使用ffmpeg直接下载
        logger.warning("yt-dlp下载失败，尝试使用ffmpeg直接下载...")
        success = download_with_ffmpeg(video_url, output_path, update_progress)
        if success:
            logger.info("ffmpeg直接下载成功")
            if task_id:
                relative_path = os.path.join(f"{anime_id}", f"ep{episode_id_clean}.mp4")
                file_size = os.path.getsize(output_path)
                operations.update_download_progress(task_id, episode_number, 100, relative_path, file_size)
                logger.info(f"更新下载进度为100%: 任务={task_id}, 剧集={episode_number}")
            return output_path
        
        # 3. 如果ffmpeg直接下载失败，尝试使用Aria2
        logger.warning("ffmpeg直接下载失败，尝试使用Aria2...")
        success = download_with_aria2(video_url, output_path, update_progress)
        if success:
            logger.info("Aria2下载成功")
            if task_id:
                relative_path = os.path.join(f"{anime_id}", f"ep{episode_id_clean}.mp4")
                file_size = os.path.getsize(output_path)
                operations.update_download_progress(task_id, episode_number, 100, relative_path, file_size)
                logger.info(f"更新下载进度为100%: 任务={task_id}, 剧集={episode_number}")
            return output_path
        
        # 4. 如果所有方法都失败，使用Python requests分块下载（最后手段）
        # logger.warning("所有高级下载方法失败，尝试使用基本requests下载...")
        # logger.warning("注意: 基本requests方法不能正确处理m3u8格式，可能只会下载索引文件而非实际视频内容")
        
        # try:
        #     headers = {
        #         'User-Agent': get_random_ua(),
        #         'Accept': '*/*',
        #         'Accept-Encoding': 'gzip, deflate, br',
        #         'Connection': 'keep-alive',
        #         'Referer': get_base_url()
        #     }
            
        #     with requests.get(video_url, headers=headers, stream=True, timeout=300, verify=False) as r:
        #         r.raise_for_status()
        #         total_size = int(r.headers.get('content-length', 0))
        #         logger.info(f"视频大小: {total_size / 1024 / 1024:.2f} MB")
                
        #         # 更新数据库中的总大小信息
        #         if task_id:
        #             operations.update_download_size(task_id, episode_number, total_size)
                
        #         with open(output_path, 'wb') as f:
        #             downloaded = 0
        #             chunk_size = 1024 * 1024  # 使用1MB的块大小
        #             last_progress_update = -1
        #             last_time_update = 0
        #             start_time = time.time()
                    
        #             for chunk in r.iter_content(chunk_size=chunk_size):
        #                 if chunk:
        #                     f.write(chunk)
        #                     downloaded += len(chunk)
                            
        #                     if total_size > 0:
        #                         percent = (downloaded / total_size) * 100
        #                         current_progress = int(percent)
        #                         current_time = time.time()
                                
        #                         # 计算下载速度和估计剩余时间
        #                         elapsed_time = current_time - start_time
        #                         speed = downloaded / elapsed_time if elapsed_time > 0 else 0
        #                         eta = (total_size - downloaded) / speed if speed > 0 else 0
                                
        #                         # 更细致的日志记录：每1%或每3秒更新一次
        #                         if (current_progress > last_progress_update) or (current_time - last_time_update >= 3):
        #                             logger.info(f"下载进度: {percent:.2f}% ({downloaded / 1024 / 1024:.2f}MB / {total_size / 1024 / 1024:.2f}MB) "
        #                                       f"速度: {speed / 1024 / 1024:.2f}MB/s ETA: {eta / 60:.1f}分钟")
        #                             last_progress_update = current_progress
        #                             last_time_update = current_time
                                    
        #                             # 更新数据库中的进度
        #                             if task_id and (current_progress % 2 == 0 or current_progress >= 99):
        #                                 operations.update_download_progress(task_id, episode_number, current_progress)
        #                                 logger.info(f"更新下载进度: {current_progress}% - 任务={task_id}, 剧集={episode_number}")
            
        #     logger.info(f"视频下载完成: {output_path}")
            
        #     # 获取相对路径
        #     relative_path = os.path.join(f"{anime_id}", os.path.basename(output_path))
        #     file_size = os.path.getsize(output_path)
            
        #     # 更新数据库中的下载进度为100%和文件大小
        #     if task_id:
        #         operations.update_download_progress(task_id, episode_number, 100, relative_path, file_size)
        #         logger.info(f"更新下载完成状态: 任务={task_id}, 剧集={episode_number}, 路径={relative_path}")
            
        #     return output_path
            
        # except requests.exceptions.Timeout:
        #     logger.error(f"下载视频超时: {video_url}")
        #     if os.path.exists(output_path) and os.path.getsize(output_path) > 1024 * 1024:
        #         file_size = os.path.getsize(output_path)
        #         progress = (file_size / total_size * 100) if 'total_size' in locals() and total_size > 0 else 0
        #         logger.info(f"保留部分下载的文件: {output_path}，大小: {file_size / 1024 / 1024:.2f}MB，进度: {progress:.2f}%")
                
        #         if task_id:
        #             operations.update_download_progress(task_id, episode_number, int(progress))
        #             logger.info(f"更新部分下载进度: {int(progress)}% - 任务={task_id}, 剧集={episode_number}")
                    
        #         return output_path
                
        # except Exception as e:
        #     logger.error(f"下载视频异常: {str(e)}")
        #     logger.error(traceback.format_exc())
        logger.error(f"下载视频异常: {str(e)}")
        logger.error(traceback.format_exc())
            
    except ValueError as e:
        logger.error(str(e))
        return None
    except Exception as e:
        logger.error(f"下载视频失败: {str(e)}")
        logger.error(traceback.format_exc())
    
    # 如果所有下载方法都失败
    if task_id:
        operations.update_download_progress(task_id, episode_number, -1)
        logger.info(f"更新下载进度为失败(-1): 任务={task_id}, 剧集={episode_number}")
    return None 