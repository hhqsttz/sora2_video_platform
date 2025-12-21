import aiohttp
import asyncio
import logging
import sys
import os
import base64

# Add parent directory to path to allow importing config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SORA_CREATE_URL, SORA_QUERY_URL, SORA_STORYBOARD_URL, SORA_CHARACTERS_URL, USE_MOCK, SORA_MODEL, HTTP_PROXY

logger = logging.getLogger(__name__)

class SoraClient:
    def __init__(self):
        self.default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _parse_timestamps(self, timestamps):
        if not timestamps:
            return []
        if isinstance(timestamps, list):
            return timestamps
        # Split by comma, hyphen or space
        import re
        try:
            # Replace common separators with space
            clean_ts = re.sub(r'[,\-\s]+', ' ', str(timestamps).strip())
            parts = clean_ts.split()
            return [float(p) for p in parts if p]
        except Exception as e:
            logger.warning(f"Failed to parse timestamps '{timestamps}': {e}")
            return timestamps

    async def generate_video(self, prompt, progress_cb, api_key=None, duration=10, size="large", orientation="landscape", image=None, proxy=None, model="sora-2", mode="studio", character_url=None, character_timestamps=None):
        # 优先使用用户传入的代理，否则使用全局配置的代理
        request_proxy = proxy if proxy else HTTP_PROXY

        if not api_key:
             # Key 为空
             raise ValueError("API Key is required for real requests")

        # 使用前端传递的 API Key 构建 Authorization 头
        headers = self.default_headers.copy()
        headers["Authorization"] = f"Bearer {api_key}"

        # 如果是 Storyboard 模式且有图片，使用 Multipart/Form-Data，移除默认的 Content-Type
        if mode == 'storyboard' and image and "Content-Type" in headers:
            del headers["Content-Type"]

        # Map friendly names to API values
        # API expects specific resolution strings (e.g. "1920x1080") instead of "large"/"medium"
        api_orientation = orientation
        
        if mode == 'storyboard':
            # Storyboard mode: size is aspect ratio string (e.g. "16x9"), ignores specific resolution
            if orientation == "portrait":
                api_size = "9x16"
            else: # landscape
                api_size = "16x9"
        else:
            # Studio mode: Calculate resolution based on size and orientation
            # Supported sizes: large (1080p), small (720p)
            # Supported orientations: landscape (16:9), portrait (9:16)
            if size == "large":
                if orientation == "portrait":
                    api_size = "1080x1920"
                else: # landscape (default)
                    api_size = "1920x1080"
            elif size == "small": # re-purposing small as 720p
                if orientation == "portrait":
                    api_size = "720x1280"
                else: # landscape
                    api_size = "1280x720"
            else: # default/fallback to large landscape
                api_size = "1920x1080"
            
            # Fallback if size is already in resolution format (e.g. passed directly)
            if "x" in size and size not in ["large", "medium", "small"]:
                 api_size = size
 
        logger.info(f"Sending generation request to Sora ({mode}): {prompt}, duration: {duration}s, size: {api_size}, orientation: {api_orientation}, model: {model}, has_image: {bool(image)}")
        async with aiohttp.ClientSession(headers=headers) as session:
 
            # ① 提交生成任务
            try:
                if mode == 'storyboard':
                    # Storyboard mode (Multipart)
                    logger.info("Using Storyboard mode (Multipart)")
                    
                    data = aiohttp.FormData()
                    
                    if image:
                        # Handle Base64 image
                        if "," in image:
                            header, encoded = image.split(",", 1)
                        else:
                            encoded = image
                        image_bytes = base64.b64decode(encoded)
                        # Field name based on user request
                        data.add_field('input_reference', image_bytes, filename='storyboard.jpg', content_type='image/jpeg')
                    
                    # Add other fields
                    data.add_field('prompt', prompt)
                    data.add_field('model', model)
                    data.add_field('size', api_size)
                    data.add_field('seconds', str(duration))
                    data.add_field('watermark', 'false')
                    data.add_field('private', 'false')
                    async with session.post(
                        SORA_STORYBOARD_URL,
                        data=data,
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
                    # Standard mode / Creation Center (JSON)
                    logger.info("Using Studio mode (JSON)")
                    
                    # Prepare images list if image is present
                    images_list = []
                    if image:
                        # Remove header if present (e.g. "data:image/jpeg;base64,")
                        if "," in image:
                            _, encoded = image.split(",", 1)
                            images_list.append(encoded)
                        else:
                            images_list.append(image)

                    payload = {
                        "model": model, # 使用传入的 model 参数
                        "prompt": prompt,
                        "duration": int(duration), # Force int
                        "size": api_size,
                        "orientation": api_orientation,
                        "watermark": False,
                        "private": True,
                        "images": images_list
                    }

                    if character_url and character_timestamps:
                        payload["character"] = {
                            "url": character_url,
                            "timestamps": self._parse_timestamps(character_timestamps)
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

                if state == "processing" or state == "pending" or state == "queued":
                    # 优先使用 API 返回的进度
                    if "progress" in status_data:
                        local_progress = status_data["progress"]
                    # 其次尝试从 detail 中获取
                    elif (state == "pending" or state == "queued") and "detail" in status_data and "pending_info" in status_data["detail"]:
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

    async def upload_file_to_proxy(self, file_path: str, api_key: str, proxy: str = None):
        """
        Uploads a file to the proxy to get a public URL.
        """
        request_proxy = proxy if proxy else HTTP_PROXY
        upload_url = "https://imageproxy.zhongzhuan.chat/api/upload"
        
        if not os.path.exists(file_path):
             raise FileNotFoundError(f"File not found: {file_path}")
             
        logger.info(f"Starting proxy upload for file: {file_path}")
        
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        data = aiohttp.FormData()
        filename = os.path.basename(file_path)
        # Determine content type based on extension
        import mimetypes
        content_type, _ = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = 'application/octet-stream'
            
        # Open file in binary mode
        with open(file_path, 'rb') as f:
            data.add_field('file', f, filename=filename, content_type=content_type)
            
            logger.info(f"Posting to {upload_url}...")
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.post(upload_url, data=data, proxy=request_proxy) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"Proxy upload failed. Status: {resp.status}, Response: {error_text}")
                        raise Exception(f"Proxy upload failed: {error_text}")
                    
                    response_text = await resp.text()
                    logger.info(f"Proxy upload success. Response: {response_text}")
                    
                    try:
                        import json
                        resp_json = json.loads(response_text)
                        
                        raw_url = ""
                        if 'url' in resp_json:
                            raw_url = resp_json['url']
                        elif 'data' in resp_json and 'url' in resp_json['data']:
                            raw_url = resp_json['data']['url']
                        else:
                            raw_url = response_text
                            
                        # Clean the URL (remove quotes, backticks, whitespace)
                        return raw_url.strip().strip('"').strip("'").strip("`")
                    except:
                        return response_text.strip().strip('"').strip("'").strip("`")

    async def create_character(self, timestamps: str, api_key: str = None, from_task: str = None, url: str = None, name: str = None, permission: str = None, proxy: str = None, video_file_path: str = None):
        request_proxy = proxy if proxy else HTTP_PROXY
        
        if not api_key:
             raise ValueError("API Key is required for real requests")

        # 1. Handle Local File Upload (Proxy)
        # If we have a local video file path, we MUST upload it to the proxy first
        # to get a public URL that Sora can access.
        final_url = url
        
        if video_file_path:
            logger.info(f"Detected local video file: {video_file_path}")
            if os.path.exists(video_file_path):
                try:
                    logger.info(">>> Step 1: Uploading local video to proxy server...")
                    final_url = await self.upload_file_to_proxy(video_file_path, api_key, proxy)
                    logger.info(f"<<< Step 1 Complete. Public Proxy URL: {final_url}")
                except Exception as e:
                    logger.error(f"Failed to upload file to proxy: {e}")
                    raise Exception(f"Failed to upload local video to proxy: {e}")
            else:
                logger.warning(f"Local file path provided but does not exist: {video_file_path}")

        # 2. Prepare Payload
        headers = self.default_headers.copy()
        headers["Authorization"] = f"Bearer {api_key}"
        
        payload = {
            "timestamps": str(timestamps).strip()
        }
        
        if from_task:
            payload["from_task"] = from_task
        elif final_url:
            # Clean final_url again just in case
            payload["url"] = final_url.strip().strip("`")
        else:
             raise ValueError("Either from_task, url (public), or video_file_path (local) must be provided")

        # Name and permission are no longer sent to the API as per user instruction
        
        logger.info(f">>> Step 2: Creating character with payload: {payload}")
        
        # Set a longer timeout (e.g. 600 seconds) for character creation as it involves video processing
        timeout = aiohttp.ClientTimeout(total=600)
        
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            try:
                async with session.post(
                    SORA_CHARACTERS_URL,
                    json=payload,
                    proxy=request_proxy
                ) as resp:
                     if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"Character creation failed.\nURL: {SORA_CHARACTERS_URL}\nStatus: {resp.status}\nResponse: {error_text}\nPayload: {payload}")
                        raise Exception(f"Character creation failed: Status {resp.status}. Response: {error_text}")
                    
                     resp_json = await resp.json()
                     logger.info(f"<<< Step 2 Complete. Character created successfully. Response: {resp_json}")
                     return resp_json
            except asyncio.TimeoutError:
                 logger.error(f"Character creation timed out after 600s. Payload: {payload}")
                 raise Exception("Character creation timed out. The video processing took too long.")
