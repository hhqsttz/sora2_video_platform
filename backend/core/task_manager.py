import asyncio
from core.task import TaskStatus
from core.sora_client import SoraClient
from storage.saver import save_video
from config import MAX_CONCURRENT, MAX_RETRY
from state.memory import save_tasks

class TaskManager:
    def __init__(self):
        self.sem = asyncio.Semaphore(MAX_CONCURRENT)
        self.client = SoraClient()

    async def run_task(self, task):
        async with self.sem:
            task.status = TaskStatus.RUNNING
            save_tasks() # Save status change
            try:
                def progress_cb(p):
                    task.progress = p
                    # Optional: save_tasks() on progress? Might be too frequent.
                    # Let's just save on major status changes.

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
                    mode=task.mode,
                    character_url=task.character_url,
                    character_timestamps=task.character_timestamps
                )
                task.result_path = save_video(task.id, data)
                task.status = TaskStatus.DONE
                save_tasks() # Save completion
            except Exception as e:
                task.retry += 1
                if task.retry <= MAX_RETRY:
                    await self.run_task(task)
                else:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    save_tasks() # Save failure
