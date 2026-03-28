#!/usr/bin/env python3
"""
竞赛回收系统 - 服务器文件
使用 FastAPI 构建 RESTful API
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from pathlib import Path
import zipfile
import csv
import asyncio
import aiofiles
from jose import JWTError, jwt
import os
import sys
import json
import time
import logging
import hashlib
import secrets

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("system.log", encoding="utf-8", mode="a"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="竞赛回收系统 API",
    description="用于竞赛代码的上传和管理",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 获取 PyInstaller 解压后的临时路径，如果没打包则使用当前执行路径
if getattr(sys, 'frozen', False):
    # 打包后的运行环境（临时目录）
    base_path = Path(sys._MEIPASS)
else:
    # 开发时的运行环境
    base_path = Path(__file__).parent

# 配置模板和静态文件 (使用 base_path 绝对路径)
templates = Jinja2Templates(directory=str(base_path / "templates"))

# 创建/绑定静态文件目录 (使用 base_path 绝对路径)
static_dir = base_path / "static"
# 注意：在开发环境下如果 static 文件夹不存在则创建它
if not getattr(sys, 'frozen', False):
    static_dir.mkdir(exist_ok=True)
    
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 算法，用于 JWT 签名
ALGORITHM = "HS256"


def get_secret_key():
    """从 .exam_state.json 文件中获取密钥
    如果文件不存在或发生异常，返回一个保底的随机字符串
    """
    state_file = Path("./.exam_state.json")
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            secret_key = state.get("secret_key")
            if secret_key:
                return secret_key
        except Exception as e:
            logger.error(f"读取密钥失败: {e}")
    # 如果不存在或发生异常，返回一个保底的随机字符串
    return secrets.token_hex(32)

# 题目列表缓存
problem_list = []

# 考场防作弊与单点登录状态记录 
account_ip_map = {}  # 记录 账号 -> 最新登录的IP
ip_account_map = {}  # 记录 IP -> 最新登录的账号


def get_problems():
    """获取题目列表
    读取 problems.zip，获取根目录下的子文件夹名称作为题目列表
    支持智能判断并剥离"外层套壳文件夹"（如外层多套了一个 problems 文件夹）
    处理中文文件名乱码问题
    """
    global problem_list
    if problem_list:
        return problem_list
    
    problems_zip = Path("./problems.zip")
    if not problems_zip.exists():
        return []
    
    try:
        with zipfile.ZipFile(problems_zip, 'r') as zf:
            file_list = zf.namelist()
            
            # 1. 过滤并提前解码所有有效路径 (提前解码便于准确解析目录结构)
            valid_paths = []
            for item in file_list:
                # 排除 macOS 系统文件和隐藏文件
                if item.startswith('__MACOSX') or '.DS_Store' in item:
                    continue
                # 处理中文乱码
                try:
                    decoded = item.encode('cp437').decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        decoded = item.encode('cp437').decode('gbk')
                    except UnicodeDecodeError:
                        decoded = item
                valid_paths.append(decoded)
            
            # 2. 梳理第一层结构
            root_dirs = set()
            root_items = set()
            
            for p in valid_paths:
                parts = p.split('/')
                if not parts[0]:
                    continue
                root_items.add(parts[0])
                # 如果有超过一级，或者以/结尾，说明这是一个文件夹
                if len(parts) > 1 and parts[1] != "":
                    root_dirs.add(parts[0])
                elif p.endswith('/'):
                    root_dirs.add(parts[0])
                    
            # 剔除根目录下的说明文件 (如 pdf)
            root_problems = {item for item in root_items if not item.endswith('.pdf')}
            
            # 3. 智能判断"单层嵌套" (套壳文件夹)
            # 触发条件：压缩包根目录下只有 1 个真正的文件夹（可能有同级的 pdf）
            if len(root_dirs) == 1 and len(root_problems) == 1:
                wrapper_dir = list(root_dirs)[0]
                
                sub_dirs = set()
                direct_files = set()
                
                # 收集该可能套壳的文件夹下的内部直接内容
                for p in valid_paths:
                    parts = p.split('/')
                    if len(parts) > 1 and parts[0] == wrapper_dir:
                        second = parts[1]
                        if not second:
                            continue
                        if len(parts) > 2 and parts[2] != "":
                            sub_dirs.add(second)
                        elif p.endswith('/'):
                            sub_dirs.add(second)
                        else:
                            direct_files.add(second)
                            
                # 排除说明类型文件，看该目录下是否有实际的测试数据文件 (in, out, ans, cpp等)
                data_files = [f for f in direct_files if not f.endswith(('.pdf', '.md', '.txt', '.doc', '.docx', '.html', '.htm'))]
                
                is_wrapper = False
                if len(data_files) == 0 and len(sub_dirs) > 0:
                    if len(sub_dirs) > 1:
                        # 包含多个子文件夹，且没有游离的数据文件，100% 是套壳文件夹
                        is_wrapper = True
                    else:
                        # 只有 1 个子文件夹，深度判断它是套壳，还是本来就是单道题
                        sub_dir_name = list(sub_dirs)[0].lower()
                        container_names = ['problems', 'problem', '题目', '试题', 'data', '数据', 'contest', 'task', 'tasks']
                        if wrapper_dir.lower() in container_names:
                            is_wrapper = True
                        elif sub_dir_name in ['testdata', 'data', 'src', 'source', '测试数据', 'down']:
                            # 子文件夹明显是内层数据包(testdata等)，说明外层就是题目名，不是套壳
                            is_wrapper = False
                        else:
                            is_wrapper = True
                            
                if is_wrapper:
                    # 确认为套壳文件夹，剥离外层，提取第二层文件夹作为题目列表
                    problem_list = sorted([d for d in sub_dirs if not d.endswith('.pdf')])
                    return problem_list
                    
            # 4. 如果不是套壳（例如有多个题目文件夹在根目录），直接提取第一层作为题目
            problem_list = sorted(list(root_problems))
            return problem_list
            
    except Exception as e:
        logger.error(f"解析 problems.zip 失败: {e}")
        return []

def verify_token(token: str):
    """验证 JWT token
    返回 token 中的准考证号
    """
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        student_id: str = payload.get("sub")
        if student_id is None:
            raise HTTPException(status_code=401, detail="无效的 token")

        return student_id
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的 token")


def authenticate_student(student_id: str, password: str):
    """验证学生身份
    从 students.csv 中查找学生信息
    """
    students_csv = Path("./students.csv")
    if not students_csv.exists():
        return False
    
    try:
        with open(students_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("exam_id") == student_id:
                    # 验证密码
                    return row.get("password") == password
        return False
    except Exception as e:
        logger.error(f"读取 students.csv 失败: {e}")
        return False


@app.get("/")
def read_root(request: Request):
    """根路径，渲染前端页面"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/download/problems")
def download_problems():
    """下载 problems.zip 文件"""
    problems_zip = Path("./problems.zip")
    if not problems_zip.exists():
        raise HTTPException(status_code=404, detail="problems.zip 文件不存在")
    return FileResponse(path=problems_zip, filename="problems.zip", media_type="application/zip")


@app.get("/api/instructions")
def get_instructions():
    """获取考试说明"""
    instructions_file = Path("./exam_instructions.md")
    if not instructions_file.exists():
        raise HTTPException(status_code=404, detail="exam_instructions.md 文件不存在")
    with open(instructions_file, "r", encoding="utf-8") as f:
        content = f.read()
    return {"content": content}


@app.get("/api/status")
def get_status():
    """获取考试状态"""
    state_file = Path("./.exam_state.json")
    if not state_file.exists():
        return {"is_running": False, "end_timestamp": 0, "password": ""}
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
        return {
            "is_running": state.get("is_running", False),
            "end_timestamp": state.get("end_timestamp", 0),
            "password": state.get("password", "")
        }
    except Exception as e:
        logger.error(f"读取状态文件失败: {e}")
        return {"is_running": False, "end_timestamp": 0, "password": ""}


@app.get("/api/notifications")
def get_notifications():
    """获取通知列表"""
    notifications_file = Path("./notifications.json")
    if not notifications_file.exists():
        return []
    try:
        with open(notifications_file, "r", encoding="utf-8") as f:
            notifications = json.load(f)
        return notifications
    except Exception as e:
        logger.error(f"读取通知文件失败: {e}")
        return []


@app.post("/api/login")
def login(student_id: str = Form(...), password: str = Form(...), request: Request = None):
    """登录接口
    接收准考证号和密码，与 students.csv 比对
    成功后返回 JWT token
    """
    client_ip = request.client.host if request else "未知"
    if authenticate_student(student_id, password):
        # IP 异常检测与主控台报警 
        if client_ip != "未知" and client_ip != "127.0.0.1":
            # 检测 1：防代考/串号（这台电脑之前登录过别的账号吗？）
            if client_ip in ip_account_map and ip_account_map[client_ip] != student_id:
                logger.warning(f"🚨 [异常报警] 电脑IP {client_ip} 原本登录的是 {ip_account_map[client_ip]}，现在尝试登录 {student_id}！")
            
            # 检测 2：防异地登录（这个账号之前在别的电脑登录过吗？）
            if student_id in account_ip_map and account_ip_map[student_id] != client_ip:
                logger.warning(f"🚨 [异地登录] 考生 {student_id} 原本在 {account_ip_map[student_id]} 考试，现在换到了 {client_ip} 登录！")

        # 生成 JWT token
        payload = {"sub": student_id}
        token = jwt.encode(payload, get_secret_key(), algorithm=ALGORITHM)

        # 更新全局绑定关系（覆盖旧数据，使最新登录生效） 
        account_ip_map[student_id] = client_ip
        ip_account_map[client_ip] = student_id

        # 记录登录成功日志
        logger.info(f"[LOGIN] exam_id: {student_id} | IP: {client_ip}")
        return {"access_token": token, "token_type": "bearer"}
    else:
        # 记录登录失败日志
        logger.warning(f"[LOGIN FAILED] exam_id: {student_id} | IP: {client_ip}")
        raise HTTPException(status_code=401, detail="准考证号或密码错误")


@app.get("/api/problems")
def get_problem_list(authorization: str = Header(...)):
    """获取题目接口
    需要校验 Token，校验通过后返回题目列表及提交状态
    """
    # 提取 token
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="无效的 authorization 头")
    token = authorization.split(" ")[1]
    
    # 验证 token
    student_id = verify_token(token)
    
    # 获取题目列表
    problem_names = get_problems()
    
    # 构建包含提交状态的题目列表
    problems = []
    for problem_name in problem_names:
        # 检查提交状态
        problem_dir = Path("./data") / student_id / problem_name
        submitted = False
        filename = ""
        size = ""
        submit_time = ""
        
        if problem_dir.exists():
            # 查找 .cpp 文件
            cpp_files = list(problem_dir.glob("*.cpp"))
            if cpp_files:
                cpp_file = cpp_files[0]
                submitted = True
                filename = cpp_file.name
                
                # 计算文件大小（KB）
                size_kb = cpp_file.stat().st_size / 1024
                size = f"{size_kb:.1f} KB"
                
                # 格式化最后修改时间
                mtime = cpp_file.stat().st_mtime
                submit_time = time.strftime("%H:%M:%S", time.localtime(mtime))
        
        problems.append({
            "name": problem_name,
            "submitted": submitted,
            "filename": filename,
            "size": size,
            "submit_time": submit_time
        })
    
    return {"problems": problems}


@app.post("/api/upload")
async def upload_code(
    file: UploadFile = File(...),
    problem_name: str = Form(...),
    authorization: str = Header(...),
    request: Request = None
):
    """上传代码接口
    接收上传的 .cpp 文件和对应的题目名称
    校验 Token，从 Token 中提取准考证号
    将文件异步保存到指定目录
    """
    # 获取学生 IP 地址
    client_ip = request.client.host if request else "未知"
    
    # 提取 token
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="无效的 authorization 头")
    token = authorization.split(" ")[1]
    
    # 验证 token
    student_id = verify_token(token)
    
    # 检查考试状态
    state_file = Path("./.exam_state.json")
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            is_running = state.get("is_running", False)
            end_timestamp = state.get("end_timestamp", 0)
            current_time = time.time()
            
            if not is_running or current_time > end_timestamp:
                # 记录考试结束后尝试提交的日志
                logger.warning(f"[DENY] exam_id: {student_id} | 尝试在考试结束后提交 | IP: {client_ip}")
                raise HTTPException(status_code=403, detail="考试已结束，禁止提交代码")
        except Exception as e:
            logger.error(f"读取状态文件失败: {e}")
    
    # 验证文件类型
    if not file.filename.endswith(".cpp"):
        raise HTTPException(status_code=400, detail="只支持上传 .cpp 文件")
    
    # 读取文件内容并检查大小
    content = await file.read()
    if len(content) > 100 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过100KB")
    
    # 计算文件哈希值
    file_hash = hashlib.sha256(content).hexdigest()
    
    # 创建保存目录
    save_dir = Path("./data") / student_id / problem_name
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存文件，使用原始文件名
    file_path = save_dir / file.filename
    
    # 使用 aiofiles 异步写入
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)
    
    # 计算文件大小
    file_size = len(content) / 1024
    
    # 记录上传成功日志
    logger.info(f"[SUBMIT] exam_id: {student_id} | 题目: {problem_name} | 文件名: {file.filename} | 大小: {file_size:.1f}KB | 哈希(sha256): {file_hash} | IP: {client_ip}")
    
    return {
        "message": "文件上传成功",
        "student_id": student_id,
        "problem_name": problem_name,
        "file_path": str(file_path)
    }


@app.get("/api/view_code")
def view_code(
    problem_name: str,
    authorization: str = Header(...)
):
    """查看代码接口
    接收题目名称和 Token
    校验 Token 后，返回对应题目的代码内容
    """
    # 提取 token
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="无效的 authorization 头")
    token = authorization.split(" ")[1]
    
    # 验证 token
    student_id = verify_token(token)
    
    # 检查目录是否存在
    save_dir = Path("./data") / student_id / problem_name
    if not save_dir.exists():
        raise HTTPException(status_code=404, detail="代码不存在")
    
    # 查找 .cpp 文件
    cpp_files = list(save_dir.glob("*.cpp"))
    if not cpp_files:
        raise HTTPException(status_code=404, detail="代码不存在")
    
    # 读取第一个 .cpp 文件
    cpp_file = cpp_files[0]
    try:
        with open(cpp_file, "r", encoding="utf-8") as f:
            code = f.read()
        return {
            "code": code,
            "filename": cpp_file.name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="读取代码失败")


@app.get("/api/me")
def get_current_student(authorization: str = Header(...)):
    """获取当前学生信息接口
    要求携带 Token，返回安全的学生信息（exam_id 和 name）
    """
    # 提取 token
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="无效的 authorization 头")
    token = authorization.split(" ")[1]
    
    # 验证 token
    student_id = verify_token(token)
    
    # 读取 students.csv 文件
    students_csv = Path("./students.csv")
    if not students_csv.exists():
        raise HTTPException(status_code=404, detail="学生信息不存在")
    
    try:
        with open(students_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("exam_id") == student_id:
                    # 只返回安全的字段，不返回 password
                    return {
                        "exam_id": row["exam_id"],
                        "name": row["name"]
                    }
        # 没找到匹配的学生
        raise HTTPException(status_code=404, detail="学生信息不存在")
    except Exception as e:
        logger.error(f"读取 students.csv 失败: {e}")
        raise HTTPException(status_code=500, detail="获取学生信息失败")
