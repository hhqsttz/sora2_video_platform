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
            
            # Reset retry count if needed, or assume it starts at 0
            # task.retry is managed in the loop or persisted
            
            while True:
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
                        mode=task.mode,
                        character_url=task.character_url,
                        character_timestamps=task.character_timestamps,
                        scenes=task.scenes
                    )
                    task.result_path = save_video(task.id, data)
                    task.status = TaskStatus.DONE
                    save_tasks() # Save completion
                    break # Success, exit loop
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Task {task.id} failed (attempt {task.retry + 1}/{MAX_RETRY + 1}): {e}")
                    
                    task.retry += 1
                    if task.retry <= MAX_RETRY:
                        # Wait a bit before retrying
                        # If error is quota related or rate limit, wait longer
                        wait_time = 10
                        error_str = str(e).lower()
                        if "quota" in error_str or "limit" in error_str or "429" in error_str or "saturated" in error_str or "busy" in error_str:
                            wait_time = 30
                            logger.info(f"Rate limit/Quota error detected, waiting {wait_time}s...")
                        
                        await asyncio.sleep(wait_time)
                        continue # Retry
                    else:
                        task.status = TaskStatus.FAILED
                        task.error = str(e)
                        save_tasks() # Save failure
                        break # Give up
