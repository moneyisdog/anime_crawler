# 动漫爬取和视频下载工具

这是一个用于樱花动漫网站(https://yhdm.one/)的爬虫和视频下载工具，可以自动抓取动漫列表、详情、剧集列表，并下载视频到本地。

## 主要功能

- 抓取动漫列表、详情和剧集列表
- 自动下载视频并保存到本地
- 支持多种下载方式（yt-dlp、ffmpeg、直接下载）
- 支持多种视频格式（mp4、m3u8等）
- 提供RESTful API接口
- 支持周期性缓存任务
- 本地SQLite数据存储
- 网页端任务管理界面
- 提供视频播放功能

## 项目结构

### 核心模块
- `app.py` - Flask应用程序，提供REST API接口和网页界面
- `core/crawler.py` - 缓存核心代码，负责抓取网站数据
- `utils/video.py` - 视频下载工具，支持多种下载方式

### 数据模块
- `database/models.py` - 数据库模型和初始化函数
- `database/operations.py` - 数据库操作函数，实现数据的CRUD
- `database/__init__.py` - 数据库模块初始化

### 任务模块
- `tasks/scheduler.py` - 任务调度器，支持周期性任务
- `tasks/executor.py` - 任务执行器，运行缓存任务并下载视频

### 工具模块
- `utils/network.py` - 网络请求工具，处理HTTP请求和反爬问题
- `utils/logging.py` - 日志工具，统一日志管理
- `utils/filesystem.py` - 文件系统工具，处理文件读写

### 其他文件
- `mock_data.py` - 模拟数据生成器，用于开发和测试
- `config.py` - 配置文件，包含各种参数设置
- `setup.py` - 依赖安装脚本
- `static/` - 前端静态资源（CSS、JavaScript）
- `templates/` - 前端HTML模板
- `video/` - 下载的视频文件存储目录

## 安装与配置

### 系统要求

- Python 3.7+
- FFmpeg（可选，用于m3u8格式视频下载）
- yt-dlp（可选，用于视频下载）

### 安装步骤

1. 克隆仓库:

```bash
git clone https://github.com/moneyisdog/anime_crawler.git
cd anime_crawler
```

2. 安装Python依赖:

```bash
pip install -r requirements.txt
```

或使用安装脚本:

```bash
python setup.py
```

3. 安装FFmpeg（可选，用于m3u8格式视频下载）:

Windows:
```bash
# 下载FFmpeg，解压后添加到环境变量PATH中
```

Linux:
```bash
sudo apt-get install ffmpeg
```

macOS:
```bash
brew install ffmpeg
```

4. 安装yt-dlp（可选，用于视频下载）:

```bash
pip install yt-dlp
```

5. 配置项目:

编辑 `config.py` 文件，根据需要修改以下配置:

```python
# 基础URL配置
BASE_URL = "https://yhdm.one"
BASE_DOMAINS = ["yhdm.one"]

# 数据库配置
DB_PATH = "anime_crawler.db"

# 视频存储目录
VIDEO_DIR = "video"

# 日志配置
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_FILE = "crawler.log"
```

## 使用方法

### 启动应用

```bash
python app.py
```

默认情况下，应用会在 http://127.0.0.1:5000 上运行。

### 网页界面使用

1. 访问 http://127.0.0.1:5000 进入首页
2. 在动漫列表中搜索或浏览动漫
3. 点击动漫卡片查看详情，可选择剧集并创建下载任务
4. 在任务管理页面查看和管理下载任务
5. 点击执行按钮启动视频下载
6. 下载完成后可在任务详情页查看视频播放链接

### API使用

#### 获取动漫列表

```
GET /api/anime/list?page=1
```

参数:
- `page`: 页码，默认为1

返回示例:
```json
{
  "success": true,
  "data": [
    {
      "id": "2021644535",
      "title": "凡人修仙传：魔道争锋",
      "cover_url": "https://yhdm.one/cover2/2021644535.jpg",
      "update_info": "更新至第126集"
    }
  ]
}
```

#### 获取动漫详情

```
GET /api/anime/detail/<anime_id>
```

参数:
- `anime_id`: 动漫ID

返回示例:
```json
{
  "success": true,
  "data": {
    "id": "2021644535",
    "title": "凡人修仙传：魔道争锋",
    "cover_url": "https://yhdm.one/cover2/2021644535.jpg",
    "alias": "凡人修仙传",
    "region": "中国大陆",
    "year": "2020",
    "description": "国民级IP《凡人修仙传》动画年番来了！看机智的凡人小子韩立如何稳健发展、步步为营...",
    "episodes": [
      {
        "id": "1",
        "title": "第1集",
        "url": "https://yhdm.one/vod-play/2021644535/ep1.html"
      },
      {
        "id": "2",
        "title": "第2集",
        "url": "https://yhdm.one/vod-play/2021644535/ep2.html"
      }
    ],
    "total_episodes": 126
  }
}
```

#### 创建下载任务

```
POST /api/tasks
```

请求体:
```json
{
  "anime_id": "2021644535",
  "anime_title": "凡人修仙传：魔道争锋",
  "start_episode": 1,
  "end_episode": 5,
  "is_periodic": false,
  "daily_update_time": 0
}
```

返回示例:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "anime_id": "2021644535",
    "anime_title": "凡人修仙传：魔道争锋",
    "start_episode": 1,
    "end_episode": 5,
    "status": "pending",
    "is_periodic": false,
    "daily_update_time": 0,
    "created_at": 1711715584,
    "updated_at": 1711715584
  },
  "message": "任务创建成功"
}
```

#### 获取所有任务

```
GET /api/tasks
```

返回示例:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "anime_id": "2021644535",
      "anime_title": "凡人修仙传：魔道争锋",
      "start_episode": 1,
      "end_episode": 5,
      "status": "completed",
      "is_periodic": false,
      "daily_update_time": 0,
      "created_at": 1711715584,
      "updated_at": 1711715894
    }
  ]
}
```

#### 获取任务详情

```
GET /api/tasks/<task_id>
```

参数:
- `task_id`: 任务ID

返回示例:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "anime_id": "2021644535",
    "anime_title": "凡人修仙传：魔道争锋",
    "start_episode": 1,
    "end_episode": 5,
    "status": "completed",
    "is_periodic": false,
    "daily_update_time": 0,
    "created_at": 1711715584,
    "updated_at": 1711715894,
    "last_run": 1711715894,
    "next_run": null
  }
}
```

#### 执行任务

```
POST /api/tasks/<task_id>/execute
```

参数:
- `task_id`: 任务ID

返回示例:
```json
{
  "success": true,
  "message": "任务执行完成"
}
```

#### 删除任务

```
DELETE /api/tasks/<task_id>
```

参数:
- `task_id`: 任务ID

返回示例:
```json
{
  "success": true,
  "message": "任务已删除"
}
```

## 视频下载功能

本工具支持多种视频下载方式:

1. yt-dlp下载: 主要用于各种常见视频格式，支持断点续传和进度跟踪
2. ffmpeg下载: 专为m3u8格式视频设计，支持流媒体下载
3. 直接下载: 使用Python requests库进行常规HTTP下载

下载的视频文件默认保存在 `video/<anime_id>/` 目录下，文件命名格式为 `ep<episode_id>.<format>`。

### 下载进度跟踪

下载过程中会实时记录进度到数据库，可以通过任务详情页面查看。同时，所有下载活动都会被记录到日志文件中。

下载进度范围:
- 0-100: 正常进度百分比
- -1: 下载失败

## 高级功能

### 周期性任务

可以设置周期性任务，系统会根据设定的间隔时间自动重缓存和下载。这对于追更连载动漫非常有用。

### 反爬策略

本工具实现了多种反爬策略:
- 随机User-Agent
- 请求延迟
- 多域名轮询
- 自定义请求头
- SSL/TLS错误处理

### 下载恢复

如果下载中断，再次执行任务时会检查本地文件是否存在，如果已存在则跳过下载。

## 常见问题

1. 无法启动应用
   - 检查Python版本是否≥3.7
   - 确认所有依赖都已正确安装

2. 视频下载失败
   - 检查网络连接
   - 确认ffmpeg或yt-dlp已正确安装（对应格式需要）
   - 查看日志文件获取详细错误信息

3. m3u8格式视频无法下载
   - 确保ffmpeg已安装并添加到系统PATH

4. 数据库错误
   - 检查`anime_crawler.db`文件是否存在且未损坏
   - 如有必要，删除数据库文件让系统重新创建

## 许可证

MIT License 