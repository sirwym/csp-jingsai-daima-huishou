#!/usr/bin/env python3
"""
竞赛回收系统 - 主控台
使用 PySide6 构建桌面 GUI 界面，控制考试服务的启停
"""
import sys
import os
from pathlib import Path
# === 核心修复 1：解决 macOS .app 无控制台导致的 print 闪退问题 ===
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

# === 核心修复 2：统一当前工作路径 ===
if getattr(sys, 'frozen', False):
    # 打包后：获取可执行文件所在目录
    app_path = Path(sys.executable).parent
    # 如果是 macOS 的 .app 内部 (Contents/MacOS)，将路径提权到 .app 外层
    if sys.platform == 'darwin' and app_path.name == 'MacOS' and app_path.parent.name == 'Contents':
        app_path = app_path.parent.parent.parent
    os.chdir(app_path)
else:
    # 开发环境
    os.chdir(Path(__file__).parent)


import json
import socket
import time
import multiprocessing
import secrets
import logging
from init_env import init_environment
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QPlainTextEdit, QGroupBox,QMessageBox
)
from PySide6.QtCore import QTimer, Qt, QThread, Signal
from PySide6.QtGui import QPalette, QColor
import uvicorn


# 配置 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [MAIN] %(message)s',
    handlers=[
        logging.FileHandler("system.log", encoding="utf-8", mode="a"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("竞赛回收系统V1.0 - 主控台")
        self.setGeometry(100, 100, 800, 600)
        
        # 服务进程
        self.server_process = None
        # 考试状态
        self.exam_state = {
            "port": "8000",
            "exam_duration": "120",  # 默认 120 分钟
            "password": "",
            "end_timestamp": 0,
            "is_running": False,
            "secret_key": ""
        }
        # 状态文件路径
        self.state_file = Path("./.exam_state.json")
        
        # 日志文件和位置
        self.log_file = Path("./system.log")
        self.log_pos = 0
        
        # 检查日志文件是否存在，如果存在，获取其大小作为初始位置
        if self.log_file.exists():
            self.log_pos = self.log_file.stat().st_size
        
        # 初始化 UI
        self.init_ui()
        # 恢复状态
        self.restore_state()
        # 初始化计时器
        self.init_timer()
        
        # 记录启动日志
        logger.info("主控台启动")
    
    def read_new_logs(self):
        """读取新的日志内容并显示在界面中"""
        if self.log_file.exists():
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    # 跳转到上次读取的位置
                    f.seek(self.log_pos)
                    # 读取新增的文本
                    new_lines = f.read()
                    # 更新读取位置
                    self.log_pos = f.tell()
                    # 如果有新内容，追加到日志区域
                    if new_lines:
                        self.log_text_edit.appendPlainText(new_lines.strip())
                        # 保持滚动条在最下方
                        scroll_bar = self.log_text_edit.verticalScrollBar()
                        scroll_bar.setValue(scroll_bar.maximum())
            except Exception as e:
                logger.error(f"读取日志文件失败: {e}")
    
    def get_local_ip(self):
        """获取本机在局域网中的真实 IP 地址"""
        try:
            # 利用 UDP 协议的一个特性来获取正确的出口网卡 IP，不需要真实连接
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    def update_access_address(self):
        """当端口改变时，实时更新界面上的考生访问地址"""
        port = self.port_input.text().strip()
        # 如果端口没填，给个默认提示
        if not port:
            port = "8000"
        self.address_display.setText(f"http://{self.local_ip}:{port}")


    def clear_old_data(self):
        """清空旧数据，为新考试做准备"""
        try:
            # 清空 notifications.json
            notifications_file = Path("./notifications.json")
            with open(notifications_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            logger.info("已清空通知数据")
        except Exception as e:
            logger.error(f"清空通知数据失败: {e}")
        
        try:
            # 清空 system.log
            with open("./system.log", "w", encoding="utf-8") as f:
                f.write("")
            # 重置日志读取位置
            self.log_pos = 0
            # 清空界面上的日志显示
            self.log_text_edit.clear()
            logger.info("已清空日志数据")
        except Exception as e:
            logger.error(f"清空日志数据失败: {e}")
    
    def init_ui(self):
        """初始化 UI 界面"""
        # 创建主部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 设置全局样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QWidget {
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }
            QGroupBox {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                font-weight: bold;
                color: #4a5568;
            }
            QPushButton {
                background-color: #4299e1;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3182ce;
            }
            QPushButton:disabled {
                background-color: #a0aec0;
            }
            QLineEdit {
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #4299e1;
                outline: none;
            }
            QPlainTextEdit {
                background-color: #2d3748;
                color: #e2e8f0;
                font-family: 'Menlo', 'Consolas', monospace;
                font-size: 12px;
                border: 1px solid #4a5568;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        
        # 顶部帮助按钮
        top_bar_layout = QHBoxLayout()
        top_bar_layout.addStretch()
        # 帮助按钮
        self.help_button = QPushButton("?")
        self.help_button.setFixedSize(28, 28)
        self.help_button.setStyleSheet("""
            QPushButton {
                background-color: #edf2f7;
                color: #4a5568;
                border: 1px solid #cbd5e0;
                border-radius: 14px;
                font-size: 14px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
        """)
        self.help_button.clicked.connect(self.show_help_dialog)
        top_bar_layout.addWidget(self.help_button)
        main_layout.addLayout(top_bar_layout)
        
        # 顶部控制区
        header_group = QGroupBox("控制中心")
        header_layout = QHBoxLayout()
        
        # 状态指示灯和标签
        status_layout = QHBoxLayout()
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(12, 12)
        self.status_indicator.setStyleSheet("background-color: #a0aec0; border-radius: 6px;")
        self.status_label = QLabel("等待开始...")
        self.status_label.setStyleSheet("font-weight: bold; margin-left: 8px;")
        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        # 控制按钮
        self.start_stop_button = QPushButton("开始考试")
        self.start_stop_button.clicked.connect(self.toggle_server)
        
        header_layout.addLayout(status_layout)
        header_layout.addWidget(self.start_stop_button)
        header_group.setLayout(header_layout)
        main_layout.addWidget(header_group)
        
        # 中部设置区 
        settings_group = QGroupBox("考试设置")
        settings_layout = QGridLayout()
        settings_layout.setColumnStretch(0, 1)
        settings_layout.setColumnStretch(1, 2)
        
        # 获取本机 IP
        self.local_ip = self.get_local_ip()
        
        # 端口号输入框
        port_label = QLabel("端口号:")
        self.port_input = QLineEdit(self.exam_state["port"])
        # 绑定文字改变事件，实时更新地址
        self.port_input.textChanged.connect(self.update_access_address) 
        settings_layout.addWidget(port_label, 0, 0)
        settings_layout.addWidget(self.port_input, 0, 1)
        
        # 考试时长输入框
        duration_label = QLabel("考试时长 (分):")
        self.duration_input = QLineEdit(self.exam_state["exam_duration"])
        settings_layout.addWidget(duration_label, 0, 2)
        settings_layout.addWidget(self.duration_input, 0, 3)
        
        # 解压密码输入框
        password_label = QLabel("解压密码 (可选):")
        self.password_input = QLineEdit(self.exam_state["password"])
        settings_layout.addWidget(password_label, 1, 0)
        settings_layout.addWidget(self.password_input, 1, 1, 1, 3)
        
        # 考生访问地址展示 
        address_label = QLabel("考生访问地址:")
        self.address_display = QLineEdit()
        self.address_display.setReadOnly(True)  # 设置为只读，但可以复制
        self.update_access_address() # 初始化时调用一次
        settings_layout.addWidget(address_label, 2, 0)
        settings_layout.addWidget(self.address_display, 2, 1, 1, 3)
        
        # 倒计时标签 (注意：这里由原来的 2,0 改到了 3,0 行)
        self.countdown_label = QLabel("剩余时间: --:--:--")
        settings_layout.addWidget(self.countdown_label, 3, 0, 1, 4)
        
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)
        
        # 消息广播区域
        broadcast_group = QGroupBox("消息广播")
        broadcast_layout = QVBoxLayout()
        
        self.broadcast_input = QPlainTextEdit()
        self.broadcast_input.setPlaceholderText("请输入广播消息...")
        self.broadcast_input.setFixedHeight(80)
        broadcast_layout.addWidget(self.broadcast_input)
        
        self.send_broadcast_button = QPushButton("发送全员通知")
        self.send_broadcast_button.clicked.connect(self.send_broadcast)
        broadcast_layout.addWidget(self.send_broadcast_button)
        
        broadcast_group.setLayout(broadcast_layout)
        main_layout.addWidget(broadcast_group)
        
        # 底部日志区
        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout()
        
        self.log_text_edit = QPlainTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setPlaceholderText("系统日志将显示在这里...")
        log_layout.addWidget(self.log_text_edit)
        
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group, 1)  # 占满剩余空间
    
    def init_timer(self):
        """初始化计时器"""
        # 倒计时定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)  # 每秒更新一次
        
        # 日志读取定时器
        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self.read_new_logs)
        self.log_timer.start(500)  # 每500毫秒读取一次
    
    def update_countdown(self):
        """更新倒计时显示"""
        if self.exam_state["is_running"] and self.exam_state["end_timestamp"] > 0:
            current_time = time.time()
            remaining_time = self.exam_state["end_timestamp"] - current_time
            
            if remaining_time <= 0:
                # 考试结束
                self.exam_state["is_running"] = False
                self.stop_server()
                self.start_stop_button.setText("开始考试")
                self.status_label.setText("系统状态: 考试结束")
                self.countdown_label.setText("剩余时间: 00:00:00")
                QMessageBox.information(self, "考试结束", "考试时间已结束！")
                return
            
            # 计算时、分、秒
            hours = int(remaining_time // 3600)
            minutes = int((remaining_time % 3600) // 60)
            seconds = int(remaining_time % 60)
            
            # 格式化显示
            countdown_str = f"剩余时间: {hours:02d}:{minutes:02d}:{seconds:02d}"
            self.countdown_label.setText(countdown_str)
        else:
            self.countdown_label.setText("剩余时间: --:--:--")
    
    def restore_state(self):
        """恢复状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    saved_state = json.load(f)
                
                # 恢复状态
                self.exam_state["port"] = saved_state.get("port", "8000")
                self.exam_state["exam_duration"] = saved_state.get("exam_duration", "120")
                self.exam_state["password"] = saved_state.get("password", "")
                self.exam_state["end_timestamp"] = saved_state.get("end_timestamp", 0)
                self.exam_state["secret_key"] = saved_state.get("secret_key", "")
                
                # 如果 secret_key 为空，生成一个新的
                if not self.exam_state["secret_key"]:
                    self.exam_state["secret_key"] = secrets.token_hex(32)
                    logger.info("生成新的安全密钥")
                
                # 检查是否需要恢复运行状态
                current_time = time.time()
                if self.exam_state["end_timestamp"] > current_time:
                    self.exam_state["is_running"] = True
                    self.start_server()
                    self.start_stop_button.setText("结束考试")
                    self.status_label.setText("系统状态: 运行中")
                
                # 更新 UI
                self.port_input.setText(self.exam_state["port"])
                self.duration_input.setText(self.exam_state["exam_duration"])
                self.password_input.setText(self.exam_state["password"])
                
            except Exception as e:
                print(f"恢复状态失败: {e}")
    
    def save_state(self):
        """保存状态"""
        try:
            # 更新状态
            self.exam_state["port"] = self.port_input.text()
            self.exam_state["exam_duration"] = self.duration_input.text()
            self.exam_state["password"] = self.password_input.text()
            
            # 写入文件
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.exam_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存状态失败: {e}")
    
    def toggle_server(self):
        """切换服务器状态"""
        if self.exam_state["is_running"]:
            # 停止服务器
            self.stop_server()
            self.start_stop_button.setText("开始考试")
            self.status_label.setText("系统状态: 已停止")
            self.status_indicator.setStyleSheet("background-color: #a0aec0; border-radius: 6px;")
            self.exam_state["is_running"] = False
            self.exam_state["end_timestamp"] = 0
            self.save_state()
            logger.info("考试结束")
        else:
            # 开始服务器
            # 清空旧数据，为新考试做准备
            self.clear_old_data()
            # 生成新的安全密钥，确保每次新考试的 Token 都不同
            self.exam_state["secret_key"] = secrets.token_hex(32)
            logger.info("生成新的安全密钥")
            if self.start_server():
                self.start_stop_button.setText("结束考试")
                self.status_label.setText("系统状态: 运行中")
                self.status_indicator.setStyleSheet("background-color: #48bb78; border-radius: 6px;")
                self.exam_state["is_running"] = True
                
                # 计算结束时间戳
                try:
                    duration = int(self.duration_input.text())
                    self.exam_state["end_timestamp"] = time.time() + duration * 60
                    self.save_state()
                    logger.info(f"考试开始，时长: {duration} 分钟")
                except ValueError:
                    QMessageBox.warning(self, "错误", "请输入有效的考试时长")
                    self.stop_server()
                    self.start_stop_button.setText("开始考试")
                    self.status_label.setText("系统状态: 未启动")
                    self.status_indicator.setStyleSheet("background-color: #a0aec0; border-radius: 6px;")
                    self.exam_state["is_running"] = False
    
    def start_server(self):
        """启动服务器"""
        try:
            port = self.port_input.text()
            
            # 使用 multiprocessing 启动服务器
            self.server_process = multiprocessing.Process(
                target=run_server,
                args=(port,)
            )
            self.server_process.daemon = True
            self.server_process.start()
            
            # 等待服务器启动
            time.sleep(2)
            
            if self.server_process.is_alive():
                logger.info(f"服务器启动成功，端口: {port}")
                return True
            else:
                QMessageBox.warning(self, "错误", "服务器启动失败")
                logger.error("服务器启动失败")
                return False
        except Exception as e:
            QMessageBox.warning(self, "错误", f"启动服务器失败: {e}")
            logger.error(f"启动服务器失败: {e}")
            return False
    
    def stop_server(self):
        """停止服务器"""
        if self.server_process and self.server_process.is_alive():
            self.server_process.terminate()
            self.server_process.join(timeout=5)
            logger.info("服务器已停止")
    
    def send_broadcast(self):
        """发送广播消息"""
        content = self.broadcast_input.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "警告", "请输入广播内容")
            return
        
        # 获取当前时间
        current_time = time.strftime("%H:%M:%S", time.localtime())
        
        # 读取或创建 notifications.json 文件
        notifications_file = Path("./notifications.json")
        if notifications_file.exists():
            try:
                with open(notifications_file, "r", encoding="utf-8") as f:
                    notifications = json.load(f)
            except Exception as e:
                logger.error(f"读取通知文件失败: {e}")
                notifications = []
        else:
            notifications = []
        
        # 添加新消息
        new_notification = {
            "time": current_time,
            "content": content
        }
        notifications.append(new_notification)
        
        # 写入文件
        try:
            with open(notifications_file, "w", encoding="utf-8") as f:
                json.dump(notifications, f, ensure_ascii=False, indent=2)
            
            # 清空输入框
            self.broadcast_input.clear()
            # 弹出成功提示
            QMessageBox.information(self, "成功", "通知发送成功")
            logger.info(f"发送广播消息: {content}")
        except Exception as e:
            logger.error(f"写入通知文件失败: {e}")
            QMessageBox.warning(self, "错误", "通知发送失败")
    
    def show_help_dialog(self):
        """显示帮助对话框（富文本美化版）"""
        from PySide6.QtWidgets import QDialog, QTextBrowser
        
        # 创建自定义对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("竞赛回收系统 - 使用指南")
        dialog.resize(650, 550)  # 给一个更宽敞的阅读尺寸
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(15, 15, 15, 15)

        # 使用 QTextBrowser 渲染 HTML
        text_browser = QTextBrowser(dialog)
        text_browser.setOpenExternalLinks(True)
        text_browser.setStyleSheet("border: none; background-color: #ffffff;")
        
        # 编写带有 CSS 样式的 HTML 内容
        html_content = """
        <style>
            body { font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif; font-size: 14px; color: #2d3748; line-height: 1.6; }
            h2 { color: #2b6cb0; text-align: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; margin-top: 0; }
            h3 { color: #2c5282; margin-top: 20px; margin-bottom: 10px; font-size: 15px; }
            ul { margin-top: 0; padding-left: 20px; margin-bottom: 10px; }
            li { margin-bottom: 6px; }
            code { background-color: #edf2f7; color: #e53e3e; padding: 2px 5px; border-radius: 4px; font-family: 'Consolas', monospace; }
            pre { background-color: #f7fafc; border: 1px solid #e2e8f0; padding: 12px; border-radius: 6px; font-family: 'Consolas', monospace; line-height: 1.4; color: #4a5568; margin-top: 5px; margin-bottom: 5px; font-size: 13px;}
            .note { background-color: #ebf8ff; border-left: 4px solid #4299e1; padding: 12px; margin-top: 20px; border-radius: 4px; }
        </style>

        <h2>📚 竞赛回收系统使用指南</h2>

        <h3>1. 初始化环境与基础配置</h3>
        <ul>
            <li>首次运行系统会自动生成 <code>students.csv</code> 和 <code>exam_instructions.md</code>。</li>
            <li>考前请务必编辑 <code>students.csv</code>，录入选手的<b>准考证号</b>、<b>姓名</b>和<b>密码</b>。</li>
            <li>可按需编辑 <code>exam_instructions.md</code> 来修改展示给选手的考试须知。</li>
        </ul>

        <h3>2. 配置题目 (problems.zip)</h3>
        <ul>
            <li>需将题目压缩为 <code>problems.zip</code> 并放置在项目根目录。</li>
            <li>系统会自动读取压缩包内的<b>【根目录文件夹名称】</b>作为题目列表分发给选手。</li>
            <li>标准的压缩包内部结构示例（注意对齐格式）：</li>
        </ul>
        <pre>
problems.zip
├── CSP2026-J.pdf  (PDF文件会自动排除在题目外，提供给选手下载)
├── apple/         (题目1文件夹，名称将显示为题目名)
├── tree/          (题目2文件夹)
└── graph/         (题目3文件夹)</pre>

        <h3>3. 开始考试</h3>
        <ul>
            <li>设置考试时长（分钟）和端口号（默认为 <code>8000</code>）。</li>
            <li>可选设置<b>【解压密码】</b>，填写后会在学生端醒目展示，方便对加密的下发试卷进行解密。</li>
            <li>点击“开始考试”启动服务，系统每次都会生成全新的动态安全密钥以防越权提交。</li>
        </ul>

        <h3>4. 考生登录与提交</h3>
        <ul>
            <li>局域网访问地址：<code>http://服务器IP:端口号</code> (例如：<code>http://192.168.1.100:8000</code>)</li>
            <li>选手使用 <code>students.csv</code> 中的准考证号和密码进行登录。</li>
            <li><b>提交规范</b>：目前系统限制选手仅能提交 <code>.cpp</code> 格式的源代码文件，且单文件大小不超过 <code>100KB</code>。重新提交会自动覆盖旧代码。</li>
        </ul>

        <div class="note">
            <b>💡 监考与结束收卷注意事项：</b><br>
            - 考试期间请保持主控台运行。可通过"消息广播"发布全员通知，选手端会自动弹窗提醒。<br>
            - 点击"结束考试"或倒计时归零后，系统自动拦截所有提交请求。<br>
            - 考试结束后，所有代码会按标准格式自动保存在根目录的 <code>data/准考证号/题目名/</code> 文件夹下，方便后续使用评测机集中评测。
        </div>
        """
        text_browser.setHtml(html_content)
        layout.addWidget(text_browser)

        # 添加一个底部居中的关闭按钮
        close_btn = QPushButton("我知道了", dialog)
        close_btn.setFixedSize(120, 36)
        close_btn.setStyleSheet("""
            QPushButton { background-color: #4299e1; color: white; border: none; border-radius: 4px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background-color: #3182ce; }
        """)
        close_btn.clicked.connect(dialog.accept)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        # 弹出对话框
        dialog.exec()


    def closeEvent(self, event):
        """关闭窗口事件"""
        # 停止服务器
        self.stop_server()
        # 保存状态
        self.save_state()
        # 停止日志读取定时器
        self.log_timer.stop()
        logger.info("主控台关闭")
        event.accept()


def run_server(port):
    """运行服务器"""
    try:
        from server import app  # 显式导入你的 app 实例
        # 注意这里去掉了字符串引号，直接传 app 对象
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=int(port)
        )
    except Exception as e:
        logger.error(f"服务器运行失败: {e}")


def main():
    """主函数"""
    import multiprocessing
    multiprocessing.freeze_support()  # 必须加这一行，否则打包后运行会电脑卡死
    # 初始化环境，生成缺失的模板文件
    init_environment()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
