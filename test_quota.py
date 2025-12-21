import requests
import json
import os

# 请在此处替换您的 API Key
API_KEY = "sk-1FcQHcmvF5P6ZvXI31Bf054GlXWF6fYR1CqqNOTsjnr3yaRu" 

# 如果您是通过环境变量运行，可以尝试读取
env_key = os.getenv("SORA_API_KEY")
if env_key:
    API_KEY = env_key

# 如果前端输入了 Key，请手动将其粘贴到上面的 API_KEY 变量中覆盖

URL = "https://yunwu.ai/v1/videos"

payload = {
    "model": "sora-2",
    "prompt": "test video",
    "seconds": "10",
    "size": "1280x720",
    "private": False,
    "watermark": False
}

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

print(f"Testing API with Key: {API_KEY[:8]}...{API_KEY[-4:] if len(API_KEY)>10 else ''}")
print(f"URL: {URL}")

try:
    response = requests.post(URL, headers=headers, json=payload, timeout=30)
    print(f"Status Code: {response.status_code}")
    print("Response Body:")
    print(response.text)
except Exception as e:
    print(f"Request failed: {e}")
