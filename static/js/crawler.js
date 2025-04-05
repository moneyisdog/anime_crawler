// 全局变量
let currentPage = 1;
let totalPages = 1;
let currentAnimeId = null;
let currentAnimeDetail = null;
let currentEpisodeId = null;
let selectedEpisodes = [];
let currentTaskId = null;
let currentTaskInfo = null;

// DOM 元素
const animeListElement = document.getElementById('animeList');
const paginationElement = document.getElementById('pagination');
const tasksListElement = document.getElementById('tasksList');
const createTaskForm = document.getElementById('createTaskForm');
const searchForm = document.getElementById('searchForm');
const searchInput = document.getElementById('searchInput');
const animeDetailModal = new bootstrap.Modal(document.getElementById('animeDetailModal'));
const taskDetailModal = new bootstrap.Modal(document.getElementById('taskDetailModal'));
const createTaskModal = new bootstrap.Modal(document.getElementById('createTaskModal'));
const toast = new bootstrap.Toast(document.getElementById('toast'));

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    // 加载动漫列表
    loadAnimeList();
    
    // 加载任务列表
    loadTasks();
    
    // 事件监听
    document.getElementById('refreshAnimeList').addEventListener('click', () => loadAnimeList());
    document.getElementById('refreshTasks').addEventListener('click', () => loadTasks());
    document.getElementById('openCreateTaskModal').addEventListener('click', showCreateTaskModal);
    document.getElementById('isPeriodic').addEventListener('change', toggledailyUpdateTime);
    document.getElementById('submitCreateTask').addEventListener('click', handleCreateTask);
    searchForm.addEventListener('submit', handleSearch);
    
    // 批量选择剧集相关
    document.getElementById('selectAllEpisodes').addEventListener('click', selectAllEpisodes);
    document.getElementById('deselectAllEpisodes').addEventListener('click', deselectAllEpisodes);
    document.getElementById('batchCreateTask').addEventListener('click', batchCreateTask);
    
    // 任务操作按钮
    document.getElementById('executeTaskBtn').addEventListener('click', executeTask);
    document.getElementById('deleteTaskBtn').addEventListener('click', deleteTask);
});

// 加载动漫列表
async function loadAnimeList(page = 1, preloadedData = null) {
    currentPage = page;
    showLoading(animeListElement);
    
    // 如果提供了预加载数据，直接使用
    if (preloadedData) {
        renderAnimeList(preloadedData);
        return;
    }
    
    try {
        const response = await fetch(`/api/anime/list?page=${page}`);
        const data = await response.json();
        
        if (data.success && data.data.length > 0) {
            renderAnimeList(data.data);
            renderPagination();
        } else {
            animeListElement.innerHTML = '<div class="text-center p-4 text-muted">暂无动漫</div>';
        }
    } catch (error) {
        console.error('加载动漫列表失败:', error);
        animeListElement.innerHTML = '<div class="text-center p-4 text-danger">加载失败，请重试</div>';
    }
}

// 渲染动漫列表
function renderAnimeList(animes) {
    animeListElement.innerHTML = '';
    
    animes.forEach(anime => {
        const animeCard = document.createElement('div');
        animeCard.className = 'anime-card';
        
        animeCard.innerHTML = `
            <img src="${anime.cover_url || '/static/img/no-image.jpg'}" class="anime-cover" alt="${anime.title}">
            <div class="anime-info">
                <h5 class="anime-title">${anime.title}</h5>
                <div class="anime-meta">
                    ${anime.year ? `${anime.year}年` : ''} 
                    ${anime.region || ''} 
                    ${anime.update_info || ''}
                </div>
            </div>
        `;
        
        animeCard.addEventListener('click', () => loadAnimeDetail(anime.id));
        animeListElement.appendChild(animeCard);
    });
}

// 渲染分页控件
function renderPagination() {
    paginationElement.innerHTML = '';
    
    // 上一页按钮
    const prevButton = document.createElement('li');
    prevButton.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
    prevButton.innerHTML = `<a class="page-link" href="#">上一页</a>`;
    if (currentPage > 1) {
        prevButton.addEventListener('click', () => loadAnimeList(currentPage - 1));
    }
    paginationElement.appendChild(prevButton);
    
    // 页码按钮 (显示最多5个页码)
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, startPage + 4);
    
    for (let i = startPage; i <= endPage; i++) {
        const pageItem = document.createElement('li');
        pageItem.className = `page-item ${i === currentPage ? 'active' : ''}`;
        pageItem.innerHTML = `<a class="page-link" href="#">${i}</a>`;
        pageItem.addEventListener('click', () => loadAnimeList(i));
        paginationElement.appendChild(pageItem);
    }
    
    // 下一页按钮
    const nextButton = document.createElement('li');
    nextButton.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
    nextButton.innerHTML = `<a class="page-link" href="#">下一页</a>`;
    if (currentPage < totalPages) {
        nextButton.addEventListener('click', () => loadAnimeList(currentPage + 1));
    }
    paginationElement.appendChild(nextButton);
}

// 加载动漫详情
async function loadAnimeDetail(animeId) {
    currentAnimeId = animeId;
    // 清空已选剧集
    selectedEpisodes = [];
    
    // 显示全屏加载器
    document.getElementById('fullscreenLoading').style.display = 'flex';
    
    try {
        const response = await fetch(`/api/anime/detail/${animeId}`);
        const data = await response.json();
        
        // 隐藏全屏加载器
        document.getElementById('fullscreenLoading').style.display = 'none';
        
        if (data.success && data.data) {
            currentAnimeDetail = data.data;
            renderAnimeDetail(data.data);
            animeDetailModal.show();
        } else {
            showToast('错误', '获取动漫详情失败', 'danger');
        }
    } catch (error) {
        // 隐藏全屏加载器
        document.getElementById('fullscreenLoading').style.display = 'none';
        
        console.error('加载动漫详情失败:', error);
        showToast('错误', '获取动漫详情失败', 'danger');
    }
}

// 渲染动漫详情
function renderAnimeDetail(anime) {
    document.getElementById('modalAnimeTitle').textContent = anime.title;
    document.getElementById('modalAnimeTitleDetail').textContent = anime.title;
    
    let infoText = [];
    if (anime.alias) infoText.push(`别名: ${anime.alias}`);
    if (anime.region) infoText.push(`地区: ${anime.region}`);
    if (anime.year) infoText.push(`年份: ${anime.year}`);
    
    document.getElementById('modalAnimeInfo').textContent = infoText.join(' | ');
    document.getElementById('modalAnimeDesc').textContent = anime.description || '暂无简介';
    document.getElementById('modalAnimeCover').src = anime.cover_url || '/static/img/no-image.jpg';
    
    // 渲染剧集列表
    const episodesListElement = document.getElementById('episodesList');
    episodesListElement.innerHTML = '';
    
    if (anime.episodes && anime.episodes.length > 0) {
        anime.episodes.forEach(episode => {
            const episodeItem = document.createElement('div');
            episodeItem.className = 'episode-item';
            episodeItem.textContent = episode.title;
            episodeItem.dataset.id = episode.id;
            episodeItem.dataset.animeId = anime.id;
            
            // 添加复选框
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'episode-checkbox';
            checkbox.dataset.id = episode.id;
            episodeItem.prepend(checkbox);
            
            // 点击事件 - 剧集选择
            episodeItem.addEventListener('click', (e) => {
                // 如果点击的是复选框，不触发额外操作
                if (e.target === checkbox) return;
                
                checkbox.checked = !checkbox.checked;
                toggleEpisodeSelection(episode.id);
                
                // 提示用户已添加到缓存列表
                if (checkbox.checked) {
                    showToast('提示', `《${anime.title}》的${episode.title}已添加到缓存计划列表`, 'info');
                } else {
                    showToast('提示', `已从缓存计划列表中移除${episode.title}`, 'info');
                }
            });
            
            // 复选框变化事件
            checkbox.addEventListener('change', () => {
                toggleEpisodeSelection(episode.id);
            });
            
            episodesListElement.appendChild(episodeItem);
        });
    } else {
        episodesListElement.innerHTML = '<div class="text-center p-4 text-muted">暂无剧集</div>';
    }
}

// 切换剧集选择状态
function toggleEpisodeSelection(episodeId) {
    const index = selectedEpisodes.indexOf(episodeId);
    if (index === -1) {
        selectedEpisodes.push(episodeId);
    } else {
        selectedEpisodes.splice(index, 1);
    }
    
    // 更新批缓存按钮状态
    document.getElementById('batchCreateTask').disabled = selectedEpisodes.length === 0;
}

// 选择所有剧集
function selectAllEpisodes() {
    const checkboxes = document.querySelectorAll('.episode-checkbox');
    selectedEpisodes = [];
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = true;
        selectedEpisodes.push(checkbox.dataset.id);
    });
    
    document.getElementById('batchCreateTask').disabled = selectedEpisodes.length === 0;
    showToast('提示', '已选择所有剧集', 'info');
}

// 取消选择所有剧集
function deselectAllEpisodes() {
    const checkboxes = document.querySelectorAll('.episode-checkbox');
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    
    selectedEpisodes = [];
    document.getElementById('batchCreateTask').disabled = true;
    showToast('提示', '已取消选择所有剧集', 'info');
}

// 批量创缓存任务
function batchCreateTask() {
    if (selectedEpisodes.length === 0) {
        showToast('提示', '请至少选择一个剧集', 'warning');
        return;
    }
    
    // 填充任务表单
    document.getElementById('animeId').value = currentAnimeId;
    
    // 保存动漫标题到表单
    if (currentAnimeDetail && currentAnimeDetail.title) {
        document.getElementById('animeTitle').value = currentAnimeDetail.title;
    }
    
    // 设置起始集和结束集
    const sortedEpisodes = [...selectedEpisodes].sort((a, b) => a - b);
    document.getElementById('startEpisode').value = sortedEpisodes[0];
    document.getElementById('endEpisode').value = sortedEpisodes[sortedEpisodes.length - 1];
    
    // 如果只选了一集，禁用结束集输入框
    if (sortedEpisodes.length === 1) {
        document.getElementById('endEpisode').disabled = true;
    } else {
        document.getElementById('endEpisode').disabled = false;
    }
    
    // 隐藏动漫详情模态框，显示任务创建模态框
    animeDetailModal.hide();
    setTimeout(() => {
        createTaskModal.show();
    }, 500);
}

// 显示创建任务模态框
function showCreateTaskModal() {
    // 重置表单
    createTaskForm.reset();
    document.getElementById('animeId').value = '';
    document.getElementById('animeTitle').value = '';
    document.getElementById('startEpisode').value = '1';
    document.getElementById('endEpisode').value = '';
    document.getElementById('endEpisode').disabled = false;
    document.getElementById('isPeriodic').checked = false;
    toggledailyUpdateTime();
    
    // 显示模态框
    createTaskModal.show();
}

// 切换间隔时间输入框显示
function toggledailyUpdateTime() {
    const dailyUpdateTimeDiv = document.getElementById('dailyUpdateTimeDiv');
    dailyUpdateTimeDiv.style.display = document.getElementById('isPeriodic').checked ? 'block' : 'none';
}

// 处理创建任务表单提交
async function handleCreateTask() {
    const animeId = document.getElementById('animeId').value;
    const startEpisode = document.getElementById('startEpisode').value;
    const endEpisode = document.getElementById('endEpisode').value;
    const isPeriodic = document.getElementById('isPeriodic').checked;
    const dailyUpdateTime = document.getElementById('dailyUpdateTime').value;
    
    if (!animeId || !startEpisode) {
        showToast('错误', '请填写必要的字段', 'danger');
        return;
    }
    
    // 构建任务数据
    const data = {
        anime_id: animeId,
        start_episode: parseInt(startEpisode),
        is_periodic: isPeriodic
    };
    
    // 添加动漫标题 - 如果是从动漫详情创建的任务，使用当前动漫详情的标题
    if (currentAnimeDetail && currentAnimeDetail.id === animeId) {
        data.anime_title = currentAnimeDetail.title;
    } else {
        // 尝试从页面中获取标题
        const titleElement = document.getElementById('modalAnimeTitle');
        if (titleElement && titleElement.textContent) {
            data.anime_title = titleElement.textContent;
        }
    }
    
    if (endEpisode) {
        data.end_episode = parseInt(endEpisode);
    }
    
    if (isPeriodic) {
        const [hours, minutes] = dailyUpdateTime.split(':').map(Number);
        data.daily_update_time = parseInt(hours * 3600 + minutes * 60);
    }
    
    try {
        const response = await fetch('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('成功', '任务创建成功', 'success');
            createTaskModal.hide();
            loadTasks(); // 刷新任务列表
        } else {
            showToast('错误', result.error || '创建任务失败', 'danger');
        }
    } catch (error) {
        console.error('创建任务失败:', error);
        showToast('错误', '创建任务失败，请重试', 'danger');
    }
}

// 加载任务列表
async function loadTasks() {
    showLoading(tasksListElement);
    
    try {
        const response = await fetch('/api/tasks');
        const data = await response.json();
        
        if (data.success && data.data.length > 0) {
            renderTasks(data.data);
        } else {
            tasksListElement.innerHTML = '<div class="text-center p-4 text-muted">暂无任务</div>';
        }
    } catch (error) {
        console.error('加载任务列表失败:', error);
        tasksListElement.innerHTML = '<div class="text-center p-4 text-danger">加载失败，请重试</div>';
    }
}

// 渲染任务列表
function renderTasks(tasks) {
    tasksListElement.innerHTML = '';
    
    tasks.forEach(task => {
        const taskItem = document.createElement('a');
        taskItem.href = '#';
        taskItem.className = `list-group-item list-group-item-action task-item status-${task.status}`;
        
        let statusBadge = '';
        switch (task.status) {
            case 'pending':
                statusBadge = '<span class="badge bg-secondary">待处理</span>';
                break;
            case 'running':
                statusBadge = '<span class="badge bg-info">进行中</span>';
                break;
            case 'completed':
                statusBadge = '<span class="badge bg-success">已完成</span>';
                break;
            case 'partial':
                statusBadge = '<span class="badge bg-warning">部分完成</span>';
                break;
            case 'failed':
                statusBadge = '<span class="badge bg-danger">失败</span>';
                break;
            case 'terminated':
                statusBadge = '<span class="badge bg-warning">异常终止</span>';
                break;
            default:
                statusBadge = `<span class="badge bg-secondary">${task.status}</span>`;
        }
        
        const periodicBadge = task.is_periodic 
            ? '<span class="badge bg-primary ms-1">周期性</span>' 
            : '';
        
        const episodeRange = task.end_episode 
            ? `${task.start_episode}-${task.end_episode}集` 
            : `从第${task.start_episode}集开始`;
        
        taskItem.innerHTML = `
            <div class="d-flex w-100 justify-content-between">
                <h6 class="mb-1">${task.anime_title || '未知动漫'}</h6>
                <small>${statusBadge}${periodicBadge}</small>
            </div>
            <p class="mb-1">${episodeRange}</p>
            <small class="text-muted">创建时间: ${formatDateTime(task.created_at)}</small>
        `;
        
        taskItem.addEventListener('click', () => loadTaskDetail(task.id));
        tasksListElement.appendChild(taskItem);
    });
}

// 加载任务详情
async function loadTaskDetail(taskId) {
    currentTaskId = taskId;
    
    // 显示全屏加载器
    document.getElementById('fullscreenLoading').style.display = 'flex';
    
    try {
        const response = await fetch(`/api/tasks/${taskId}`);
        const data = await response.json();
        
        // 隐藏全屏加载器
        document.getElementById('fullscreenLoading').style.display = 'none';
        
        if (data.success && data.data) {
            // 保存当前任务信息到全局变量
            currentTaskInfo = data.data;
            renderTaskDetail(data.data);
            taskDetailModal.show();
        } else {
            showToast('错误', '获取任务详情失败', 'danger');
        }
    } catch (error) {
        // 隐藏全屏加载器
        document.getElementById('fullscreenLoading').style.display = 'none';
        
        console.error('加载任务详情失败:', error);
        showToast('错误', '获取任务详情失败', 'danger');
    }
}
function daily_update_time_format(daily_update_time) {
    const hours = Math.floor(daily_update_time / 3600);
    const minutes = Math.floor((daily_update_time % 3600) / 60);
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
}
// 渲染任务详情
function renderTaskDetail(task) {
    const tableBody = document.getElementById('taskDetailTable');
    tableBody.innerHTML = '';
    
    const rows = [
        { label: '任务ID', value: task.id },
        { label: '动漫', value: task.anime_title || '未知动漫' },
        { label: '动漫ID', value: task.anime_id },
        { label: '缓存范围', value: task.end_episode ? `${task.start_episode}-${task.end_episode}集` : `从第${task.start_episode}集开始` },
        { label: '任务类型', value: task.is_periodic ? '周期性任务' : '一次性任务' },
        { label: '更新时间', value: task.is_periodic ? daily_update_time_format(task.daily_update_time) : '无' },
        { label: '状态', value: getStatusText(task.status) },
        { label: '创建时间', value: formatDateTime(task.created_at) },
        { label: '上次执行', value: task.last_run ? formatDateTime(task.last_run) : '未执行' },
        { label: '下次执行', value: task.next_run ? formatDateTime(task.next_run) : '未排期' }
    ];
    
    rows.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <th scope="row">${row.label}</th>
            <td>${row.value}</td>
        `;
        tableBody.appendChild(tr);
    });
    
    // 根据任务状态启用/禁用按钮
    const executeBtn = document.getElementById('executeTaskBtn');
    executeBtn.disabled = task.status === 'running';
    
    // 对于异常终止或失败的任务，显示重新执行按钮
    if (task.status === 'terminated' || task.status === 'failed') {
        executeBtn.textContent = '重新执行';
        executeBtn.classList.remove('btn-primary');
        executeBtn.classList.add('btn-warning');
    } else {
        executeBtn.textContent = '执行';
        executeBtn.classList.remove('btn-warning');
        executeBtn.classList.add('btn-primary');
    }
    
    // 如果任务已执行过，加载执行结果
    if (task.status === 'running' || task.status === 'completed' || task.status === 'failed') {
        loadTaskResults(task.id);
    } else {
        // 隐藏结果区域
        document.getElementById('taskResultsSection').style.display = 'none';
    }
}

// 获取状态文本
function getStatusText(status) {
    switch (status) {
        case 'pending': return '待处理';
        case 'running': return '进行中';
        case 'partial': return '部分完成';
        case 'completed': return '已完成';
        case 'failed': return '失败';
        case 'terminated': return '异常终止';
        default: return status;
    }
}

// 执行任务
async function executeTask() {
    // 如果传入的是事件对象，则需要从当前上下文获取任务ID
    let taskIdToExecute = currentTaskId;
    
    if (!taskIdToExecute) {
        // 检查是否有全局变量存储当前任务ID
        if (typeof currentTaskInfo !== 'undefined' && currentTaskInfo && currentTaskInfo.id) {
            taskIdToExecute = currentTaskInfo.id;
        } else {
            console.error('无法获取任务ID');
            showToast('错误', '无法获取任务ID', 'danger');
            return;
        }
    }
    
    // 显示全屏加载器
    document.getElementById('fullscreenLoading').style.display = 'flex';
    
    try {
        console.log(`正在执行任务: ${taskIdToExecute}`);
        const response = await fetch(`/api/tasks/${taskIdToExecute}/execute`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        // 隐藏全屏加载器
        document.getElementById('fullscreenLoading').style.display = 'none';
        
        if (data.success) {
            showToast('成功', '任务已开始执行', 'success');
            taskDetailModal.hide();
            loadTasks(); // 刷新任务列表
        } else {
            showToast('错误', data.error || '执行任务失败', 'danger');
        }
    } catch (error) {
        // 隐藏全屏加载器
        document.getElementById('fullscreenLoading').style.display = 'none';
        
        console.error('执行任务失败:', error);
        showToast('错误', '执行任务失败，请重试', 'danger');
    }
}

// 删除任务
async function deleteTask(currentTaskId) {
    // 如果传入的是事件对象，则需要从当前上下文获取任务ID
    if (!currentTaskId || currentTaskId.target) {
        // 检查是否有全局变量存储当前任务ID
        if (typeof currentTaskInfo !== 'undefined' && currentTaskInfo && currentTaskInfo.id) {
            currentTaskId = currentTaskInfo.id;
        } else {
            console.error('无法获取任务ID');
            showToast('错误', '无法获取任务ID', 'danger');
            return;
        }
    }
    
    if (!confirm(`确定要删除该任务吗？`)) {
        return;
    }
    
    try {
        console.log(`正在删除任务: ${currentTaskId}`);
        const response = await fetch(`/api/tasks/${currentTaskId}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('成功', '任务已删除', 'success');
            taskDetailModal.hide();
            loadTasks(); // 刷新任务列表
        } else {
            showToast('错误', data.error || '删除任务失败', 'danger');
        }
    } catch (error) {
        console.error('删除任务失败:', error);
        showToast('错误', '删除任务失败，请重试', 'danger');
    }
}

// 处理搜索提交
async function handleSearch(e) {
    e.preventDefault();
    
    const query = searchInput.value.trim();
    
    if (!query) return;
    
    // 显示全屏加载器
    document.getElementById('fullscreenLoading').style.display = 'flex';
    
    try {
        const response = await fetch(`/api/anime/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        // 隐藏全屏加载器
        document.getElementById('fullscreenLoading').style.display = 'none';
        
        if (data.success && data.data.length > 0) {
            loadAnimeList(1, data.data);
        } else {
            showToast('提示', '未找到相关动漫', 'info');
        }
    } catch (error) {
        // 隐藏全屏加载器
        document.getElementById('fullscreenLoading').style.display = 'none';
        
        console.error('搜索失败:', error);
        showToast('错误', '搜索失败，请重试', 'danger');
    }
}

// 辅助函数：显示加载中
function showLoading(element) {
    element.innerHTML = `
        <div class="text-center p-4 text-muted">
            <div class="spinner-border"></div>
            <p class="mt-2">加载中...</p>
        </div>
    `;
}

// 辅助函数：显示消息提示
function showToast(title, message, type = 'primary') {
    const toastTitle = document.getElementById('toastTitle');
    const toastMessage = document.getElementById('toastMessage');
    
    toastTitle.textContent = title;
    toastMessage.textContent = message;
    
    // 设置toast颜色
    const toastElement = document.getElementById('toast');
    toastElement.className = `toast border-${type}`;
    
    toast.show();
}

// 辅助函数：格式化日期时间
function formatDateTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
}

// 加载任务执行结果
async function loadTaskResults(taskId) {
    const resultsContainer = document.getElementById('taskResultsContainer');
    resultsContainer.innerHTML = '<div class="text-center p-3"><div class="spinner-border spinner-border-sm"></div> 加载中...</div>';
    document.getElementById('taskResultsSection').style.display = 'block';
    
    try {
        const response = await fetch(`/api/tasks/${taskId}/results`);
        const data = await response.json();
        
        if (data.success && data.data.length > 0) {
            renderTaskResults(data.data);
        } else {
            resultsContainer.innerHTML = '<div class="text-center p-3 text-muted">暂无执行结果</div>';
        }
    } catch (error) {
        console.error('加载任务执行结果失败:', error);
        resultsContainer.innerHTML = '<div class="text-center p-3 text-danger">加载结果失败，请重试</div>';
    }
}

// 渲染任务执行结果
function renderTaskResults(results) {
    const resultsContainer = document.getElementById('taskResultsContainer');
    resultsContainer.innerHTML = '';
    
    if (!results || results.length === 0) {
        resultsContainer.innerHTML = '<div class="alert alert-info">暂无任务结果</div>';
        return;
    }
    
    // 按集数排序
    results.sort((a, b) => {
        // 去除可能的前缀并转换为数字
        const numA = parseInt(String(a.episode_number).replace('ep', ''));
        const numB = parseInt(String(b.episode_number).replace('ep', ''));
        return numA - numB;
    });
    
    results.forEach(result => {
        const resultItem = document.createElement('div');
        resultItem.className = 'list-group-item';
        
        let statusIcon, statusClass;
        switch (result.status) {
            case 'completed':
            case 'success':
                statusIcon = '<i class="bi bi-check-circle-fill text-success"></i>';
                statusClass = 'text-success';
                break;
            case 'partial':
                statusIcon = '<i class="bi bi-check-circle-fill text-warning"></i>';
                statusClass = 'text-warning';
                break;
            case 'failed':
                statusIcon = '<i class="bi bi-x-circle-fill text-danger"></i>';
                statusClass = 'text-danger';
                break;
            case 'pending':
                statusIcon = '<i class="bi bi-hourglass-split text-warning"></i>';
                statusClass = 'text-warning';
                break;
            default:
                statusIcon = '<i class="bi bi-question-circle-fill text-secondary"></i>';
                statusClass = 'text-secondary';
        }
        
        let retryText = result.retry_count > 0 ? ` (已重试${result.retry_count}次)` : '';
        
        // 确保显示的集数不包含ep前缀
        const cleanEpisodeNumber = String(result.episode_number).replace('ep', '');
        
        resultItem.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="me-2">${statusIcon}</div>
                <div class="flex-grow-1">
                    <div class="fw-bold">第 ${cleanEpisodeNumber} 集 
                        <span class="${statusClass}">
                            ${result.status === 'success' ? '缓存成功' : result.status === 'failed' ? '缓存失败' + retryText : '处理中'}
                        </span>
                    </div>
                    ${result.cache_url ? `<div class="text-break small">缓存地址: ${result.cache_url}</div>` : ''}
                    ${result.error_message ? `<div class="text-danger small">错误: ${result.error_message}</div>` : ''}
                    <div class="text-muted small">更新时间: ${formatDateTime(result.created_at)}</div>
                </div>
            </div>
        `;
        
        resultsContainer.appendChild(resultItem);
    });
} 