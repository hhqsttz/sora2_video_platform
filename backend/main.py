import asyncio
import logging
import os
import sys
import traceback

# Global exception handler to keep window open on crash
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    print("Uncaught exception:", file=sys.stderr)
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    input("Press Enter to exit...")

sys.excepthook = handle_exception

# Add current directory to sys.path to ensure local imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Response, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Literal
import shutil

from core.task import VideoTask
from core.task_manager import TaskManager
from state.memory import add_task, get_task, all_tasks, delete_task
from state.character_store import add_character, get_all_characters, delete_character
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

# 挂载前端静态资源 css 和 js
app.mount("/css", StaticFiles(directory=os.path.join(BASE_DIR, "frontend", "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(BASE_DIR, "frontend", "js")), name="js")

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
    prompt: Optional[str] = ""
    api_key: Optional[str] = None
    duration: Optional[int] = 10
    model: Optional[Literal["sora-2-pro", "sora-2"]] = "sora-2"
    size: Optional[Literal["large", "small"]] = "large"
    orientation: Optional[Literal["landscape", "portrait"]] = "landscape"
    image: Optional[str] = None  # Base64 string
    proxy: Optional[str] = None  # User provided proxy URL
    mode: Optional[str] = "studio" # "studio" or "storyboard"
    character_url: Optional[str] = None
    character_timestamps: Optional[str] = None

class CharacterRequest(BaseModel):
    timestamps: str
    from_task: Optional[str] = None
    url: Optional[str] = None
    name: Optional[str] = None
    permission: Optional[str] = None
    api_key: Optional[str] = None
    proxy: Optional[str] = None

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_path = os.path.join(OUTPUT_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Construct local URL (relative to server root)
        # Frontend can prepend origin
        return {"url": f"/outputs/{file.filename}", "filename": file.filename}
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/characters")
async def create_character(req: CharacterRequest):
    if not req.from_task and not req.url:
        raise HTTPException(status_code=400, detail="Either from_task or url must be provided")
    
    # Check if URL is a local file
    video_file_path = None
    if req.url and ("/outputs/" in req.url or "localhost" in req.url or "127.0.0.1" in req.url):
        # Extract filename
        try:
            filename = req.url.split("/")[-1]
            possible_path = os.path.join(OUTPUT_DIR, filename)
            if os.path.exists(possible_path):
                video_file_path = possible_path
                logger.info(f"Resolved local video path: {video_file_path}")
            else:
                logger.warning(f"Could not find local file for URL: {req.url}")
        except Exception as e:
            logger.warning(f"Error resolving local path: {e}")

    try:
        result = await manager.client.create_character(
            timestamps=req.timestamps,
            api_key=req.api_key,
            from_task=req.from_task,
            url=req.url,
            name=req.name,
            permission=req.permission,
            proxy=req.proxy,
            video_file_path=video_file_path
        )
        
        # Save character to persistent store
        char_data = result.copy()
        # Ensure we keep the custom name/permission if provided and not in result
        if req.name:
            char_data['name'] = req.name
        elif 'name' not in char_data:
            char_data['name'] = char_data.get('username', 'Unknown')
            
        if req.permission:
            char_data['permission'] = req.permission
        elif 'permission' not in char_data:
            char_data['permission'] = 'private'
            
        add_character(char_data)
        
        return result
    except Exception as e:
        logger.error(f"Failed to create character: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/characters")
def list_characters():
    return get_all_characters()

@app.delete("/characters/{char_id}")
def delete_character_endpoint(char_id: str):
    if delete_character(char_id):
        return {"status": "success"}
    else:
        raise HTTPException(status_code=404, detail="Character not found")

@app.delete("/tasks/{task_id}")
def delete_task_endpoint(task_id: str):
    if delete_task(task_id):
        return {"status": "success"}
    else:
        raise HTTPException(status_code=404, detail="Task not found")

@app.post("/tasks")
async def create_task(req: TaskRequest):
    # 安全校验：Base64 长度检查
    # 15MB 的 Base64 大约对应 11MB 的原始图片
    if req.image and len(req.image) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image payload too large (max ~10MB raw)")

    logger.info(f"Received new task request with prompt: {req.prompt}, duration: {req.duration}, model: {req.model}, size: {req.size}, orientation: {req.orientation}, has_image: {bool(req.image)}, proxy: {req.proxy}, mode: {req.mode}, character_url: {req.character_url}, character_timestamps: {req.character_timestamps}")
    # 注意：VideoTask 类也需要相应更新，或者我们在这里做一个简单的转换
    # 为了最小化修改，我们暂时将 size 和 orientation 组合成 resolution 字符串传递给 VideoTask，或者修改 VideoTask
    # 这里选择修改 VideoTask 更清晰
    task = VideoTask(req.prompt, req.api_key, req.duration, req.size, req.orientation, req.image, req.proxy, req.model, req.mode, req.character_url, req.character_timestamps)
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
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    except KeyboardInterrupt:
        print("Server stopped by user.")
    except Exception as e:
        print(f"Error starting server: {e}")
        input("Press Enter to exit...") # 让用户看到错误信息
