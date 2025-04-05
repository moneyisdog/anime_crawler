// 全局变量
let player = null; // 播放器实例
let currentAnimeId = null; // 当前动漫ID
let currentAnimeDetail = null; // 当前动漫详情
let currentEpisodeIndex = 0; // 当前播放的集数索引
let currentEpisodeNumber = 0; // 当前播放的集数
let watchHistory = JSON.parse(localStorage.getItem('watchHistory') || '{}'); // 观看历史
let cachedVideos = []; // 缓存的视频列表

const playerConfig = {
    controls: [
        'play-large', 'play', 'progress', 'current-time', 'mute', 
        'volume', 'captions', 'settings', 'pip', 'airplay', 'fullscreen'
    ],
    autoplay: true,
    keyboard: { focused: true, global: true },
    seekTime: 10,
    tooltips: { controls: true, seek: true },
    captions: { active: true, language: 'auto', update: true },
};

// DOM元素获取函数
function getElements() {
    return {
        searchForm: document.getElementById('searchForm'), //搜索框
        largeSearchForm: document.getElementById('largeSearchForm'), //搜索框
        searchInput: document.getElementById('searchInput'), //搜索框
        largeSearchInput: document.getElementById('largeSearchInput'), //搜索框
        searchResultModal: document.getElementById('searchResultModal') ? 
                          new bootstrap.Modal(document.getElementById('searchResultModal')) : null, //搜索结果模态框
        searchResultsGrid: document.getElementById('searchResultsGrid'), //搜索结果网格
        welcomeScreen: document.getElementById('welcomeScreen'), //欢迎界面
        playerScreen: document.getElementById('playerScreen'), //播放界面
        videoSource: document.getElementById('videoSource'), //视频源
        currentEpisodeTitle: document.getElementById('currentEpisodeTitle'), //当前集数标题
        episodesList: document.getElementById('episodesList'), //集数列表
        prevEpisodeBtn: document.getElementById('prevEpisode'), //上一集按钮
        nextEpisodeBtn: document.getElementById('nextEpisode'), //下一集按钮
        toast: document.getElementById('toast') ? 
              new bootstrap.Toast(document.getElementById('toast')) : null, //提示框
        toastTitle: document.getElementById('toastTitle'), //提示框标题
        toastMessage: document.getElementById('toastMessage'), //提示框消息
        cachedVideosContainer: document.getElementById('cachedVideosContainer'), //缓存视频容器
    };
}

// 全局DOM元素引用
let domElements = {};

// 初始化函数
function init() {
    try {
        // 初始化DOM元素引用
        domElements = getElements();
        
        // 检查必要的DOM元素是否存在
        if (document.getElementById('player')) {
            initPlayer();
        } else {
            console.warn('播放器元素不存在，跳过播放器初始化');
        }
        
        // 无论如何都初始化事件监听器，因为我们已经增加了存在性检查
        initEventListeners();
        
        // 检查是否存在缓存视频容器
        if (domElements.cachedVideosContainer) {
            loadCachedVideos(); // 加载缓存的视频列表
        } else {
            console.warn('缓存视频容器不存在，跳过加载缓存视频');
        }
    } catch (error) {
        console.error('初始化过程中发生错误:', error);
    }
}

// 初始化播放器
function initPlayer() {
    // 使用已有的 video 元素
    const videoElement = document.getElementById('player');
    if (!videoElement) {
        console.error('找不到播放器元素');
        return;
    }

    // 初始化播放器
    player = new Plyr(videoElement, playerConfig);
    
    // 监听播放器就绪事件
    player.on('ready', () => {
        console.log('播放器已就绪');
        // 确保视频元素填充整个容器
        if (videoElement) {
            videoElement.style.width = '100%';
            videoElement.style.height = '100%';
        }
    });
    
    // 监听播放结束事件
    player.on('ended', () => {
        console.log('播放结束', currentAnimeId, currentEpisodeNumber, currentAnimeDetail);
        cachedVideos.forEach(video => {
            if(currentAnimeId == video.anime_id){
                if(currentEpisodeNumber == video.episode_number + 1){
                    playCachedVideo(currentAnimeId, video.episode_number, video.cache_url);
                }
            }
        });
    });
    
    // 监听播放时间更新
    player.on('timeupdate', () => {
        if (!currentAnimeId || !currentAnimeDetail) return;
        
        // 如果播放超过30秒，记录为已观看
        if (player.currentTime > 30) {
            const episodeId = currentAnimeDetail.episodes[currentEpisodeIndex].id;
            if (!watchHistory[currentAnimeId]) {
                watchHistory[currentAnimeId] = { episodes: {} };
            }
            
            if (!watchHistory[currentAnimeId].episodes[episodeId]) {
                watchHistory[currentAnimeId].episodes[episodeId] = {
                    watched: true,
                    timestamp: Date.now()
                };
                
                // 保存到 localStorage
                localStorage.setItem('watchHistory', JSON.stringify(watchHistory));
            }
        }
    });
    
    // 添加错误处理
    player.on('error', (error) => {
        console.error('播放器错误:', error);
        showMessage('错误', `视频播放失败，错误信息: ${error.detail || '未知错误'}`);
    });
}

// 初始化事件监听
function initEventListeners() {
    // 移除已存在的事件监听（以防止重复绑定）
    if (domElements.searchForm) {
        domElements.searchForm.removeEventListener('submit', performSearch);
        domElements.searchForm.addEventListener('submit', performSearch);
    }
    
    if (domElements.largeSearchForm) {
        domElements.largeSearchForm.removeEventListener('submit', performSearch);
        domElements.largeSearchForm.addEventListener('submit', performSearch);
    }
    
    // 同步两个搜索框的值
    if (domElements.searchInput && domElements.largeSearchInput) {
        domElements.searchInput.addEventListener('input', () => {
            domElements.largeSearchInput.value = domElements.searchInput.value;
        });
        
        domElements.largeSearchInput.addEventListener('input', () => {
            domElements.searchInput.value = domElements.largeSearchInput.value;
        });
    }
    
  
    
    // 上一集按钮
    if (domElements.prevEpisodeBtn) {
        domElements.prevEpisodeBtn.addEventListener('click', function() {
            console.log('上一集按钮点击',currentAnimeId,currentEpisodeNumber, currentAnimeDetail);
            if (currentEpisodeNumber > 0) {
                cachedVideos.forEach(video => {
                    if(currentAnimeId == video.anime_id){
                        if(currentEpisodeNumber == video.episode_number + 1){
                            playCachedVideo(currentAnimeId, video.episode_number, video.cache_url);
                        }
                    }
                });
                
            } else {
                showMessage('提示', '已经是第一集');
            }
        });
    }else{
        console.log('上一集按钮不存在');
    }
    
    // 下一集按钮
    if (domElements.nextEpisodeBtn) {
        domElements.nextEpisodeBtn.addEventListener('click', function() {
            console.log('下一集按钮点击',currentAnimeId,currentEpisodeNumber, currentAnimeDetail);
           
                cachedVideos.forEach(video => {
                    if(currentAnimeId == video.anime_id){
                        if(currentEpisodeNumber == video.episode_number - 1){
                            playCachedVideo(currentAnimeId, video.episode_number, video.cache_url);
                        }
                    }
                });
        });
    }else{
        console.log('下一集按钮不存在');
    }
    
    
    // 监听视频类型更新事件
    document.addEventListener('videoTypeUpdated', function(e) {
        console.log('收到视频类型更新事件:', e.detail);
        
        const { url, type, isTS } = e.detail;
        
        // 检查当前是否正在播放该URL的视频
        if (currentAnimeDetail && currentAnimeDetail.episodes && 
            currentEpisodeIndex < currentAnimeDetail.episodes.length) {
            
            const episode = currentAnimeDetail.episodes[currentEpisodeIndex];
            let currentVideoUrl = episode.url || '';
            
            // 确保有完整的URL进行比较
            if (currentVideoUrl && !currentVideoUrl.startsWith('http') && !currentVideoUrl.startsWith('/')) {
                currentVideoUrl = '/' + currentVideoUrl;
            }
            
            // 如果是当前正在播放的视频
            if (currentVideoUrl === url) {
                console.log('当前正在播放的视频类型更新为:', type);
                
                // 如果实际上是TS格式但显示为MP4
                if (isTS && type === 'video/mp2t') {
                    console.log('检测到实际是TS格式视频，需要切换播放模式');
                    
                    // 如果播放器已初始化
                    if (player) {
                        // 停止当前播放器
                        player.pause();
                        
                        // 显示提示
                        showMessage('提示', '检测到TS格式视频，正在切换播放模式...');
                        
                        // 延迟切换，让用户看到提示
                        setTimeout(() => {
                            // 重新播放，使用TS格式特定处理
                            tryFallbackPlayer(url, e.detail);
                        }, 1000);
                    }
                }
            }
        }
    });
}

// 加载缓存的视频列表
function loadCachedVideos() {
    fetch('/api/videos/cached')
        .then(response => {
            if (!response.ok) {
                throw new Error('获取缓存视频列表失败');
            }
            return response.json();
        })
        .then(data => {
            console.log('获取到的缓存视频数据:', data);
            
            if (data.success && data.data) {
                cachedVideos = data.data;
                console.log('缓存视频列表:', cachedVideos);
                renderCachedVideos();
            } else {
                console.error('无法获取缓存视频数据:', data);
                if (domElements.cachedVideosContainer) {
                    domElements.cachedVideosContainer.innerHTML = `
                        <div class="text-center p-4 text-muted">
                            <i class="bi bi-exclamation-circle"></i>
                            <p class="mt-2">获取缓存视频失败，服务器返回无效数据</p>
                            <button class="btn btn-primary btn-sm mt-2" onclick="loadCachedVideos()">重新加载</button>
                        </div>
                    `;
                }
            }
        })
        .catch(error => {
            console.error('加载缓存视频失败:', error);
            showMessage('错误', '加载缓存视频列表失败');
            if (domElements.cachedVideosContainer) {
                domElements.cachedVideosContainer.innerHTML = `
                    <div class="text-center p-4 text-muted">
                        <i class="bi bi-exclamation-circle text-danger"></i>
                        <p class="mt-2">加载缓存视频失败: ${error.message}</p>
                        <button class="btn btn-primary btn-sm mt-2" onclick="loadCachedVideos()">重新加载</button>
                    </div>
                `;
            }
        });
}

// 渲染缓存的视频列表
function renderCachedVideos() {
    if (!domElements.cachedVideosContainer) {
        console.error('无法找到缓存视频容器元素');
        return;
    }
    
    if (!cachedVideos || cachedVideos.length === 0) {
        domElements.cachedVideosContainer.innerHTML = `
            <div class="text-center p-4 text-muted">
                <i class="bi bi-exclamation-circle"></i>
                <p class="mt-2">暂无缓存视频，请先搜索并缓存视频</p>
                <button class="btn btn-outline-primary btn-sm mt-2" onclick="loadCachedVideos()">刷新列表</button>
            </div>
        `;
        return;
    }
    
    console.log(`渲染 ${cachedVideos.length} 个缓存视频`);
    
    // 按动漫分组视频
    const groupedVideos = {};
    cachedVideos.forEach(video => {
        console.log('处理视频:', video);
        
        // 确保anime_id存在
        const animeId = video.anime_id || 'unknown';
        
        if (!groupedVideos[animeId]) {
            groupedVideos[animeId] = {
                title: video.anime_title || `动漫 ${animeId}`,
                episodes: []
            };
        }
        groupedVideos[animeId].episodes.push(video);
    });
    
    let html = '';
    for (const animeId in groupedVideos) {
        const anime = groupedVideos[animeId];
        html += `
            <div class="cached-anime-card mb-4">
                <h5 class="cached-anime-title">${anime.title}</h5>
                <div class="cached-episodes-grid">
        `;
        
        anime.episodes.forEach(episode => {
            // 打印调试信息
            console.log('视频地址:', episode.cache_url);
            
            html += `
                <div class="cached-episode-item" 
                     data-anime-id="${animeId}" 
                     data-episode-number="${episode.episode_number}"
                     data-video-url="${episode.cache_url}"
                     onclick="playCachedVideo('${animeId}', '${episode.episode_number}', '${episode.cache_url}')"
                     >
                    第${episode.episode_number}集
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    }
    
    domElements.cachedVideosContainer.innerHTML = html;
}

// 播放缓存的视频
function playCachedVideo(animeId, episodeNumber, videoUrl) {
    console.log('播放缓存视频:', animeId, episodeNumber, videoUrl);
    
    // 显示播放界面
    domElements.welcomeScreen.style.display = 'none';
    domElements.playerScreen.style.display = 'block';
    
    // 创建简单的动漫详情对象
    const anime = cachedVideos.find(v => v.anime_id === animeId);
    currentAnimeId = animeId;
    currentAnimeDetail = {
        id: animeId,
        title: anime ? anime.anime_title : `动漫 ${animeId}`,
        episodes: [{ id: episodeNumber, title: `第${episodeNumber}集`, url: videoUrl }]
    };
    
    currentEpisodeIndex = 0;
    currentEpisodeNumber = episodeNumber;
    
    // 更新视频源 - 确保URL是完整的
    let fullVideoUrl = videoUrl;
    if (videoUrl && !videoUrl.startsWith('http') && !videoUrl.startsWith('/')) {
        fullVideoUrl = '/' + videoUrl;
    }
    
    console.log('设置视频源:', fullVideoUrl);
    
    // 判断视频类型 - 不仅仅依靠后缀名
    let videoType = detectVideoFormat(fullVideoUrl);
    console.log('检测到视频类型:', videoType);
    
    // 更新所有视频源标签
    const videoSource = document.getElementById('videoSource');
    const videoSourceWebm = document.getElementById('videoSourceWebm');
    const videoSourceOgg = document.getElementById('videoSourceOgg');
    
    if (videoSource) {
        videoSource.src = fullVideoUrl;
        videoSource.type = videoType.type;
    }
    
    // 只有非HLS/TS才设置其他格式源
    if (!videoType.isHLS && !videoType.isDASH && !videoType.isTS) {
        // 如果是普通格式，尝试设置其他格式
        const baseName = fullVideoUrl.substring(0, fullVideoUrl.lastIndexOf('.'));
        
        if (videoSourceWebm) {
            videoSourceWebm.src = `${baseName}.webm`;
        }
        
        if (videoSourceOgg) {
            videoSourceOgg.src = `${baseName}.ogg`;
        }
    } else {
        // HLS/TS/DASH格式，清空其他源
        if (videoSourceWebm) videoSourceWebm.src = '';
        if (videoSourceOgg) videoSourceOgg.src = '';
    }
    
    
    // 释放之前的播放器实例
    if (player) {
        player.destroy();
    }
    
    // 确保视频元素存在且重置
    const videoElement = document.getElementById('player');
    if (videoElement) {
        // 重置视频元素
        videoElement.innerHTML = '';
        videoElement.load();
    }
    
   
    // 对于TS格式，立即使用原生播放器
    if (videoType.isTS) {
        console.log('检测到TS格式视频，直接使用原生播放器');
        tryFallbackPlayer(fullVideoUrl, videoType);
        return; // 提前返回
    }
    
    // 对于HLS格式，总是尝试使用hls.js
    if (videoType.isHLS) {
        // 检查是否已加载hls.js
        if (window.Hls && Hls.isSupported()) {
            console.log('使用HLS.js播放HLS格式');
            
            // 创建新的HLS实例
            const hls = new Hls({
                maxBufferLength: 30,
                maxMaxBufferLength: 60,
                enableWorker: true,
                lowLatencyMode: false,
                enableSoftwareAES: true,
                startLevel: -1,
                abrEwmaDefaultEstimate: 500000,
                manifestLoadingTimeOut: 10000,
                manifestLoadingMaxRetry: 3,
                manifestLoadingRetryDelay: 1000,
                levelLoadingTimeOut: 10000,
                levelLoadingMaxRetry: 3,
                levelLoadingRetryDelay: 1000,
                fragLoadingTimeOut: 20000,
                fragLoadingMaxRetry: 3,
                fragLoadingRetryDelay: 1000,
                startFragPrefetch: true,
                testBandwidth: true,
                progressive: true,
                lowLatencyMode: false,
                backBufferLength: 90
            });
            
            hls.loadSource(fullVideoUrl);
            hls.attachMedia(videoElement);
            
            // 在HLS实例创建后添加格式检测
            hls.on(Hls.Events.MANIFEST_PARSED, function() {
                console.log('HLS清单已解析');
                
                // 检查视频编码格式
                const videoElement = document.getElementById('player');
                if (videoElement) {
                    const videoTrack = videoElement.videoTracks && videoElement.videoTracks[0];
                    if (videoTrack) {
                        console.log('视频轨道信息:', videoTrack);
                    }
                  
                }
                
                // 创建播放器
                player = new Plyr(videoElement, playerConfig);
                // console.log("videoElement",videoElement)
                
                // 更新UI
                updatePlayerUI(episodeNumber);
                player.on('ended', () => {
                    // 自动播放下一集
                    console.log('播放结束',currentAnimeId,currentEpisodeNumber, currentAnimeDetail);
                    cachedVideos.forEach(video => {
                        if(currentAnimeId == video.anime_id){
                            if(currentEpisodeNumber == video.episode_number - 1){
                                playCachedVideo(currentAnimeId, video.episode_number, video.cache_url);
                            }
                        }
                    });
                });
                
                // 尝试播放
                videoElement.play().catch(err => {
                    console.warn('HLS自动播放失败:', err);
                    showMessage('提示', '点击视频开始播放');
                });
            });
            
            hls.on(Hls.Events.ERROR, function(event, data) {
                console.error('HLS错误:', data);
                if (data.fatal) {
                    switch(data.type) {
                        case Hls.ErrorTypes.NETWORK_ERROR:
                            console.error('HLS网络错误，尝试恢复');
                            hls.startLoad();
                            break;
                        case Hls.ErrorTypes.MEDIA_ERROR:
                            console.error('HLS媒体错误，尝试恢复');
                            hls.recoverMediaError();
                            break;
                        default:
                            // 无法恢复的错误
                            console.error('HLS致命错误，切换到原生播放器');
                            hls.destroy();
                            tryFallbackPlayer(fullVideoUrl);
                            break;
                    }
                } else {
                    // 非致命错误，记录详细信息
                    console.warn('HLS非致命错误:', {
                        type: data.type,
                        details: data.details,
                        fatal: data.fatal,
                        url: data.url
                    });
                }
            });
            
            return; // 提前返回，避免执行后续代码
        } else {
            // 如果没有HLS.js但浏览器可能支持原生HLS
            const hlsSupported = videoElement.canPlayType('application/vnd.apple.mpegurl') || 
                                 videoElement.canPlayType('application/x-mpegURL');
            
            if (hlsSupported) {
                console.log('使用浏览器原生支持播放HLS');
                // 使用原生播放器
                videoSource.src = fullVideoUrl;
                videoSource.type = videoType.type;
                videoElement.load();
                
                // 创建播放器实例
                player = new Plyr(videoElement, playerConfig);
                
                // 更新UI
                updatePlayerUI(episodeNumber);
                
                // 尝试播放
                videoElement.play().catch(error => {
                    console.warn('原生HLS播放失败:', error);
                    showMessage('提示', '点击视频开始播放');
                });
                
                return; // 提前返回
            } else {
                console.warn('浏览器不支持HLS且没有找到hls.js库，尝试使用原生播放器');
                tryFallbackPlayer(fullVideoUrl);
                return; // 提前返回
            }
        }
    }
    
    // 为标准格式(非HLS非TS)设置源
   
    videoElement = document.getElementById('player');
    player = new Plyr(videoElement, playerConfig);
    
    // 设置视频源
    player.source = {
        type: 'video',
        title: `${currentAnimeDetail.title} - 第${episodeNumber}集`,
        sources: [
            {
                src: fullVideoUrl,
                type: videoType.type,
                size: 720
            }
        ],
        poster: anime?.cover || ''
    };
    
    // 更新UI
    updatePlayerUI(episodeNumber);
    
    // 添加详细的错误处理
    player.on('error', (event) => {
        const error = event.detail.error;
        console.error('视频播放错误:', error);
        
        // 获取更多详细信息
        const mediaError = videoElement.error;
        let errorMessage = '未知错误';
        
        if (mediaError) {
            // 解析HTML5 MediaError代码
            switch (mediaError.code) {
                case 1: // MEDIA_ERR_ABORTED
                    errorMessage = '播放被中止';
                    break;
                case 2: // MEDIA_ERR_NETWORK
                    errorMessage = '网络错误导致视频下载失败';
                    break;
                case 3: // MEDIA_ERR_DECODE
                    errorMessage = '视频解码失败，可能是格式不支持';
                    break;
                case 4: // MEDIA_ERR_SRC_NOT_SUPPORTED
                    errorMessage = '视频格式不受支持或地址无效';
                    break;
                default:
                    errorMessage = `未知错误 (${mediaError.code})`;
            }
            
            if (mediaError.message) {
                errorMessage += `: ${mediaError.message}`;
            }
        }
        
        console.error('详细错误信息:', errorMessage);
        showMessage('播放错误', errorMessage);
        
        // 检查是否可能是TS格式
        if (errorMessage.includes('解码失败') || errorMessage.includes('格式不支持')) {
            console.log('怀疑视频可能是TS格式，尝试作为TS播放');
            const tsType = {
                type: 'video/mp2t',
                extension: videoType.extension,
                isTS: true,
                isHLS: false,
                isDASH: false
            };
            tryFallbackPlayer(fullVideoUrl, tsType);
            return;
        }
        
        // 尝试重新检测格式并使用原生播放器
        const newVideoType = detectVideoFormat(fullVideoUrl, true);
        console.log('重新检测视频类型:', newVideoType);
        tryFallbackPlayer(fullVideoUrl, newVideoType);
    });
    
    // 监听就绪事件
    // player.on('ready', () => {
    //     console.log('播放器就绪');
    //     showMessage('提示', '视频已就绪，点击播放');
    // });
    
    // // 监听加载事件
    // player.on('loadstart', () => {
    //     console.log('开始加载视频');
    //     showMessage('提示', '正在加载视频，请稍候...');
    // });
    
    // // 监听加载完成事件
    // player.on('loadeddata', () => {
    //     console.log('视频数据已加载');
    //     showMessage('提示', '视频已准备好，开始播放');
    // });
    
    // // 尝试自动播放
    // player.play().catch(error => {
    //     console.warn('自动播放失败，可能需要用户交互:', error);
    //     showMessage('提示', '点击视频开始播放');
    // });
}

// 更新播放器UI
function updatePlayerUI(episodeNumber) {
    // 更新标题
    domElements.currentEpisodeTitle.textContent = `${currentAnimeDetail.title} - 第${episodeNumber}集`;
    
    // 更新按钮状态（只有一集）
    domElements.prevEpisodeBtn.disabled = true;
    domElements.nextEpisodeBtn.disabled = true;
    cachedVideos.forEach(video => {
        if(currentAnimeId == video.anime_id){
            if(episodeNumber == video.episode_number + 1){
                domElements.prevEpisodeBtn.disabled = false;
            }
            if(episodeNumber == video.episode_number - 1){
                domElements.nextEpisodeBtn.disabled = false;
            }
        }
    });

    // 创建或更新返回按钮
    let backButton = document.getElementById('backButton');
    if (!backButton) {
        backButton = document.createElement('button');
        backButton.id = 'backButton';
        backButton.className = 'btn btn-primary position-absolute top-0 start-0 m-3';
        backButton.style.top = '10px';
        backButton.style.left = '10px';
        backButton.style.zIndex = '1000';
        backButton.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        backButton.innerHTML = '<i class="bi bi-arrow-left"></i>';
        document.getElementById('playerScreen').appendChild(backButton);
        
        // 添加返回按钮点击事件
        backButton.addEventListener('click', function() {
            // 停止播放
            if (player) {
                player.pause();
            }
            
            // 显示导航栏
            const navBar = document.querySelector('.navbar');
            if (navBar) {
                navBar.style.display = 'block';
            }
            
            // 显示欢迎界面，隐藏播放界面
            domElements.welcomeScreen.style.display = 'block';
            domElements.playerScreen.style.display = 'none';
        });
    }

    // 隐藏导航栏
    const navBar = document.querySelector('.navbar');
    if (navBar) {
        navBar.style.display = 'none';
    }
}

// 检测视频格式
function detectVideoFormat(videoUrl, forceCheck = false) {
    // 设置默认结果
    let result = {
        type: 'video/mp4',
        extension: '.mp4',
        isHLS: false,
        isDASH: false,
        isTS: false
    };
    
    // 边界检查
    if (!videoUrl) {
        console.warn('视频URL为空');
        return result;
    }
    
    console.log('正在检测视频格式:', videoUrl);
    
    // 检查是否是m3u8（HLS）格式
    if (videoUrl.toLowerCase().endsWith('.m3u8') || 
        videoUrl.toLowerCase().includes('.m3u8?') || 
        videoUrl.toLowerCase().includes('=m3u8')) {
        
        result.type = 'application/vnd.apple.mpegurl';
        result.extension = '.m3u8';
        result.isHLS = true;
        
        console.log('检测到HLS格式:', result);
        return result;
    }
    
    // 检查是否是mpd（DASH）格式
    if (videoUrl.toLowerCase().endsWith('.mpd') || 
        videoUrl.toLowerCase().includes('.mpd?') ||
        videoUrl.toLowerCase().includes('=mpd')) {
        
        result.type = 'application/dash+xml';
        result.extension = '.mpd';
        result.isDASH = true;
        
        console.log('检测到DASH格式:', result);
        return result;
    }
    
    // 检查是否是TS格式
    if (videoUrl.toLowerCase().endsWith('.ts') || 
        videoUrl.toLowerCase().includes('.ts?') ||
        videoUrl.toLowerCase().includes('=ts')) {
        
        result.type = 'video/mp2t';
        result.extension = '.ts';
        result.isTS = true;
        
        console.log('检测到MPEG-TS格式:', result);
        return result;
    }
    
    // 强制检查服务器返回的内容类型 - 针对可能是TS但使用mp4扩展名的情况
    if ((videoUrl.toLowerCase().endsWith('.mp4') || forceCheck) && navigator.onLine) {
        console.log('检测到mp4扩展名，但进行内容类型检查以确保格式');
        
        // 异步过程，但我们需要同步返回，先返回临时值，然后异步更新播放器行为
        fetch(videoUrl, { method: 'HEAD' })
            .then(response => {
                const contentType = response.headers.get('Content-Type');
                console.log('服务器返回的内容类型:', contentType);
                
                // 如果是TS格式
                if (contentType && contentType.includes('mp2t')) {
                    console.log('确认是TS格式，尽管文件名以.mp4结尾');
                    
                    // 由于我们已经返回了临时值，这里只能通知调用者
                    const tsTypeEvent = new CustomEvent('videoTypeUpdated', {
                        detail: {
                            url: videoUrl,
                            type: 'video/mp2t',
                            extension: '.ts', // 保持扩展名与URL匹配
                            isHLS: false,
                            isDASH: false,
                            isTS: true
                        }
                    });
                    document.dispatchEvent(tsTypeEvent);
                    
                    // 如果当前播放器已初始化，可能需要重新配置
                    if (player && player.isPlaying) {
                        console.log('播放器已在播放，建议切换到TS处理模式');
                        // 这里可以触发UI更新或其他操作
                    }
                }
            })
            .catch(error => {
                console.error('获取内容类型时出错:', error);
            });
    }
    
    // 根据扩展名确定其他常见格式
    if (videoUrl.toLowerCase().endsWith('.webm')) {
        result.type = 'video/webm';
        result.extension = '.webm';
    } else if (videoUrl.toLowerCase().endsWith('.ogg') || videoUrl.toLowerCase().endsWith('.ogv')) {
        result.type = 'video/ogg';
        result.extension = '.ogg';
    } else if (videoUrl.toLowerCase().endsWith('.mov')) {
        result.type = 'video/quicktime';
        result.extension = '.mov';
    } else if (videoUrl.toLowerCase().endsWith('.flv')) {
        result.type = 'video/x-flv';
        result.extension = '.flv';
    } else if (videoUrl.toLowerCase().endsWith('.3gp')) {
        result.type = 'video/3gpp';
        result.extension = '.3gp';
    } else if (videoUrl.toLowerCase().endsWith('.wmv')) {
        result.type = 'video/x-ms-wmv';
        result.extension = '.wmv';
    } else if (videoUrl.toLowerCase().endsWith('.avi')) {
        result.type = 'video/x-msvideo';
        result.extension = '.avi';
    } else {
        // 默认假设是MP4格式
        result.type = 'video/mp4';
        result.extension = '.mp4';
    }
    
    console.log('根据扩展名确定视频格式:', result);
    return result;
}

// 执行搜索
function performSearch(e) {
    e.preventDefault(); // 阻止表单默认提交行为
    
    // 获取搜索关键词（从提交的表单中获取）
    const keyword = e.target.querySelector('input[type="search"], input[type="text"]').value.trim();
    
    if (!keyword) {
        showMessage('搜索提示', '请输入搜索关键词');
        return;
    }
    
    // 清空搜索结果并显示加载中
    domElements.searchResultsGrid.innerHTML = `
        <div class="col-12 text-center p-5">
            <div class="spinner-border text-primary"></div>
            <p class="mt-3">正在搜索"${keyword}"...</p>
        </div>
    `;
    
    // 显示搜索结果模态框
    domElements.searchResultModal.show();
    
    // 发送搜索请求 - 修正URL参数
    fetch(`/api/anime/search?q=${encodeURIComponent(keyword)}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('搜索请求失败');
            }
            return response.json();
        })
        .then(data => {
            // 确保data.data存在，并且是数组
            if (data.success && data.data && Array.isArray(data.data)) {
                renderSearchResults(data.data);
            } else {
                renderSearchResults([]);
            }
        })
        .catch(error => {
            console.error('搜索错误:', error);
            domElements.searchResultsGrid.innerHTML = `
                <div class="col-12 text-center p-5">
                    <i class="bi bi-exclamation-triangle text-warning display-4"></i>
                    <h4 class="mt-3">搜索失败</h4>
                    <p class="text-muted">${error.message}</p>
                    <button class="btn btn-primary mt-3" onclick="performSearch(new Event('submit'))">重试</button>
                </div>
            `;
        });
}

// 渲染搜索结果
function renderSearchResults(results) {
    if (!results || results.length === 0) {
        domElements.searchResultsGrid.innerHTML = `
            <div class="col-12 text-center p-5">
                <i class="bi bi-search text-muted display-4"></i>
                <h4 class="mt-3">未找到相关结果</h4>
                <p class="text-muted">请尝试其他关键词搜索</p>
            </div>
        `;
        return;
    }
    
    // 构建搜索结果HTML
    let html = '';
    
    results.forEach(anime => {
        html += `
            <div class="col-6 col-md-4 col-lg-3 mb-4">
                <div class="card search-result-item" data-anime-id="${anime.id}">
                    <img src="${anime.cover || 'static/img/no-image.jpg'}" class="card-img-top" alt="${anime.title}">
                    <div class="card-body">
                        <h6 class="card-title mb-1">${anime.title}</h6>
                        <p class="card-text text-muted small">${anime.update || '未知更新'}</p>
                    </div>
                </div>
            </div>
        `;
    });
    
    domElements.searchResultsGrid.innerHTML = html;
    
    // 为每个搜索结果添加点击事件
    document.querySelectorAll('.search-result-item').forEach(item => {
        item.addEventListener('click', () => {
            const animeId = item.getAttribute('data-anime-id');
            domElements.searchResultModal.hide();
            loadAnimeDetail(animeId);
        });
    });
}

// 加载动漫详情(这个页面是不需要的)
function loadAnimeDetail(animeId) {
    // 显示加载中
    domElements.welcomeScreen.style.display = 'none';
    domElements.playerScreen.style.display = 'block';
    domElements.episodesList.innerHTML = `
        <div class="text-center p-4 text-muted">
            <div class="spinner-border"></div>
            <p class="mt-2">加载中...</p>
        </div>
    `;
    
    // 请求动漫详情
    fetch(`/api/anime/detail?id=${animeId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('获取动漫详情失败');
            }
            return response.json();
        })
        .then(data => {
            currentAnimeId = animeId;
            currentAnimeDetail = data;
           
        })
        .catch(error => {
            console.error('加载动漫详情错误:', error);
            domElements.episodesList.innerHTML = `
                <div class="col-12 text-center p-4">
                    <i class="bi bi-exclamation-circle text-danger"></i>
                    <p class="mt-2">加载失败，请重试</p>
                    <button class="btn btn-primary btn-sm mt-2" onclick="loadAnimeDetail('${animeId}')">重新加载</button>
                </div>
            `;
        });
}



// 显示提示信息
function showMessage(title, message) {
    domElements.toastTitle.textContent = title;
    domElements.toastMessage.textContent = message;
    domElements.toast.show();
}

// 处理视频链接错误
function handleVideoLoadError() {
    const animeId = currentAnimeId;
    const episodeId = currentEpisodeIndex;
    
    if (!animeId || !episodeId) {
        showMessage('无法重新加载视频：未知的影片ID', 'error');
        return;
    }
    
    showMessage('视频加载失败，正在尝试刷新链接...', 'warning');
    
    // 调用刷新API
    fetch(`/api/anime/video/refresh?anime_id=${animeId}&episode_id=${episodeId}`)
        .then(response => response.json())
        .then(data => {
            if (data.code === 0 && data.data.url) {
                showMessage('已获取新的视频链接，正在重新加载...', 'success');
                
                // 重新设置视频源
                const player = document.getElementById('player');
                if (player) {
                    const currentTime = player.currentTime; // 保存当前播放位置
                    player.src = data.data.url;
                    player.load();
                    player.play().then(() => {
                        // 恢复播放位置
                        player.currentTime = currentTime;
                    }).catch(err => {
                        console.error('自动播放失败:', err);
                    });
                }
            } else {
                showMessage(`无法获取视频: ${data.msg}`, 'error');
            }
        })
        .catch(error => {
            console.error('刷新视频链接失败:', error);
            showMessage('刷新视频链接失败，请稍后再试', 'error');
        });
}

// 初始化播放器事件
function initPlayerEvents() {
    const player = document.getElementById('player');
    if (player) {
        // 监听视频加载错误
        player.addEventListener('error', function(e) {
            console.error('视频加载错误:', e);
            handleVideoLoadError();
        });
        
        // 监听网络错误
        player.addEventListener('stalled', function() {
            console.warn('视频加载停滞');
            if (player.networkState === 3) { // NETWORK_NO_SOURCE
                handleVideoLoadError();
            }
        });
    }
}

function loadAndPlayVideo(url, anime_id, episode_id) {
    const player = document.getElementById('player');
    if (player) {
        // 保存当前播放的视频ID
        currentAnimeId = anime_id;
        currentEpisodeIndex = episode_id;
        
        player.src = url;
        player.load();
        
        // 尝试播放
        player.play().catch(err => {
            console.error('播放失败:', err);
            // 如果播放失败，可能是因为浏览器策略需要用户交互
            showMessage('点击播放按钮开始播放', 'info');
        });
        
        // 确保事件监听器已初始化
        initPlayerEvents();
    }
}

// 尝试使用原生播放器作为回退
function tryFallbackPlayer(videoUrl, videoType) {
    console.log('尝试使用原生HTML5播放器作为回退', videoUrl);
    
    if (!videoType) {
        videoType = detectVideoFormat(videoUrl, true);
    }
    console.log('回退播放器使用的视频类型:', videoType);
    
    // 获取已有的视频元素和源元素
    const videoElement = document.getElementById('player');
    const videoSource = document.getElementById('videoSource');
    const videoSourceWebm = document.getElementById('videoSourceWebm');
    const videoSourceOgg = document.getElementById('videoSourceOgg');
    
    if (!videoElement) {
        console.error('找不到视频元素');
        return;
    }
    
    // 重置视频元素
    videoElement.pause();
    videoElement.currentTime = 0;
    videoElement.controls = true;
    videoElement.autoplay = true;
    videoElement.className = 'native-video-player';
    videoElement.style.width = '100%';
    videoElement.style.height = '100%';
    videoElement.style.maxHeight = '70vh';
    
    // 更新UI显示当前集数
    updatePlayerUI(currentEpisodeIndex + 1);
    
    // 如果是HLS格式且支持HLS.js
    if (videoType.isHLS && window.Hls && Hls.isSupported()) {
        console.log('使用HLS.js播放HLS视频');
        const hls = new Hls({
            maxBufferLength: 30,
            maxMaxBufferLength: 60,
            enableWorker: true,
            lowLatencyMode: false,
            enableSoftwareAES: true,
            startLevel: -1,
            abrEwmaDefaultEstimate: 500000,
            manifestLoadingTimeOut: 10000,
            manifestLoadingMaxRetry: 3,
            manifestLoadingRetryDelay: 1000,
            levelLoadingTimeOut: 10000,
            levelLoadingMaxRetry: 3,
            levelLoadingRetryDelay: 1000,
            fragLoadingTimeOut: 20000,
            fragLoadingMaxRetry: 3,
            fragLoadingRetryDelay: 1000,
            startFragPrefetch: true,
            testBandwidth: true,
            progressive: true,
            lowLatencyMode: false,
            backBufferLength: 90
        });
        
        hls.loadSource(videoUrl);
        hls.attachMedia(videoElement);
        
        hls.on(Hls.Events.MANIFEST_PARSED, function() {
            console.log('HLS清单已解析，尝试播放');
            videoElement.play().catch(error => {
                console.error('HLS自动播放失败:', error);
                showVideoError('自动播放失败，请点击视频开始播放');
            });
        });
        
        hls.on(Hls.Events.ERROR, function(event, data) {
            console.error('HLS回退播放器错误:', data);
            if (data.fatal) {
                switch(data.type) {
                    case Hls.ErrorTypes.NETWORK_ERROR:
                        console.log('HLS网络错误，尝试恢复...');
                        hls.startLoad();
                        break;
                    case Hls.ErrorTypes.MEDIA_ERROR:
                        console.log('HLS媒体错误，尝试恢复...');
                        hls.recoverMediaError();
                        break;
                    default:
                        // 无法恢复的错误，尝试原生播放
                        console.error('HLS致命错误无法恢复');
                        hls.destroy();
                        tryDirectSource();
                        break;
                }
            }
        });
        
        // 监听视频错误
        videoElement.addEventListener('error', function(e) {
            const error = videoElement.error;
            console.error('HLS视频错误:', error);
            showVideoError(getErrorMessage(error));
        });
        
        return;
    }
    
    // 对于标准格式视频
    if (videoSource) {
        videoSource.src = videoUrl;
        videoSource.type = videoType.type;
    }
    
    // 清除其他格式源
    if (videoSourceWebm) videoSourceWebm.src = '';
    if (videoSourceOgg) videoSourceOgg.src = '';
    
    // 重新加载视频
    videoElement.load();
    videoElement.play().catch(error => {
        console.error('原生播放器自动播放失败:', error);
        showVideoError('自动播放失败，请点击视频开始播放');
    });
    
    // 错误处理
    videoElement.onerror = function(e) {
        const error = videoElement.error;
        console.error('原生播放器错误:', error);
        showVideoError(getErrorMessage(error));
    };
}

// 辅助函数：显示视频错误
function showVideoError(message) {
    showMessage('播放错误', message);
}

// 辅助函数：获取错误消息
function getErrorMessage(error) {
    if (!error) return '未知错误';
    
    switch (error.code) {
        case 1:
            return '播放被中止';
        case 2:
            return '网络错误导致视频下载失败';
        case 3:
            return '视频解码失败，可能是格式不支持';
        case 4:
            return '视频格式不受支持或地址无效';
        default:
            return `未知错误 (${error.code})${error.message ? ': ' + error.message : ''}`;
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init); 