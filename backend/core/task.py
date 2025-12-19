import uuid
from enum import Enum
from typing import Optional

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

class VideoTask:
    def __init__(self, prompt: str, api_key: str = None, duration: int = 5, resolution: str = "1080p", image: str = None):
        self.id = str(uuid.uuid4())
        self.prompt = prompt
        self.api_key = api_key
        self.duration = duration
        self.resolution = resolution
        self.image = image
        self.status = TaskStatus.PENDING
        self.progress = 0
        self.retry = 0
        self.result_path = None
        self.error = None
