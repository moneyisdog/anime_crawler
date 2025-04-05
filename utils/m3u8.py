# _*_ coding: utf-8 _*_
# _*_ author: anwenzen _*_

import os
import re
import sys
import queue
import base64
import platform
import requests
import urllib3
import subprocess
from concurrent.futures import ThreadPoolExecutor
from database import operations
from config import VIDEO_DIR
from utils.logging import setup_logger

# 配置日志
logger = setup_logger(__name__)


class ThreadPoolExecutorWithQueueSizeLimit(ThreadPoolExecutor):
    """
    实现多线程有界队列
    队列数为线程数的2倍
    """

    def __init__(self, max_workers=None, *args, **kwargs):
        super().__init__(max_workers, *args, **kwargs)
        self._work_queue = queue.Queue(max_workers * 2)


def make_sum():
    ts_num = 0
    while True:
        yield ts_num
        ts_num += 1


class M3u8Download:
    """
    :param url: 完整的m3u8文件链接 如"https://www.bilibili.com/example/index.m3u8"
    :param anime_id: 动漫id
    :param episode_id_clean: 集数
    :param task_id: 任务id
    :param episode_number: 集数
    :param max_workers: 多线程最大线程数
    :param num_retries: 重试次数
    :param base64_key: base64编码的字符串
    """

    def __init__(self, url, anime_id, episode_id_clean, task_id, episode_number, max_workers=64, num_retries=5, base64_key=None):
        self._url = url
        self._anime_id = anime_id
        self._episode_id_clean = episode_id_clean
        self._name = f"ep{self._episode_id_clean}"
        self._task_id = task_id
        self._episode_number = episode_number
        self._max_workers = max_workers
        self._num_retries = num_retries
        # VIDEO_DIR
        self._file_path = os.path.join(VIDEO_DIR,f"{self._anime_id}", f"ep{self._episode_id_clean}")
        self._short_file_path = os.path.join( f"{self._anime_id}", f"ep{self._episode_id_clean}")
        self._front_url = None
        self._ts_url_list = []
        self._success_sum = 0
        self._ts_sum = 0
        self._progress = 0
        self._key = base64.b64decode(base64_key.encode()) if base64_key else None
        self._headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) \
        AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36'}

        urllib3.disable_warnings()
        #避免下载过程出现异常
        self.delete_file()
        self.get_m3u8_info(self._url, self._num_retries)
        logger.info('Downloading: %s' % self._name, 'Save path: %s' % self._file_path, 'task_id: %s' % self._task_id, 'episode_number: %s' % self._episode_number, sep='\n')
        with ThreadPoolExecutorWithQueueSizeLimit(self._max_workers) as pool:
            for k, ts_url in enumerate(self._ts_url_list):
                pool.submit(self.download_ts, ts_url, os.path.join(self._file_path, str(k)), self._num_retries)
        if self._success_sum == self._ts_sum:
            # self.output_mp4()
            # self.delete_file()
            file_size = os.path.getsize(self._file_path + '.m3u8')
            for file in os.listdir(self._file_path):
                file_size += os.path.getsize(os.path.join(self._file_path, file))
            self._progress = 100
            operations.update_download_progress(self._task_id, self._episode_number, self._progress , self._short_file_path + '.m3u8', file_size)
            logger.info(f"Download successfully --> {self._name}")
            
        return 

    def get_m3u8_info(self, m3u8_url, num_retries):
        """
        获取m3u8信息
        """
        try:
            with requests.get(m3u8_url, timeout=(3, 30), verify=False, headers=self._headers) as res:
                self._front_url = res.url.split(res.request.path_url)[0]
                if "EXT-X-STREAM-INF" in res.text:  # 判定为顶级M3U8文件
                    for line in res.text.split('\n'):
                        if "#" in line:
                            continue
                        elif line.startswith('http'):
                            self._url = line
                        elif line.startswith('/'):
                            self._url = self._front_url + line
                        else:
                            self._url = self._url.rsplit("/", 1)[0] + '/' + line
                    self.get_m3u8_info(self._url, self._num_retries)
                else:
                    m3u8_text_str = res.text
                    self.get_ts_url(m3u8_text_str)
        except Exception as e:
            print(e)
            if num_retries > 0:
                self.get_m3u8_info(m3u8_url, num_retries - 1)

    def get_ts_url(self, m3u8_text_str):
        """
        获取每一个ts文件的链接
        """
        if not os.path.exists(self._file_path):
            os.mkdir(self._file_path)
        new_m3u8_str = ''
        ts = make_sum()
        for line in m3u8_text_str.split('\n'):
            if "#" in line:
                if "EXT-X-KEY" in line and "URI=" in line:
                    if os.path.exists(os.path.join(self._file_path, 'key')):
                        continue
                    key = self.download_key(line, 5)
                    if key:
                        new_m3u8_str += f'{key}\n'
                        continue
                new_m3u8_str += f'{line}\n'
                if "EXT-X-ENDLIST" in line:
                    break
            else:
                if line.startswith('http'):
                    self._ts_url_list.append(line)
                elif line.startswith('/'):
                    self._ts_url_list.append(self._front_url + line)
                else:
                    self._ts_url_list.append(self._url.rsplit("/", 1)[0] + '/' + line)
                # new_m3u8_str += (os.path.join(self._file_path, str(next(ts))) + '\n')
                new_m3u8_str += (os.path.join(".\\", self._name, str(next(ts))) + '.ts\n')
        self._ts_sum = next(ts)
        with open(self._file_path + '.m3u8', "wb") as f:
            if platform.system() == 'Windows':
                f.write(new_m3u8_str.encode('gbk'))
            else:
                f.write(new_m3u8_str.encode('utf-8'))

    def download_ts(self, ts_url, name, num_retries):
        """
        下载 .ts 文件
        """
        ts_url = ts_url.split('\n')[0]
        try:
            if not os.path.exists(name + '.ts' ):
                with requests.get(ts_url, stream=True, timeout=(5, 60), verify=False, headers=self._headers) as res:
                    if res.status_code == 200:
                        with open(name + '.ts', "wb") as ts:
                            for chunk in res.iter_content(chunk_size=1024):
                                if chunk:
                                    ts.write(chunk)
                        self._success_sum += 1
                        sys.stdout.write('\r[%-25s](%d/%d)' % ("*" * (100 * self._success_sum // self._ts_sum // 4),
                                                               self._success_sum, self._ts_sum))
                        sys.stdout.flush()
                        pro = int(100 * self._success_sum // self._ts_sum)
                        if(self._progress != pro):
                            self._progress = pro
                            operations.update_download_progress(self._task_id, self._episode_number, pro)
                    else:
                        self.download_ts(ts_url, name, num_retries - 1)
            else:
                self._success_sum += 1
                pro = int(100 * self._success_sum // self._ts_sum)
                if(self._progress != pro):
                    self._progress = pro
                    operations.update_download_progress(self._task_id, self._episode_number, pro)
        except Exception:
            if os.path.exists(name + '.ts'):
                os.remove(name + '.ts')
            if num_retries > 0:
                self.download_ts(ts_url, name, num_retries - 1)

    def download_key(self, key_line, num_retries):
        """
        下载key文件
        """
        mid_part = re.search(r"URI=[\'|\"].*?[\'|\"]", key_line).group()
        may_key_url = mid_part[5:-1]
        if self._key:
            with open(os.path.join(self._file_path, 'key'), 'wb') as f:
                f.write(self._key)
            return f'{key_line.split(mid_part)[0]}URI="./{self._name}/key"'
        if may_key_url.startswith('http'):
            true_key_url = may_key_url
        elif may_key_url.startswith('/'):
            true_key_url = self._front_url + may_key_url
        else:
            true_key_url = self._url.rsplit("/", 1)[0] + '/' + may_key_url
        try:
            with requests.get(true_key_url, timeout=(5, 30), verify=False, headers=self._headers) as res:
                with open(os.path.join(self._file_path, 'key'), 'wb') as f:
                    f.write(res.content)
            return f'{key_line.split(mid_part)[0]}URI="./{self._name}/key"{key_line.split(mid_part)[-1]}'
        except Exception as e:
            print(e)
            if os.path.exists(os.path.join(self._file_path, 'key')):
                os.remove(os.path.join(self._file_path, 'key'))
            print("加密视频,无法加载key,揭秘失败")
            if num_retries > 0:
                self.download_key(key_line, num_retries - 1)
                
    '''
    run cmd
    '''
    def shell_run_cmd_block(self, cmd):
        p = subprocess.Popen(cmd,
                         shell=True,
                         stdout=sys.stdout,
                         stderr=sys.stderr,
                         )
        p.wait()
        print('cmd ret=%d' % p.returncode)

    def output_mp4(self):
        """
        合并.ts文件，输出mp4格式视频，需要ffmpeg
        """
        from static_ffmpeg import run
        ffmpeg_path, _ = run.get_or_fetch_platform_executables_else_raise()
        cmd = ffmpeg_path +' -allowed_extensions ALL -i "%s.m3u8" -acodec copy -vcodec copy -f mp4 %s.mp4' % (self._file_path, self._file_path)
        # os.system(cmd)
        print(cmd)
        self.shell_run_cmd_block(cmd)

    def delete_file(self):
        file = os.listdir(self._file_path)
        for item in file:
            logger.info(f"删除文件: {os.path.join(self._file_path, item)}")
            os.remove(os.path.join(self._file_path, item))
        logger.info(f"删除文件夹: {self._file_path}")
        os.removedirs(self._file_path)
        logger.info(f"删除文件: {self._file_path + '.m3u8'}")
        os.remove(self._file_path + '.m3u8')
        
        
# def proc(url_list, name_list):
#     sta = len(url_list) == len(name_list)
#     for i, u in enumerate(url_list):
#         M3u8Download(u,
#                      name_list[i] if sta else f"{name_list[0]}{i + 1:02}",
#                      max_workers=64,
#                      num_retries=10,
#                      # base64_key='5N12sDHDVcx1Hqnagn4NJg=='
#                      )
#     exit()

# if __name__ == "__main__":
#     while True:
#         url_list = input("输入url，若同时输入多个url时要用|分开：").split('|')
#         name_list = []
#         for url in url_list:
#             name = os.path.basename(url)
#             file,ext = os.path.splitext(name)
#             name_list.append(file)
#         # 如果M3U8_URL的数量 ≠ SAVE_NAME的数量
#         # 下载一部电视剧时，只需要输入一个name就可以了
#         p = multiprocessing.Process(target=proc, args=(url_list, name_list))
#         p.start()
        
    