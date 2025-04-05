"""
任务调度器模块
"""
import threading
import time
from database import operations
from utils.logging import setup_logger
from datetime import datetime, timedelta, timezone
logger = setup_logger(__name__)

class TaskScheduler:
    """任务调度器，管理周期性任务"""
    
    def __init__(self, check_interval=60):
        """
        初始化调度器
        
        Args:
            check_interval: 检查任务的间隔(秒)
        """
        self.check_interval = check_interval
        self.is_running = False
        self.thread = None
    
    def start(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("调度器已经在运行中")
            return False
        
        self.is_running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True  # 守护线程，主程序退出时自动结束
        self.thread.start()
        logger.info("任务调度器已启动")
        return True
    
    def stop(self):
        """停止调度器"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
            self.thread = None
        logger.info("任务调度器已停止")
    
    def _run(self):
        """运行调度器主循环"""
        while self.is_running:
            try:
                self._check_pending_tasks()
            except Exception as e:
                logger.error(f"检查待执行任务时出错: {str(e)}")
            
            # 等待下一次检查
            time.sleep(self.check_interval)
    
    def _check_pending_tasks(self):
        """检查待执行的任务"""
        current_time = int(time.time())
        tz_beijing = timezone(timedelta(hours=8))
        zero_time = datetime.now(tz_beijing).replace(hour=0, minute=0, second=0, microsecond=0)
        tasks = operations.get_tasks()
        
        for task in tasks:
            if task['is_periodic'] and task['next_run'] and task['next_run'] <= current_time:
                try:
                    # 标记任务为运行中
                    operations.update_task_status(task['id'], 'running')
                    
                    # 创建新线程执行任务
                    from tasks.executor import execute_task
                    task_thread = threading.Thread(target=execute_task, args=(task['id'],))
                    task_thread.daemon = True
                    task_thread.start()
                    #今天时间已经过去了,那么制定明天计划,否则制定今天计划
                    if(current_time >= task['daily_update_time'] + 600):
                        next_run = zero_time + timedelta(days=1) + timedelta(seconds=task['daily_update_time'])
                    else:
                        next_run = zero_time + timedelta(seconds=task['daily_update_time'])
                    
                    # 更新下次运行时间
                    operations.update_task_next_run(task['id'], int(next_run.timestamp()))
                    
                    logger.info(f"已调度任务执行: {task['id']}, 下次执行时间: {next_run}")
                except Exception as e:
                    logger.error(f"调度任务执行失败: {task['id']}, 错误: {str(e)}")

# 全局调度器实例
scheduler = TaskScheduler()

def init_scheduler():
    """初始化并启动调度器"""
    return scheduler.start()

def stop_scheduler():
    """停止调度器"""
    return scheduler.stop() 