import asyncio
from core.task import TaskStatus
from core.sora_client import SoraClient
from storage.saver import save_video
from config import MAX_CONCURRENT, MAX_RETRY

class TaskManager:
    def __init__(self):
        self.sem = asyncio.Semaphore(MAX_CONCURRENT)
        self.client = SoraClient()

    async def run_task(self, task):
        async with self.sem:
            task.status = TaskStatus.RUNNING
            try:
                def progress_cb(p):
                    task.progress = p

                data = await self.client.generate_video(
                    prompt=task.prompt, 
                    progress_cb=progress_cb, 
                    api_key=task.api_key,
                    duration=task.duration,
                    size=task.size,
                    orientation=task.orientation,
                    image=task.image,
                    proxy=task.proxy,
                    model=task.model,
                    mode=task.mode
                )
                task.result_path = save_video(task.id, data)
                task.status = TaskStatus.DONE
            except Exception as e:
                task.retry += 1
                if task.retry <= MAX_RETRY:
                    await self.run_task(task)
                else:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
