// 全局变量
let token = null;
let studentInfo = {};
let examEndTime = null;
let countdownInterval = null;
let currentProblemName = null;
let notificationCount = 0;
let notificationInterval = null;
let isFirstLoad = true;
let isHandlingExpire = false;

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 检查 localStorage 中是否有 token
    token = localStorage.getItem('token');
    if (token) {
        // 有 token，显示主页面
        showMainPage();
    } else {
        // 无 token，显示登录页面
        showLoginPage();
        // 加载登录页面的考试说明
        loadLoginInstructions();
        // 加载考试状态，显示解压密码
        loadExamStatus();
    }

    // 绑定登录表单提交事件
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    // 绑定退出登录按钮点击事件
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }

    // 初始化时间显示
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
});

// 更新当前时间
function updateCurrentTime() {
    const now = new Date();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    const seconds = now.getSeconds().toString().padStart(2, '0');
    const timeString = `${hours}:${minutes}:${seconds}`;
    
    const currentTimeElement = document.getElementById('current-time');
    if (currentTimeElement) {
        currentTimeElement.textContent = timeString;
    }
}

// 显示登录页面
function showLoginPage() {
    const loginPage = document.getElementById('login-page');
    const mainPage = document.getElementById('main-page');
    
    if (loginPage) {
        loginPage.classList.remove('hidden');
    }
    if (mainPage) {
        mainPage.classList.add('hidden');
    }
    // 隐藏倒计时
    const countdownContainer = document.getElementById('countdown-container');
    const countdownSeparator = document.getElementById('countdown-separator');
    if (countdownContainer) countdownContainer.classList.add('hidden');
    if (countdownSeparator) countdownSeparator.classList.add('hidden');
}

// 显示主页面
async function showMainPage() {
    // 前置校验：先获取学生信息，确保 Token 有效
    const success = await getStudentInfo();
    
    // 只有在获取学生信息成功后，才显示主页面
    if (!success) {
        return; // 失败则保持在登录页
    }
    
    // 显示主页面
    const loginPage = document.getElementById('login-page');
    const mainPage = document.getElementById('main-page');
    
    if (loginPage) {
        loginPage.classList.add('hidden');
    }
    if (mainPage) {
        mainPage.classList.remove('hidden');
    }

    // 倒计时
    const countdownContainer = document.getElementById('countdown-container');
    const countdownSeparator = document.getElementById('countdown-separator');
    if (countdownContainer) countdownContainer.classList.remove('hidden');
    if (countdownSeparator) countdownSeparator.classList.remove('hidden');


    // 加载题目列表
    loadProblems();
    
    // 加载考试须知到仪表板
    loadDashboardInstructions();
    
    // 初始化倒计时
    initCountdown();
    
    // 初始化通知轮询
    initNotificationPolling();
}

// 处理登录
async function handleLogin(e) {
    e.preventDefault();
    
    const studentId = document.getElementById('student-id').value;
    const password = document.getElementById('password').value;
    const errorElement = document.getElementById('login-error');
    
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams({
                student_id: studentId,
                password: password
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            token = data.access_token;
            localStorage.setItem('token', token);
            await showMainPage(); // 等待 showMainPage 完成
        } else {
            const errorData = await response.json();
            errorElement.textContent = errorData.detail;
            errorElement.classList.remove('hidden');
        }
    } catch (error) {
        errorElement.textContent = '登录失败，请检查网络连接';
        errorElement.classList.remove('hidden');
    }
}

// 处理令牌过期
function handleTokenExpired() {
    // 防止并发 401 导致多次弹窗
    if (isHandlingExpire) {
        return;
    }
    
    isHandlingExpire = true;
    alert("登录已过期或考场已刷新，请重新登录！");
    handleLogout();
    
    // 延迟一小段时间后释放锁
    setTimeout(() => {
        isHandlingExpire = false;
    }, 1000);
}

// 处理退出登录
function handleLogout() {
    localStorage.removeItem('token');
    token = null;
    studentInfo = {};
    // 清理定时器
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }
    if (typeof notificationInterval !== 'undefined' && notificationInterval) {
        clearInterval(notificationInterval);
    }
    showLoginPage();
    loadLoginInstructions();
    loadExamStatus();
}

// 获取学生信息
async function getStudentInfo() {
    try {
        // 携带 Token 发起对 /api/me 的 GET 请求
        const response = await fetch('/api/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            studentInfo = {
                id: data.exam_id,
                name: data.name
            };
            // 更新导航栏信息
            const studentNameElement = document.getElementById('student-name');
            const studentIdElement = document.getElementById('student-id-display');
            if (studentNameElement) {
                studentNameElement.textContent = studentInfo.name;
            }
            if (studentIdElement) {
                studentIdElement.textContent = studentInfo.id;
            }
            // 更新仪表板信息
            const dashboardStudentName = document.getElementById('dashboard-student-name');
            const dashboardStudentId = document.getElementById('dashboard-student-id');
            if (dashboardStudentName) {
                dashboardStudentName.textContent = studentInfo.name;
            }
            if (dashboardStudentId) {
                dashboardStudentId.textContent = studentInfo.id;
            }
            return true; // 返回成功状态
        } else {
            if (response.status === 401) {
                handleTokenExpired();
                return false; // 返回失败状态
            }
            console.error('获取学生信息失败:', response.statusText);
            return false; // 返回失败状态
        }
    } catch (error) {
        console.error('获取学生信息失败:', error);
        // 遇到网络错误时，调用 handleTokenExpired() 强制阻断并退回登录页
        handleTokenExpired();
        return false; // 返回失败状态
    }
}

// 加载仪表板的考试须知
async function loadDashboardInstructions() {
    try {
        const response = await fetch('/api/instructions');
        if (response.ok) {
            const data = await response.json();
            const html = marked.parse(data.content);
            const instructionsElement = document.getElementById('dashboard-instructions');
            if (instructionsElement) {
                instructionsElement.innerHTML = html;
            }
        } else {
            throw new Error('加载失败');
        }
    } catch (error) {
        console.error('加载考试说明失败:', error);
        const instructionsElement = document.getElementById('dashboard-instructions');
        if (instructionsElement) {
            instructionsElement.innerHTML = '<p class="text-red-500">加载失败</p>';
        }
    }
}

// 选项卡切换
function switchTab(tabName) {
    // 隐藏所有内容
    document.getElementById('tab-instructions').classList.add('hidden');
    document.getElementById('tab-problems').classList.add('hidden');
    document.getElementById('tab-notifications').classList.add('hidden');
    
    // 重置所有选项卡按钮样式
    document.getElementById('tab-btn-instructions').className = 'py-4 px-6 border-b-2 border-transparent hover:text-gray-600 hover:border-gray-300 whitespace-nowrap';
    document.getElementById('tab-btn-problems').className = 'py-4 px-6 border-b-2 border-transparent hover:text-gray-600 hover:border-gray-300 whitespace-nowrap';
    document.getElementById('tab-btn-notifications').className = 'py-4 px-6 border-b-2 border-transparent hover:text-gray-600 hover:border-gray-300 whitespace-nowrap relative';
    
    // 显示选中的内容
    document.getElementById(`tab-${tabName}`).classList.remove('hidden');
    
    // 设置选中的选项卡按钮样式
    document.getElementById(`tab-btn-${tabName}`).className = 'py-4 px-6 border-b-2 border-indigo-500 text-indigo-600 font-medium whitespace-nowrap relative';
    
    // 如果切换到通知选项卡，清除未读状态
    if (tabName === 'notifications') {
        const badge = document.getElementById('notification-badge');
        if (badge) {
            badge.classList.add('hidden');
        }
    }
}

// 初始化通知轮询
function initNotificationPolling() {
    // 立即加载一次通知
    loadNotifications();
    
    // 每 5 秒轮询一次
    notificationInterval = setInterval(loadNotifications, 5000);
}

// 加载通知列表
async function loadNotifications() {
    try {
        const response = await fetch('/api/notifications');
        if (!response.ok) {
            if (response.status === 401) {
                return handleTokenExpired();
            }
            return; // 其他错误静默失败，避免打扰考试
        }
        
        const notifications = await response.json();
        
        // 首屏加载拦截
        if (isFirstLoad) {
            isFirstLoad = false;
            notificationCount = notifications.length;
            updateNotificationsList(notifications);
            return; // 提前返回，确保首屏不弹窗
        }
        
        // 后续轮询逻辑
        if (notifications.length > notificationCount) {
            // 有新通知
            notificationCount = notifications.length;
            updateNotificationsList(notifications);
            
            // 显示未读通知标记
            const badge = document.getElementById('notification-badge');
            if (badge) {
                badge.classList.remove('hidden');
            }
            
            // 显示提示
            alert('收到新的考场广播！');
        }
    } catch (error) {
        console.error('加载通知失败:', error);
        // 遇到网络错误时，调用 handleTokenExpired() 强制阻断并退回登录页
        handleTokenExpired();
    }
}

// 更新通知列表
function updateNotificationsList(notifications) {
    const container = document.getElementById('notifications-list');
    if (!container) return;
    
    container.innerHTML = '';
    
    // 按时间倒序排序
    notifications.sort((a, b) => {
        return b.time.localeCompare(a.time);
    });
    
    notifications.forEach(notification => {
        const notificationElement = document.createElement('div');
        notificationElement.className = 'border-l-4 border-indigo-500 pl-4 py-2 bg-gray-50 rounded';
        notificationElement.innerHTML = `
            <div class="text-sm text-gray-500">${notification.time}</div>
            <div class="mt-1">${notification.content}</div>
        `;
        container.appendChild(notificationElement);
    });
}

// 加载登录页面的考试说明
async function loadLoginInstructions() {
    try {
        const response = await fetch('/api/instructions');
        if (response.ok) {
            const data = await response.json();
            const html = marked.parse(data.content);
            const instructionsElement = document.getElementById('login-instructions');
            if (instructionsElement) {
                instructionsElement.innerHTML = html;
            }
        } else {
            throw new Error('加载失败');
        }
    } catch (error) {
        console.error('加载考试说明失败:', error);
        const instructionsElement = document.getElementById('login-instructions');
        if (instructionsElement) {
            instructionsElement.innerHTML = '<p class="text-red-500">加载失败</p>';
        }
    }
}

// 加载考试状态
async function loadExamStatus() {
    try {
        const response = await fetch('/api/status');
        if (response.ok) {
            const data = await response.json();
            if (data.password) {
                const passwordDisplay = document.getElementById('password-display');
                const unzipPassword = document.getElementById('unzip-password');
                if (passwordDisplay && unzipPassword) {
                    unzipPassword.textContent = data.password;
                    passwordDisplay.classList.remove('hidden');
                }
            }
        }
    } catch (error) {
        console.error('加载考试状态失败:', error);
    }
}

// 加载题目列表
async function loadProblems() {
    try {
        const response = await fetch('/api/problems', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            renderProblems(data.problems);
        } else {
            if (response.status === 401) {
                return handleTokenExpired();
            }
            console.error('获取题目列表失败');
        }
    } catch (error) {
        console.error('加载题目列表失败:', error);
        // 遇到网络错误时，调用 handleTokenExpired() 强制阻断并退回登录页
        handleTokenExpired();
    }
}

// 渲染题目列表
function renderProblems(problems) {
    const container = document.getElementById('problems-list');
    if (!container) return;
    
    container.innerHTML = '';
    
    // 创建表格
    const table = document.createElement('table');
    table.className = 'min-w-full divide-y divide-gray-200';
    
    // 表头
    const thead = document.createElement('thead');
    thead.className = 'bg-gray-50';
    thead.innerHTML = `
        <tr>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">序号</th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">题目名称</th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">提交状态</th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">文件大小</th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">提交时间</th>
            <th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
        </tr>
    `;
    table.appendChild(thead);
    
    // 表格内容
    const tbody = document.createElement('tbody');
    tbody.className = 'bg-white divide-y divide-gray-200';
    
    problems.forEach((problem, index) => {
        const tr = document.createElement('tr');
        
        // 提交状态显示
        let statusHtml = '';
        let sizeHtml = '';
        let timeHtml = '';
        let viewBtnHtml = '';

        
        if (problem.submitted) {
            statusHtml = '<span class="text-green-600 font-medium">已提交</span>';
            sizeHtml = problem.size;
            timeHtml = problem.submit_time;
            viewBtnHtml = `<button onclick="viewCode('${problem.name}')" class="bg-gray-600 text-white py-1 px-3 rounded-md hover:bg-gray-700">查看</button>`;
        } else {
            statusHtml = '<span class="text-red-600 font-medium">未提交</span>';
            sizeHtml = '-';
            timeHtml = '-';
            viewBtnHtml = `<button disabled class="bg-gray-300 text-white py-1 px-3 rounded-md cursor-not-allowed" title="请先提交代码">查看</button>`;
        }
        
        tr.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${index + 1}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${problem.name}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm">${statusHtml}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${sizeHtml}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${timeHtml}</td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <button onclick="openUploadModal('${problem.name}')" class="bg-indigo-600 text-white py-1 px-3 rounded-md hover:bg-indigo-700 mr-2">提交代码</button>
                ${viewBtnHtml} </td>
        `;
        tbody.appendChild(tr);
    });
    
    table.appendChild(tbody);
    container.appendChild(table);
}

// 打开上传模态框
function openUploadModal(problemName) {
    currentProblemName = problemName;
    const modalTitle = document.getElementById('modal-title');
    const fileInput = document.getElementById('modal-file-input');
    const statusElement = document.getElementById('modal-status');
    const uploadModal = document.getElementById('upload-modal');
    const confirmBtn = document.getElementById('confirm-upload-btn');
    
    if (modalTitle) {
        modalTitle.textContent = `上传代码 - ${problemName}`;
    }
    if (fileInput) {
        fileInput.value = '';
    }
    if (statusElement) {
        statusElement.textContent = '';
        statusElement.classList.add('hidden');
    }
    if (uploadModal) {
        uploadModal.classList.remove('hidden');
    }
    // 每次打开弹窗，确保按钮是可用状态 
    if (confirmBtn) {
        confirmBtn.disabled = false;
        confirmBtn.className = 'bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700';
        confirmBtn.textContent = '确认上传';
    }
}

// 关闭上传模态框
function closeUploadModal() {
    const uploadModal = document.getElementById('upload-modal');
    if (uploadModal) {
        uploadModal.classList.add('hidden');
    }
    currentProblemName = null;
}

// 确认上传
async function confirmUpload() {
    if (!currentProblemName) return;
    
    const fileInput = document.getElementById('modal-file-input');
    const statusElement = document.getElementById('modal-status');
    const confirmBtn = document.getElementById('confirm-upload-btn');   
    
    if (!fileInput.files.length) {
        statusElement.textContent = '请选择文件';
        statusElement.className = 'mt-4 text-sm text-red-500';
        statusElement.classList.remove('hidden');
        return;
    }
    
    const file = fileInput.files[0];
    
    // 前端双重校验
    if (!file.name.endsWith('.cpp')) {
        statusElement.textContent = '只支持上传 .cpp 文件';
        statusElement.className = 'mt-4 text-sm text-red-500';
        statusElement.classList.remove('hidden');
        return;
    }
    
    if (file.size > 102400) { // 100KB
        statusElement.textContent = '文件大小不能超过100KB';
        statusElement.className = 'mt-4 text-sm text-red-500';
        statusElement.classList.remove('hidden');
        return;
    }

    // 校验通过后，立即禁用上传按钮，防止连点 
    if (confirmBtn) {
        confirmBtn.disabled = true;
        confirmBtn.className = 'bg-gray-400 text-white py-2 px-4 rounded-md cursor-not-allowed';
        confirmBtn.textContent = '上传中...';
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('problem_name', currentProblemName);
    
    try {
        statusElement.textContent = '上传中...';
        statusElement.className = 'mt-4 text-sm text-blue-500';
        statusElement.classList.remove('hidden');
        
        const response = await fetch('/api/upload', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });
        
        if (response.ok) {
            statusElement.textContent = '上传成功';
            statusElement.className = 'mt-4 text-sm text-green-500';
            
            // 关闭模态框
            setTimeout(() => {
                closeUploadModal();
                // 刷新题目列表
                loadProblems();
            }, 1000);
        } else {
            if (response.status === 401) {
                return handleTokenExpired();
            }
            const errorData = await response.json();
            statusElement.textContent = `上传失败: ${errorData.detail}`;
            statusElement.className = 'mt-4 text-sm text-red-500';

            // 上传失败时，恢复按钮状态 
            if (confirmBtn) {
                confirmBtn.disabled = false;
                confirmBtn.className = 'bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700';
                confirmBtn.textContent = '确认上传';
            }
        }
    } catch (error) {
        statusElement.textContent = '上传失败，请检查网络连接';
        statusElement.className = 'mt-4 text-sm text-red-500';

        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.className = 'bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700';
            confirmBtn.textContent = '确认上传';
        }
    }
}

// 查看代码
async function viewCode(problemName) {
    try {
        const response = await fetch(`/api/view_code?problem_name=${encodeURIComponent(problemName)}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            // 创建模态对话框
            const modal = document.createElement('div');
            modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
            modal.innerHTML = `
                <div class="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-auto">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-lg font-bold">查看代码 - ${data.filename}</h3>
                        <button onclick="this.closest('.fixed').remove()" class="text-gray-500 hover:text-gray-700">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                    <pre class="bg-gray-100 p-4 rounded-md overflow-x-auto"><code>${data.code}</code></pre>
                </div>
            `;
            document.body.appendChild(modal);
        } else {
            const errorData = await response.json();
            alert(`查看失败: ${errorData.detail}`);
        }
    } catch (error) {
        alert('查看失败，请检查网络连接');
    }
}

// 初始化倒计时
async function initCountdown() {
    try {
        // 从后端获取考试状态
        const response = await fetch('/api/status');
        if (response.ok) {
            const data = await response.json();
            if (data.is_running && data.end_timestamp > 0) {
                examEndTime = new Date(data.end_timestamp * 1000);
            } else {
                examEndTime = null;
            }
        }
    } catch (error) {
        console.error('获取考试状态失败:', error);
        examEndTime = null;
    }
    
    // 开始倒计时
    updateCountdown();
    countdownInterval = setInterval(updateCountdown, 1000);
}

// 更新倒计时
function updateCountdown() {
    if (examEndTime) {
        const now = new Date();
        const timeLeft = examEndTime - now;
        
        if (timeLeft <= 0) {
            // 考试结束
            clearInterval(countdownInterval);
            const countdownElement = document.getElementById('countdown');
            if (countdownElement) {
                countdownElement.textContent = '00:00:00';
            }
            
            // 禁用所有提交按钮
            const buttons = document.querySelectorAll('button');
            buttons.forEach(button => {
                if (button.textContent === '提交代码') {
                    button.disabled = true;
                    button.className = 'bg-gray-400 text-white py-1 px-3 rounded-md cursor-not-allowed mr-2';
                }
            });
            
            // 弹出提示
            alert('考试已结束');
            return;
        }
        
        // 计算时、分、秒
        const hours = Math.floor(timeLeft / (1000 * 60 * 60));
        const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((timeLeft % (1000 * 60)) / 1000);
        
        // 格式化显示
        const formattedTime = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        const countdownElement = document.getElementById('countdown');
        if (countdownElement) {
            countdownElement.textContent = formattedTime;
        }
    } else {
        const countdownElement = document.getElementById('countdown');
        if (countdownElement) {
            countdownElement.textContent = '--:--:--';
        }
    }
}
