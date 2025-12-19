import aiohttp
import asyncio
import logging
import sys
import os

# Add parent directory to path to allow importing config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SORA_CREATE_URL, SORA_QUERY_URL, USE_MOCK, SORA_MODEL, HTTP_PROXY

logger = logging.getLogger(__name__)

class SoraClient:
    def __init__(self):
        self.default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def generate_video(self, prompt: str, progress_cb, api_key: str = None, duration: int = 5, size: str = "large", orientation: str = "landscape", image: str = None, proxy: str = None):
        # 智能判断：如果没有提供 Key 且配置了 Mock 模式，才使用 Mock
        # 只要提供了 Key，就强制尝试真实调用
        should_use_mock = USE_MOCK and not api_key
        
        # 兼容旧代码调用 (如果有人传了 resolution 参数，虽然现在签名改了，但为了安全起见...)
        # 其实签名改了，旧的关键字参数调用会报错，所以这里假设调用方都已经更新了 (TaskManager 已更新)
        
        # 优先使用用户传入的代理，否则使用全局配置的代理
        request_proxy = proxy if proxy else HTTP_PROXY

        if should_use_mock:
            logger.info(f"[Mock] Generating video for prompt: {prompt}, duration: {duration}s, size: {size}, orientation: {orientation}, has_image: {bool(image)}")
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

        # 使用前端传递的 API Key 构建 Authorization 头
        headers = self.default_headers.copy()
        headers["Authorization"] = f"Bearer {api_key}"

        logger.info(f"Sending generation request to Sora: {prompt}, duration: {duration}s, size: {size}, orientation: {orientation}")
        async with aiohttp.ClientSession(headers=headers) as session:

            # ① 提交生成任务
            try:
                payload = {
                    "model": SORA_MODEL, # 使用配置中的 SORA_MODEL (应为 "sora-2-pro")
                    "prompt": prompt,
                    "duration": duration,
                    "size": size,
                    "orientation": orientation,
                    "watermark": False,
                    "private": True,
                    "images": [image] if image else []
                }

                async with session.post(
                    SORA_CREATE_URL,
                    json=payload,
                    proxy=request_proxy
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
            # status_url = f"{SORA_API_URL}/{task_id}"
            video_url = None
            local_progress = 10

            while True:
                await asyncio.sleep(2)

                try:
                    async with session.get(SORA_QUERY_URL, params={"id": task_id}, proxy=request_proxy) as resp:
                        resp.raise_for_status()
                        status_data = await resp.json()
                except Exception as e:
                    logger.error(f"Failed to poll status: {e}")
                    raise

                state = status_data["status"]
                logger.info(f"Task {task_id} status: {state}")

                if state == "processing" or state == "pending":
                    # 简单模拟进度增加
                    if state == "pending" and "detail" in status_data and "pending_info" in status_data["detail"]:
                         # 尝试获取真实进度
                         try:
                             real_progress = status_data["detail"]["pending_info"].get("progress_pct", 0)
                             local_progress = int(real_progress * 100)
                         except:
                             local_progress += 5
                    else:
                        local_progress += 5
                        
                    new_progress = min(90, local_progress)
                    progress_cb(new_progress)

                elif state == "completed" or state == "succeeded":
                    if "video_url" in status_data and status_data["video_url"]:
                        video_url = status_data["video_url"]
                    elif "detail" in status_data and "url" in status_data["detail"]:
                         video_url = status_data["detail"]["url"]
                    elif "output" in status_data and "video_url" in status_data["output"]:
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
                async with session.get(video_url, proxy=request_proxy) as resp:
                    resp.raise_for_status()
                    video_bytes = await resp.read()
            except Exception as e:
                logger.error(f"Failed to download video: {e}")
                raise

            progress_cb(100)
            return video_bytes
