import aiohttp
import asyncio
import logging
import sys
import os
import base64

# Add parent directory to path to allow importing config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SORA_CREATE_URL, SORA_QUERY_URL, SORA_STORYBOARD_CREATE_URL, SORA_STORYBOARD_STATUS_URL, SORA_CHARACTERS_URL, USE_MOCK, SORA_MODEL, HTTP_PROXY

logger = logging.getLogger(__name__)

class SoraClient:
    def __init__(self):
        self.default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _clean_url(self, url: str) -> str:
        if not url:
            return ""
        import re
        raw = str(url)
        raw = raw.replace("`", "").replace("，", ",")
        match = re.search(r"https?://[^\s'\"`<>，,]+", raw)
        cleaned = match.group(0) if match else raw.strip()
        cleaned = cleaned.strip().strip('"').strip("'").strip()
        cleaned = cleaned.split(",", 1)[0].strip()
        while cleaned and cleaned[-1] in [",", ";", ")", "]", "}", ">", "'", '"', "`"]:
            cleaned = cleaned[:-1].strip()
        return cleaned

    def _compute_resolution_size(self, size: str, orientation: str, model: str = None) -> str:
        import re
        if isinstance(size, str) and re.match(r"^\d{3,4}x\d{3,4}$", size.strip()):
            return size.strip()
        normalized_model = (model or "").strip().lower()
        if size == "small" or normalized_model == "sora-2":
            if orientation == "portrait":
                return "720x1280"
            return "1280x720"
        if orientation == "portrait":
            return "1080x1920"
        return "1920x1080"

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

    async def generate_video(self, prompt, progress_cb, api_key=None, duration=10, size="large", orientation="landscape", image=None, proxy=None, model="sora-2", mode="studio", character_url=None, character_timestamps=None, scenes=None):
        # 优先使用用户传入的代理，否则使用全局配置的代理
        request_proxy = proxy if proxy else HTTP_PROXY

        if mode == 'storyboard' and scenes:
            constructed_prompt = ""
            shot_index = 1
            for scene in scenes:
                # Handle both object (Pydantic) and dict (JSON)
                s_duration = getattr(scene, 'duration', None)
                if s_duration is None and isinstance(scene, dict):
                    s_duration = scene.get('duration')
                
                s_prompt = getattr(scene, 'prompt', None)
                if s_prompt is None and isinstance(scene, dict):
                    s_prompt = scene.get('prompt')
                    
                constructed_prompt += f"Shot {shot_index}:\nduration: {s_duration}sec\nScene: {s_prompt or 'Continue previous action'}\n\n"
                shot_index += 1
            
            if constructed_prompt:
                prompt = constructed_prompt.strip()
                logger.info(f"Constructed storyboard prompt from scenes: {prompt}")
            else:
                logger.warning("Storyboard mode but no scenes provided or constructed prompt is empty.")

        if not prompt and not image:
            # 如果既没有 prompt 也没有图片，对于某些模型可能是允许的（纯图片生成？），但通常需要至少一个
            logger.warning("Prompt is empty and no image provided.")
            
        if not api_key:
             # Key 为空
             raise ValueError("API Key is required for real requests")

        # 如果是 Storyboard 模式，我们不应该在 Session 级别设置 Content-Type
        # 因为 Multipart 需要自动生成的 Boundary
        session_headers = self.default_headers.copy()
        if mode == 'storyboard':
            if "Content-Type" in session_headers:
                del session_headers["Content-Type"]
            
        headers = session_headers.copy()
        headers["Authorization"] = f"Bearer {api_key}"

        # Map friendly names to API values
        # API expects specific resolution strings (e.g. "1920x1080") instead of "large"/"medium"
        api_orientation = orientation

        storyboard_ratio_size = "9x16" if orientation == "portrait" else "16x9"

        storyboard_create_url = ""
        storyboard_status_url = ""
        if mode == 'storyboard':
            storyboard_create_url = self._clean_url(SORA_STORYBOARD_CREATE_URL)
            storyboard_status_url = self._clean_url(SORA_STORYBOARD_STATUS_URL)

        if mode == 'storyboard':
            # Storyboard mode logic for size
            # sora-2 usually expects resolution (e.g. 1280x720), not ratio (16x9)
            # We prioritize resolution for sora-2 to avoid 400 invalid_size
            resolution_size = self._compute_resolution_size(size, orientation, model=model)
            if model == "sora-2":
                api_size = resolution_size
            else:
                # For other models (e.g. sora-2-pro might support ratio?), we can keep ratio or fallback
                # safely default to resolution to be sure
                api_size = resolution_size
        else:
            api_size = self._compute_resolution_size(size, orientation, model=model)
 
        logger.info(f"Sending generation request to Sora ({mode}): {prompt}, duration: {duration}s, size: {api_size}, orientation: {api_orientation}, model: {model}, has_image: {bool(image)}")
        
        # 确保 User-Agent 伪装，防止被 WAF 拦截
        if "User-Agent" not in headers:
            headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        async with aiohttp.ClientSession(headers=headers) as session:
 
            # ① 提交生成任务
            try:
                if mode == 'storyboard':
                    fallback_create_url = ""

                    try:
                        d_val = float(duration)
                        if d_val.is_integer():
                            d_str = str(int(d_val))
                        else:
                            d_str = str(d_val)
                    except:
                        d_str = str(duration)

                    async def submit_storyboard_json(target_url: str, size_value, model_value: str):
                        cleaned_url = self._clean_url(target_url)
                        payload = {
                            "model": model_value,
                            "prompt": prompt,
                            "seconds": d_str,
                            "watermark": False,
                            "private": False
                        }
                        if size_value is not None:
                            payload["size"] = size_value

                        if image:
                            # 接口定义 input_reference 为 string
                            img_str = image
                            if "," in image:
                                _, img_str = image.split(",", 1)
                            payload["input_reference"] = img_str

                        logger.info(
                            "Storyboard submit (json): url=%s, model=%s, seconds=%s, size=%s, private=%s, watermark_type=%s, prompt_len=%s",
                            cleaned_url,
                            payload.get("model"),
                            payload.get("seconds"),
                            payload.get("size"),
                            payload.get("private"),
                            type(payload.get("watermark")).__name__,
                            len(payload.get("prompt") or "")
                        )
                        async with session.post(cleaned_url, json=payload, proxy=request_proxy) as resp:
                            if not resp.ok:
                                error_text = await resp.text()
                                logger.error(f"Sora Storyboard API error: {resp.status} - {error_text}")
                                raise RuntimeError(error_text)
                            return await resp.json()

                    async def submit_storyboard_multipart(target_url: str, size_value, model_value: str):
                        cleaned_url = self._clean_url(target_url)
                        
                        # Manual multipart construction to match example exactly
                        import uuid
                        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
                        body_parts = []
                        
                        def add_field(name, value):
                            body_parts.append(f'--{boundary}'.encode('utf-8'))
                            body_parts.append(f'Content-Disposition: form-data; name="{name}"'.encode('utf-8'))
                            body_parts.append(b'Content-Type: text/plain')
                            body_parts.append(b'')
                            body_parts.append(str(value).encode('utf-8'))

                        # 1. model
                        add_field('model', model_value)
                        
                        # 2. prompt
                        add_field('prompt', prompt)
                        
                        # 3. seconds
                        add_field('seconds', d_str)
                        
                        # 4. input_reference (File)
                        if image:
                            if "," in image:
                                _, encoded = image.split(",", 1)
                            else:
                                encoded = image
                            image_bytes = base64.b64decode(encoded)
                            
                            body_parts.append(f'--{boundary}'.encode('utf-8'))
                            body_parts.append(f'Content-Disposition: form-data; name="input_reference"; filename="storyboard.jpg"'.encode('utf-8'))
                            body_parts.append(b'Content-Type: image/jpeg')
                            body_parts.append(b'')
                            body_parts.append(image_bytes)
                        
                        # 5. size
                        if size_value:
                            add_field('size', size_value)
                            
                        # 6. watermark
                        add_field('watermark', 'false')
                        
                        # 7. private
                        add_field('private', 'false')
                        
                        # 8. Empty fields
                        add_field('character_url', '')
                        add_field('character_timestamps', '')
                        add_field('metadata', '')
                        add_field('character_from_task', '')
                        add_field('character_create', '')
                        
                        # End boundary
                        body_parts.append(f'--{boundary}--'.encode('utf-8'))
                        body_parts.append(b'')
                        
                        # Join all parts
                        body_bytes = b'\r\n'.join(body_parts)
                        
                        # Headers
                        post_headers = headers.copy()
                        post_headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'
                        post_headers['Content-Length'] = str(len(body_bytes))

                        logger.info(
                            "Storyboard submit (manual multipart): url=%s, model=%s, seconds=%s, size=%s, private=%s, has_image=%s, prompt_len=%s",
                            cleaned_url,
                            model_value,
                            d_str,
                            size_value,
                            False,
                            bool(image),
                            len(prompt or "")
                        )
                        
                        async with session.post(cleaned_url, data=body_bytes, headers=post_headers, proxy=request_proxy) as resp:
                            if not resp.ok:
                                error_text = await resp.text()
                                logger.error(f"Sora Storyboard API error: {resp.status} - {error_text}")
                                raise RuntimeError(error_text)
                            return await resp.json()

                    logger.info("Using Storyboard mode")

                    submit_response = None
                    submit_exception = None

                    def classify_storyboard_submit_error(exc: Exception) -> str:
                        text = str(exc) if exc else ""
                        lowered = text.lower()
                        if "missing_model" in lowered:
                            return "missing_model"
                        if "invalid_size" in lowered:
                            return "invalid_size"
                        if "invalid_url" in lowered:
                            return "invalid_url"
                        if "get_channel_failed" in lowered:
                            return "upstream_busy"
                        return "unknown"

                    logger.info(
                        "Storyboard upstream endpoints: create=%r status=%r",
                        storyboard_create_url,
                        storyboard_status_url
                    )

                    ratio_size_value = storyboard_ratio_size
                    resolution_size_value = self._compute_resolution_size(size, orientation, model=model)
                    size_candidates = []
                    
                    # For sora-2, we skip ratio size because it causes 400 error
                    if model == "sora-2":
                        size_candidates.append(resolution_size_value)
                        # Add ratio size only as a fallback if resolution fails (though unlikely to help for sora-2)
                        # size_candidates.append(ratio_size_value) 
                    else:
                        # For other models, try ratio first, then resolution
                        size_candidates.append(ratio_size_value)
                        size_candidates.append(resolution_size_value)
                        
                    if None not in size_candidates:
                        size_candidates.append(None)

                    model_candidates = [model]
                    # if isinstance(model, str) and model.strip() == "sora-2":
                    #     model_candidates.append("sora-2-pro")

                    # 强制使用 Multipart 提交，因为它的格式最标准，且支持空字段
                    if True: 
                        for model_value in model_candidates:
                            for size_value in size_candidates:
                                try:
                                    submit_response = await submit_storyboard_multipart(storyboard_create_url, size_value=size_value, model_value=model_value)
                                    submit_exception = None
                                    break
                                except Exception as e:
                                    submit_exception = e
                                    submit_response = None
                                    code = classify_storyboard_submit_error(e)
                                    if code == "upstream_busy":
                                        await asyncio.sleep(2)
                                        try:
                                            submit_response = await submit_storyboard_multipart(storyboard_create_url, size_value=size_value, model_value=model_value)
                                            submit_exception = None
                                            break
                                        except Exception as e2:
                                            submit_exception = e2
                                            submit_response = None
                                            code = classify_storyboard_submit_error(e2)
                                    if code == "missing_model":
                                        break
                                    if code != "invalid_size":
                                        break
                            if submit_response is not None:
                                break
                        if submit_response is None:
                            logger.warning(
                                "Storyboard multipart submit failed, will try json. url=%s, error=%s",
                                self._clean_url(storyboard_create_url),
                                str(submit_exception)
                            )

                    # 如果 Multipart 失败，才尝试 JSON
                    if submit_response is None:
                        for model_value in model_candidates:
                            for size_value in size_candidates:
                                try:
                                    submit_response = await submit_storyboard_json(storyboard_create_url, size_value, model_value=model_value)
                                    submit_exception = None
                                    break
                                except Exception as e:
                                    submit_exception = e
                                    submit_response = None
                                    code = classify_storyboard_submit_error(e)
                                    if code == "upstream_busy":
                                        await asyncio.sleep(2)
                                        try:
                                            submit_response = await submit_storyboard_json(storyboard_create_url, size_value, model_value=model_value)
                                            submit_exception = None
                                            break
                                        except Exception as e2:
                                            submit_exception = e2
                                            submit_response = None
                                            code = classify_storyboard_submit_error(e2)
                                    if code != "invalid_size":
                                        break
                            if submit_response is not None:
                                break
                        if submit_response is None:
                            logger.warning(
                                "Storyboard json submit failed. url=%s, error=%s",
                                self._clean_url(storyboard_create_url),
                                str(submit_exception)
                            )

                    if submit_response is None and fallback_create_url and fallback_create_url != storyboard_create_url:
                        if image:
                            try:
                                submit_response = await submit_storyboard_multipart(fallback_create_url, size_value=api_size)
                                submit_exception = None
                            except Exception as e:
                                submit_exception = e
                                submit_response = None
                                if submit_response is None:
                                    logger.warning(
                                        "Storyboard multipart fallback submit failed, will try json. url=%s, error=%s",
                                        self._clean_url(fallback_create_url),
                                        str(submit_exception)
                                    )

                        if submit_response is None:
                            try:
                                submit_response = await submit_storyboard_json(fallback_create_url, api_size)
                                submit_exception = None
                            except Exception as e:
                                submit_exception = e
                                submit_response = None
                                if submit_response is None:
                                    logger.warning(
                                        "Storyboard json fallback submit failed. url=%s, error=%s",
                                        self._clean_url(fallback_create_url),
                                        str(submit_exception)
                                    )

                    if submit_response is None:
                        raise submit_exception if submit_exception else RuntimeError("Storyboard submit failed")

                    task_id = None
                    if isinstance(submit_response, dict):
                        if "id" in submit_response:
                            task_id = submit_response.get("id")
                        elif "data" in submit_response and isinstance(submit_response["data"], dict):
                            task_id = submit_response["data"].get("id")
                    if not task_id:
                        raise RuntimeError(f"Storyboard submit response missing id: {submit_response}")

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
                        self._clean_url(SORA_CREATE_URL),
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
                    if mode == 'storyboard':
                         # Storyboard polling: GET /v1/videos/{id}
                         poll_url = f"{storyboard_status_url}/{task_id}"
                         async with session.get(poll_url, proxy=request_proxy) as resp:
                            if resp.status == 403:
                                logger.warning(f"Storyboard polling 403 Forbidden. Retrying with content URL... URL: {resp.url}")
                                async with aiohttp.ClientSession(headers=headers) as fresh_session:
                                     # Fallback: Try /v1/videos/{id}/content
                                     content_url = f"{self._clean_url(SORA_STORYBOARD_STATUS_URL)}/{task_id}/content"
                                     async with fresh_session.get(content_url, proxy=request_proxy) as resp2:
                                         if resp2.status == 200:
                                             resp = resp2
                                             logger.info(f"Storyboard polling succeeded via content URL: {content_url}")
                                         else:
                                             # Fallback failed, log original error
                                             error_text = await resp2.text()
                                             logger.error(f"Storyboard polling retry failed: {resp2.status} - {error_text}")
                            
                            resp.raise_for_status()
                            status_data = await resp.json()
                            
                            # Handle potential structure differences
                            if "status" in status_data:
                                state = status_data["status"]
                            elif "data" in status_data and status_data["data"] and "status" in status_data["data"]:
                                # Flatten data if wrapped
                                status_data = status_data["data"]
                                state = status_data["status"]
                            else:
                                logger.warning(f"Unknown storyboard status structure: {status_data}")
                                # Try to guess or default
                                state = "queued"
                    else:
                        # Studio polling: GET /v1/video/query?id={id}
                        # 显式带上 headers 确保鉴权信息不丢失，特别是 Authorization
                        poll_headers = headers.copy()
                        poll_url = self._clean_url(SORA_QUERY_URL)
                        
                        async with session.get(poll_url, params={"id": task_id}, headers=poll_headers, proxy=request_proxy) as resp:
                            if resp.status == 403:
                                logger.warning(f"Polling 403 Forbidden. Retrying with fresh headers... URL: {resp.url}")
                                # 某些 WAF 可能因为 Session Cookie 问题拦截，尝试不带 Cookie 重试（或仅带 Auth）
                                async with aiohttp.ClientSession(headers=headers) as fresh_session:
                                    # Retry 1: Same URL, fresh session
                                    async with fresh_session.get(poll_url, params={"id": task_id}, proxy=request_proxy) as resp2:
                                        if resp2.status == 200:
                                            resp = resp2
                                        else:
                                            # Retry 2: Fallback URL (Storyboard style) /v1/videos/{id}
                                            # 有些 Token 可能只能访问 /v1/videos/{id} 而不能访问 /v1/video/query
                                            fallback_url = f"{self._clean_url(SORA_STORYBOARD_STATUS_URL)}/{task_id}"
                                            logger.warning(f"Polling retry 1 failed. Trying fallback URL: {fallback_url}")
                                            
                                            async with fresh_session.get(fallback_url, proxy=request_proxy) as resp3:
                                                if resp3.status == 200:
                                                    resp = resp3
                                                    logger.info(f"Fallback polling succeeded via {fallback_url}")
                                                else:
                                                    # Retry 3: Try /v1/videos/{id}/content
                                                    content_url = f"{self._clean_url(SORA_STORYBOARD_STATUS_URL)}/{task_id}/content"
                                                    logger.warning(f"Fallback polling failed. Trying content URL: {content_url}")
                                                    async with fresh_session.get(content_url, proxy=request_proxy) as resp4:
                                                        if resp4.status == 200:
                                                            resp = resp4
                                                            logger.info(f"Content polling succeeded via {content_url}")
                                                        else:
                                                            # All retries failed
                                                            error_text = await resp2.text() # Use original error
                                                            logger.error(f"Polling retry failed: {resp2.status} - {error_text}")
                            
                            if resp.status == 200:
                                status_data = await resp.json()
                                # Compatible with both structures
                                if "data" in status_data and isinstance(status_data["data"], dict) and "status" in status_data["data"]:
                                    status_data = status_data["data"]
                                state = status_data.get("status", "unknown")
                            else:
                                resp.raise_for_status()
                            
                except Exception as e:
                    logger.error(f"Failed to poll status: {e}")
                    raise

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
