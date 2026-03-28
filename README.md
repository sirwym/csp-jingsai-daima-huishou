# 竞赛回收系统 (CSP Contest Code Recovery System)

![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.8+-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 项目简介

竞赛回收系统是一款专为信息学竞赛（如CSP、NOIP等）设计的局域网代码提交与管理系统。该系统采用桌面主控台 + Web服务的混合架构，支持在局域网环境下快速部署，实现考生身份验证、代码提交、实时监考和消息广播等功能。

**核心特性：**

- 🖥️ 桌面主控台：PySide6 构建的 GUI 管理界面，一键启停考试服务
- 🌐 Web 考生端：基于 FastAPI + TailwindCSS 的响应式网页，支持多端访问
- 🔐 JWT 身份认证：动态密钥生成，防止越权提交和代考
- 📡 实时消息广播：监考老师可向所有考生发送即时通知
- ⏱️ 自动倒计时：考试结束自动拦截提交，防止超时交卷
- 📦 题目自动分发：支持 ZIP 压缩包智能解析与下载

***

## 技术栈

### 后端

| 技术          | 版本     | 用途          |
| ----------- | ------ | ----------- |
| Python      | 3.13+  | 核心编程语言      |
| FastAPI     | 0.115+ | Web API 框架  |
| Uvicorn     | 0.32+  | ASGI 服务器    |
| python-jose | 3.3+   | JWT 令牌生成与验证 |
| aiofiles    | 24.1+  | 异步文件操作      |

### 前端

| 技术            | 版本   | 用途          |
| ------------- | ---- | ----------- |
| TailwindCSS   | 3.4+ | CSS 原子类框架   |
| Marked.js     | 最新   | Markdown 解析 |
| 原生 JavaScript | ES6+ | 交互逻辑        |

### 桌面端

| 技术          | 版本    | 用途            |
| ----------- | ----- | ------------- |
| PySide6     | 6.8+  | Qt6 Python 绑定 |
| PyInstaller | 6.11+ | 可执行文件打包       |

***

## 项目结构

```
.
├── main.py                 # 主控台入口（PySide6 GUI）
├── server.py               # FastAPI Web 服务
├── init_env.py             # 环境初始化脚本
├── build.sh                # macOS/Linux 打包脚本
├── build.bat               # Windows 打包脚本
├── package.json            # Node.js 依赖（TailwindCSS）
├── students.csv            # 考生信息表（自动生成）
├── exam_instructions.md    # 考试须知（自动生成）
├── problems.zip            # 题目压缩包（需自备）
├── .exam_state.json        # 考试状态持久化
├── notifications.json      # 通知消息存储
├── system.log              # 系统日志
├── data/                   # 考生代码存储目录
│   └── {准考证号}/
│       └── {题目名}/
│           └── *.cpp
├── templates/              # Jinja2 模板
│   ├── index.html          # 主页面框架
│   ├── login.html          # 登录页组件
│   ├── dashboard.html      # 考生仪表板
│   └── footer.html         # 页脚组件
├── static/                 # 静态资源
│   ├── css/
│   │   ├── input.css       # Tailwind 源文件
│   │   └── tailwind.css    # 编译后样式
│   ├── js/
│   │   └── app.js          # 前端交互逻辑
│   ├── logo.png            # 系统 Logo
│   ├── icon.ico            # Windows 图标
│   └── icon.icns           # macOS 图标
└── .venv/                  # Python 虚拟环境
```

***

## 快速开始

### 环境要求

- **操作系统**: Windows 10+ / macOS 12+ / Linux
- **Python**: 3.13 或更高版本
- **Node.js**: 18+（可选，用于重新编译 CSS）

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone <repository-url>
   cd CSP竞赛局域网代码回收系统
   ```
2. **创建虚拟环境并安装依赖**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   # 或 .venv\Scripts\activate  # Windows

   pip install -r requirements.txt
   ```
3. **安装前端依赖（可选）**
   ```bash
   npm install
   npm run build:css
   ```

### 启动方式

#### 开发模式

```bash
# 直接运行主控台
python main.py
```

#### 打包为可执行文件

**Windows:**

```bash
build.bat
```

**macOS/Linux:**

```bash
chmod +x build.sh
./build.sh
```

打包完成后，可执行文件位于 `dist/` 目录下。

***

## 使用说明

### 1. 配置考生信息

编辑 `students.csv` 文件，录入考生信息：

```csv
exam_id,name,password
1001,张三,123456
1002,李四,abcdef
```

### 2. 准备题目压缩包

将题目文件打包为 `problems.zip`，放置于项目根目录。压缩包结构示例：

```
problems.zip
├── CSP2026-J.pdf      # PDF 文件自动排除在题目外
├── apple/             # 题目1文件夹
├── tree/              # 题目2文件夹
└── graph/             # 题目3文件夹
```

### 3. 启动考试

1. 运行主控台程序
2. 设置端口号（默认 8000）和考试时长
3. 可选设置解压密码
4. 点击"开始考试"启动服务

### 4. 考生访问

考生通过浏览器访问：

```
http://{服务器IP}:{端口}
```

示例：`http://192.168.1.100:8000`

### 5. 监考功能

- **消息广播**：在主控台输入消息，点击"发送全员通知"
- **异常检测**：系统自动检测 IP 异常切换并报警
- **实时监控**：日志区实时显示登录、提交等操作

***

## 配置说明

### 考试状态文件 (.exam\_state.json)

```json
{
  "port": "8000",
  "exam_duration": "120",
  "password": "解压密码",
  "end_timestamp": 1735689600,
  "is_running": true,
  "secret_key": "动态生成的JWT密钥"
}
```

### 系统限制

| 配置项       | 默认值   | 说明          |
| --------- | ----- | ----------- |
| 最大文件大小    | 100KB | 单文件上传限制     |
| 允许文件类型    | .cpp  | 仅支持 C++ 源代码 |
| Token 有效期 | 考试期间  | 每次新考试重新生成密钥 |

***

## 部署方式

### 单机部署（推荐）

适用于小型竞赛场景，主控台与服务器运行在同一台机器上。

### 局域网部署

1. 确保服务器防火墙开放指定端口
2. 考生设备与服务器处于同一局域网
3. 通过服务器内网 IP 访问


## 开发指南

### 重新编译 CSS

```bash
# 开发模式（监听变化）
npm run dev:css

# 生产模式（压缩）
npm run build:css
```

### 目录说明

- `data/`: 考生提交的代码自动按 `data/{准考证号}/{题目名}/` 结构存储
- `templates/`: 使用 Jinja2 模板引擎，支持组件化复用
- `static/`: 静态文件通过 FastAPI 的 StaticFiles 挂载

### API 接口列表

| 接口                       | 方法   | 描述      |
| ------------------------ | ---- | ------- |
| `/`                      | GET  | 考生端首页   |
| `/api/login`             | POST | 考生登录    |
| `/api/problems`          | GET  | 获取题目列表  |
| `/api/upload`            | POST | 上传代码    |
| `/api/view_code`         | GET  | 查看已提交代码 |
| `/api/status`            | GET  | 获取考试状态  |
| `/api/notifications`     | GET  | 获取通知列表  |
| `/api/instructions`      | GET  | 获取考试须知  |
| `/api/download/problems` | GET  | 下载题目压缩包 |

***

## 常见问题 (FAQ)

**Q: 考生无法访问系统？**\
A: 请检查：1) 服务器防火墙是否开放端口；2) 考生设备是否与服务器在同一局域网；3) 服务器 IP 地址是否正确。

**Q: 如何修改考试时长？**\
A: 在主控台"考试时长"输入框中修改，单位为分钟。考试开始后修改无效。

**Q: 考生提交失败提示"考试已结束"？**\
A: 检查主控台倒计时是否归零，或 `.exam_state.json` 中的 `is_running` 是否为 false。

**Q: 如何清空历史数据？**\
A: 每次点击"开始考试"时，系统会自动清空 `notifications.json` 和 `system.log`。如需清空考生代码，请手动删除 `data/` 目录。

**Q: macOS 打包后无法运行？**\
A: 请确保在"系统偏好设置 -> 安全性与隐私"中允许该应用运行。

***

## 许可证

MIT License © 2026 Yuanming

***

## 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Web 框架
- [TailwindCSS](https://tailwindcss.com/) - 实用优先的 CSS 框架
- [Qt for Python](https://doc.qt.io/qtforpython/) - 跨平台 GUI 框架

