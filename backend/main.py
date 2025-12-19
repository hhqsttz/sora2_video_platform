import asyncio
import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from core.task import VideoTask
from core.task_manager import TaskManager
from state.memory import add_task, get_task, all_tasks
from config import OUTPUT_DIR

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 挂载静态文件目录，使得 /outputs/xxx.mp4 可以访问
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")

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
    resolution: Optional[str] = "1080p"
    image: Optional[str] = None  # Base64 string

@app.post("/tasks")
async def create_task(req: TaskRequest):
    # 安全校验：Base64 长度检查
    # 15MB 的 Base64 大约对应 11MB 的原始图片
    if req.image and len(req.image) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image payload too large (max ~10MB raw)")

    logger.info(f"Received new task request with prompt: {req.prompt}, duration: {req.duration}, resolution: {req.resolution}, has_image: {bool(req.image)}")
    task = VideoTask(req.prompt, req.api_key, req.duration, req.resolution, req.image)
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
