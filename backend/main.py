import asyncio
import logging
import os
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Literal

from core.task import VideoTask
from core.task_manager import TaskManager
from state.memory import add_task, get_task, all_tasks
from config import OUTPUT_DIR, BASE_DIR

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# 消除 favicon.ico 404 错误日志
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 挂载静态文件目录，使得 /outputs/xxx.mp4 可以访问
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")

# 挂载前端静态资源（如果有 css/js 文件夹），这里简单起见，直接映射根路由到 index.html
@app.get("/")
async def read_root():
    import sys
    # 如果是打包环境，前端资源通常被打包在 _MEIPASS 或同级目录
    # 这里我们假设打包时使用了 --add-data "frontend;frontend"，资源会被解压到 sys._MEIPASS/frontend
    if getattr(sys, 'frozen', False):
         # PyInstaller temp dir
        bundle_dir = sys._MEIPASS
        index_path = os.path.join(bundle_dir, "frontend", "index.html")
    else:
        # 开发环境
        index_path = os.path.join(BASE_DIR, "frontend", "index.html")
        
    return FileResponse(index_path)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = TaskManager()

class TaskRequest(BaseModel):
    prompt: str
    api_key: Optional[str] = None
    duration: Optional[int] = 5
    size: Optional[Literal["large", "medium", "small"]] = "large"
    orientation: Optional[Literal["landscape", "portrait", "square"]] = "landscape"
    image: Optional[str] = None  # Base64 string
    proxy: Optional[str] = None  # User provided proxy URL

@app.post("/tasks")
async def create_task(req: TaskRequest):
    # 安全校验：Base64 长度检查
    # 15MB 的 Base64 大约对应 11MB 的原始图片
    if req.image and len(req.image) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image payload too large (max ~10MB raw)")

    logger.info(f"Received new task request with prompt: {req.prompt}, duration: {req.duration}, size: {req.size}, orientation: {req.orientation}, has_image: {bool(req.image)}, proxy: {req.proxy}")
    # 注意：VideoTask 类也需要相应更新，或者我们在这里做一个简单的转换
    # 为了最小化修改，我们暂时将 size 和 orientation 组合成 resolution 字符串传递给 VideoTask，或者修改 VideoTask
    # 这里选择修改 VideoTask 更清晰
    task = VideoTask(req.prompt, req.api_key, req.duration, req.size, req.orientation, req.image, req.proxy)
    add_task(task)
    asyncio.create_task(manager.run_task(task))
    logger.info(f"Task created with ID: {task.id}")
    return {"task_id": task.id}

@app.get("/tasks/{task_id}")
def task_status(task_id: str):
    task = get_task(task_id)
    if not task:
        logger.warning(f"Task not found: {task_id}")
        return {"error": "not found"}
    # 过滤掉 api_key 和大图片数据
    task_dict = task.__dict__.copy()
    if 'api_key' in task_dict:
        del task_dict['api_key']
    if 'image' in task_dict and task_dict['image']:
        task_dict['has_image'] = True
        del task_dict['image']
    else:
        task_dict['has_image'] = False
        
    return task_dict

@app.get("/tasks")
def list_tasks():
    # 过滤掉 api_key 和大图片数据
    tasks = []
    for t in all_tasks():
        task_dict = t.__dict__.copy()
        if 'api_key' in task_dict:
            del task_dict['api_key']
        if 'image' in task_dict and task_dict['image']:
            task_dict['has_image'] = True
            del task_dict['image']
        else:
            task_dict['has_image'] = False
            
        tasks.append(task_dict)
    return tasks

if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import sys
    
    # Windows 下 PyInstaller 多进程支持
    # 虽然我们这里没有显式使用多进程，但为了稳健性加上
    from multiprocessing import freeze_support
    freeze_support()
    
    print("Starting Sora2 Video Platform...")
    print("Server running at: http://localhost:8000")
    print("Backend API Docs: http://localhost:8000/docs")
    print("Please wait while the server starts...")

    # 自动打开浏览器
    def open_browser():
        # 简单等待一下让服务器启动
        import time
        time.sleep(1.5) 
        webbrowser.open("http://localhost:8000")

    # 在新线程中打开浏览器，以免阻塞服务器启动
    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    # 启动服务器
    # 注意：在打包环境中不要使用 reload=True
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    except KeyboardInterrupt:
        print("Server stopped by user.")
    except Exception as e:
        print(f"Error starting server: {e}")
        input("Press Enter to exit...") # 让用户看到错误信息
