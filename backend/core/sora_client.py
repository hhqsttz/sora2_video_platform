import aiohttp
import asyncio
import logging
import sys
import os
import base64

# Add parent directory to path to allow importing config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SORA_CREATE_URL, SORA_QUERY_URL, SORA_STORYBOARD_URL, USE_MOCK, SORA_MODEL, HTTP_PROXY

logger = logging.getLogger(__name__)

class SoraClient:
    def __init__(self):
        self.default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def generate_video(self, prompt: str, progress_cb, api_key: str = None, duration: int = 5, size: str = "large", orientation: str = "landscape", image: str = None, proxy: str = None, model: str = "sora-2-pro"):
        # 优先使用用户传入的代理，否则使用全局配置的代理
        request_proxy = proxy if proxy else HTTP_PROXY

        if not api_key:
             # Key 为空
             raise ValueError("API Key is required for real requests")

        # 使用前端传递的 API Key 构建 Authorization 头
        headers = self.default_headers.copy()
        headers["Authorization"] = f"Bearer {api_key}"

        # 如果有图片，使用 Multipart/Form-Data，移除默认的 Content-Type
        if image and "Content-Type" in headers:
            del headers["Content-Type"]

        # Map friendly names to API values
        orientation_map = {
            "landscape": "16:9",
            "portrait": "9:16",
            "square": "1:1"
        }
        api_orientation = orientation_map.get(orientation, orientation)

        size_map = {
            "large": "1080p",
            "medium": "720p",
            "small": "480p"
        }
        api_size = size_map.get(size, size)

        logger.info(f"Sending generation request to Sora: {prompt}, duration: {duration}s, size: {api_size} (mapped from {size}), orientation: {api_orientation} (mapped from {orientation}), model: {model}, has_image: {bool(image)}")
        async with aiohttp.ClientSession(headers=headers) as session:

            # ① 提交生成任务
            try:
                if image:
                    # Storyboard mode (Multipart)
                    logger.info("Using Storyboard mode with image upload")
                    
                    # Handle Base64 image
                    if "," in image:
                        header, encoded = image.split(",", 1)
                    else:
                        encoded = image
                    image_bytes = base64.b64decode(encoded)
                    
                    data = aiohttp.FormData()
                    # Field name based on user request
                    data.add_field('input_reference', image_bytes, filename='storyboard.jpg', content_type='image/jpeg')
                    
                    # Add other fields
                    data.add_field('prompt', prompt)
                    data.add_field('model', model)
                    # duration causes type error in multipart (string vs int), passing via query param or omitting from body
                    # data.add_field('duration', str(duration)) 
                    data.add_field('size', api_size)
                    data.add_field('orientation', api_orientation)
                    
                    # Pass duration as query param to handle int type correctly in Go backends
                    params = {"duration": duration}

                    async with session.post(
                        SORA_STORYBOARD_URL,
                        data=data,
                        params=params,
                        proxy=request_proxy
                    ) as resp:
                        if not resp.ok:
                            error_text = await resp.text()
                            logger.error(f"Sora Storyboard API error: {resp.status} - {error_text}")
                            resp.raise_for_status()
                        
                        data = await resp.json()
                        task_id = data["id"]
                        logger.info(f"Sora Storyboard task submitted, ID: {task_id}")
                else:
                    # Standard mode (JSON)
                    payload = {
                        "model": model, # 使用传入的 model 参数
                        "prompt": prompt,
                        "duration": duration,
                        "size": api_size,
                        "orientation": api_orientation,
                        "watermark": False,
                        "private": True,
                        "images": []
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
            download_max_retries = 3
            video_bytes = None
            
            for attempt in range(download_max_retries):
                try:
                    # 设置较长的超时时间，防止大文件下载中断
                    timeout = aiohttp.ClientTimeout(total=300) # 5 minutes
                    async with session.get(video_url, proxy=request_proxy, timeout=timeout) as resp:
                        if resp.status != 200:
                            logger.warning(f"Download attempt {attempt + 1} failed with status {resp.status}")
                            resp.raise_for_status()
                        
                        video_bytes = await resp.read()
                        logger.info("Video downloaded successfully")
                        break # Download successful, exit loop
                except Exception as e:
                    logger.error(f"Failed to download video (Attempt {attempt + 1}/{download_max_retries}): {e}")
                    if attempt < download_max_retries - 1:
                        wait_time = (attempt + 1) * 5
                        logger.info(f"Retrying download in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                    else:
                        # 此时已达到最大重试次数，抛出异常
                        # 注意：这里抛出异常会导致 TaskManager 认为任务失败，从而触发整个任务（包括生成）的重试
                        # 如果是网络问题导致的下载失败，这可能是期望的行为（换个节点重试？）
                        # 但如果是文件本身有问题，重试生成也是合理的
                        # 为了避免无限消耗配额，建议 TaskManager 层控制最大重试次数（已有 MAX_RETRY）
                        raise RuntimeError(f"Failed to download video after {download_max_retries} attempts: {e}")

            progress_cb(100)
            return video_bytes
