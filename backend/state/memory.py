from collections import OrderedDict

# 使用 OrderedDict 来模拟 LRU，限制最大任务数
MAX_TASKS = 100
TASKS = OrderedDict()

def add_task(task):
    # 如果任务数超过限制，移除最早的一个（FIFO）
    if len(TASKS) >= MAX_TASKS:
        TASKS.popitem(last=False)
    TASKS[task.id] = task

def get_task(task_id):
    return TASKS.get(task_id)

def all_tasks():
    # 返回列表副本，避免迭代时修改
    return list(TASKS.values())
