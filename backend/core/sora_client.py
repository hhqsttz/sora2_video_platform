import aiohttp
import asyncio
import logging
import sys
import os

# Add parent directory to path to allow importing config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SORA_API_URL, USE_MOCK, SORA_MODEL

logger = logging.getLogger(__name__)

class SoraClient:
    def __init__(self):
        self.default_headers = {
            "Content-Type": "application/json"
        }

    async def generate_video(self, prompt: str, progress_cb, api_key: str = None, duration: int = 5, resolution: str = "1080p", image: str = None):
        # 智能判断：如果没有提供 Key 且配置了 Mock 模式，才使用 Mock
        # 只要提供了 Key，就强制尝试真实调用
        should_use_mock = USE_MOCK and not api_key

        if should_use_mock:
            logger.info(f"[Mock] Generating video for prompt: {prompt}, duration: {duration}s, resolution: {resolution}, has_image: {bool(image)}")
            # Simulate duration based on requested duration
            steps = 10
            sleep_time = max(0.5, duration / steps)
            for i in range(1, steps + 1):
                await asyncio.sleep(sleep_time)
                progress_cb(i * 10)
                logger.debug(f"[Mock] Progress: {i * 10}%")
            logger.info("[Mock] Video generation completed")
            return b"fake_video_content_mp4_header..."

        if not api_key:
             # 既没有 Key 也没开 Mock（或者 Mock 被上面逻辑跳过了但 Key 为空）
             raise ValueError("API Key is required for real requests")

        headers = self.default_headers.copy()
        headers["Authorization"] = f"Bearer {api_key}"

        logger.info(f"Sending generation request to Sora: {prompt}, duration: {duration}s, resolution: {resolution}")
        async with aiohttp.ClientSession(headers=headers) as session:

            # ① 提交生成任务
            try:
                payload = {
                    "model": SORA_MODEL,
                    "prompt": prompt,
                    "seconds": duration,
                    "size": resolution
                }
                if image:
                    payload["input_reference"] = image

                async with session.post(
                    SORA_API_URL,
                    json=payload
                ) as resp:
                    if not resp.ok:
                        error_text = await resp.text()
                        logger.error(f"Sora API error: {resp.status} - {error_text}")
                        resp.raise_for_status()
                    
                    data = await resp.json()
                    task_id = data["id"]
                    logger.info(f"Sora task submitted, ID: {task_id}")
            except Exception as e:
                logger.error(f"Failed to submit task: {e}")
                raise

            progress_cb(10)

            # ② 轮询状态
            status_url = f"{SORA_API_URL}/{task_id}"
            video_url = None
            local_progress = 10

            while True:
                await asyncio.sleep(2)

                try:
                    async with session.get(status_url) as resp:
                        resp.raise_for_status()
                        status_data = await resp.json()
                except Exception as e:
                    logger.error(f"Failed to poll status: {e}")
                    raise

                state = status_data["status"]
                logger.info(f"Task {task_id} status: {state}")

                if state == "processing":
                    # 简单模拟进度增加
                    local_progress += 5
                    new_progress = min(90, local_progress)
                    progress_cb(new_progress)

                elif state == "completed" or state == "succeeded":
                    if "output" in status_data and "video_url" in status_data["output"]:
                        video_url = status_data["output"]["video_url"]
                    else:
                        # Fallback or error if structure is different
                        logger.warning(f"Unexpected status data structure: {status_data}")
                        # Try to find url in other common fields or raise error
                        raise RuntimeError("Video URL not found in response")
                    break

                elif state == "failed":
                    error_msg = status_data.get("error", "Unknown error")
                    logger.error(f"Sora task failed: {error_msg}")
                    raise RuntimeError(f"Sora2 task failed: {error_msg}")

            progress_cb(95)

            # ③ 下载视频
            logger.info(f"Downloading video from {video_url}")
            try:
                async with session.get(video_url) as resp:
                    resp.raise_for_status()
                    video_bytes = await resp.read()
            except Exception as e:
                logger.error(f"Failed to download video: {e}")
                raise

            progress_cb(100)
            return video_bytes
