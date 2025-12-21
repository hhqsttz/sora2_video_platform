from collections import OrderedDict
import json
import os
import logging
from core.task import VideoTask
from config import BASE_DIR

# 使用 OrderedDict 来模拟 LRU，限制最大任务数
MAX_TASKS = 100
TASKS = OrderedDict()

DATA_DIR = os.path.join(BASE_DIR, "data")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")

logger = logging.getLogger(__name__)

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def save_tasks():
    ensure_data_dir()
    data = [task.to_dict() for task in TASKS.values()]
    try:
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save tasks: {e}")

def load_tasks():
    global TASKS
    if not os.path.exists(TASKS_FILE):
        return

    try:
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Reconstruct TASKS
        new_tasks = OrderedDict()
        for task_data in data:
            try:
                task = VideoTask.from_dict(task_data)
                new_tasks[task.id] = task
            except Exception as e:
                logger.error(f"Failed to load task: {e}")
                
        # Handle limit if file has more than MAX_TASKS (though save respects it, maybe edited manually)
        while len(new_tasks) > MAX_TASKS:
            new_tasks.popitem(last=False)
            
        TASKS = new_tasks
        logger.info(f"Loaded {len(TASKS)} tasks from disk.")
    except Exception as e:
        logger.error(f"Failed to load tasks file: {e}")

def add_task(task):
    # 如果任务数超过限制，移除最早的一个（FIFO）
    if len(TASKS) >= MAX_TASKS:
        TASKS.popitem(last=False)
    TASKS[task.id] = task
    save_tasks()

def get_task(task_id):
    return TASKS.get(task_id)

def all_tasks():
    # 返回列表副本，避免迭代时修改
    return list(TASKS.values())

def delete_task(task_id):
    if task_id in TASKS:
        del TASKS[task_id]
        save_tasks()
        return True
    return False

# Initialize
load_tasks()
