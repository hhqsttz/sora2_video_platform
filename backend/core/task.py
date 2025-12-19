import uuid
from enum import Enum
from typing import Optional

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

class VideoTask:
    def __init__(self, prompt: str, api_key: str = None, duration: int = 5, size: str = "large", orientation: str = "landscape", image: str = None, proxy: str = None, model: str = "sora-2-pro"):
        self.id = str(uuid.uuid4())
        self.prompt = prompt
        self.api_key = api_key
        self.duration = duration
        self.model = model
        self.size = size
        self.orientation = orientation
        self.resolution = f"{size} / {orientation}" # 保留 resolution 字段用于向后兼容或显示
        self.image = image
        self.proxy = proxy
        self.status = TaskStatus.PENDING
        self.progress = 0
        self.retry = 0
        self.result_path = None
        self.error = None
