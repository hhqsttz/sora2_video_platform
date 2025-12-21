import uuid
from enum import Enum
from typing import Optional

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

class VideoTask:
    def __init__(self, prompt: str, api_key: str = None, duration: int = 10, size: str = "large", orientation: str = "landscape", image: str = None, proxy: str = None, model: str = "sora-2", mode: str = "studio", character_url: str = None, character_timestamps: str = None, scenes: list = None):
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
        self.mode = mode
        self.character_url = character_url
        self.character_timestamps = character_timestamps
        self.scenes = scenes
        self.status = TaskStatus.PENDING
        self.progress = 0
        self.retry = 0
        self.result_path = None
        self.error = None

    def to_dict(self):
        # Convert Scene objects to dicts if they exist
        scenes_data = None
        if self.scenes:
            scenes_data = []
            for s in self.scenes:
                if hasattr(s, 'dict'):
                    scenes_data.append(s.dict())
                elif hasattr(s, '__dict__'):
                    scenes_data.append(s.__dict__)
                else:
                    scenes_data.append(s)

        return {
            "id": self.id,
            "prompt": self.prompt,
            "api_key": self.api_key,
            "duration": self.duration,
            "model": self.model,
            "size": self.size,
            "orientation": self.orientation,
            "image": self.image,
            "proxy": self.proxy,
            "mode": self.mode,
            "character_url": self.character_url,
            "character_timestamps": self.character_timestamps,
            "scenes": scenes_data,
            "status": self.status,
            "progress": self.progress,
            "retry": self.retry,
            "result_path": self.result_path,
            "error": self.error
        }

    @classmethod
    def from_dict(cls, data):
        task = cls(
            prompt=data.get("prompt", ""),
            api_key=data.get("api_key"),
            duration=data.get("duration", 10),
            size=data.get("size", "large"),
            orientation=data.get("orientation", "landscape"),
            image=data.get("image"),
            proxy=data.get("proxy"),
            model=data.get("model", "sora-2"),
            mode=data.get("mode", "studio"),
            character_url=data.get("character_url"),
            character_timestamps=data.get("character_timestamps"),
            scenes=data.get("scenes")
        )
        task.id = data.get("id", task.id)
        task.status = TaskStatus(data.get("status", "pending"))
        task.progress = data.get("progress", 0)
        task.retry = data.get("retry", 0)
        task.result_path = data.get("result_path")
        task.error = data.get("error")
        return task
