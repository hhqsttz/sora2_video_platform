import os

# API Config
SORA_API_KEY = os.getenv("SORA_API_KEY", "")
# 替换为第三方中转 API 地址
SORA_CREATE_URL = os.getenv("SORA_CREATE_URL", "https://yunwu.ai/v1/video/create")
SORA_STORYBOARD_CREATE_URL = os.getenv("SORA_STORYBOARD_CREATE_URL", "https://yunwu.ai/v1/videos")
SORA_STORYBOARD_STATUS_URL = os.getenv("SORA_STORYBOARD_STATUS_URL", "https://yunwu.ai/v1/videos")
SORA_CHARACTERS_URL = os.getenv("SORA_CHARACTERS_URL", "https://yunwu.ai/sora/v1/characters")
SORA_QUERY_URL = os.getenv("SORA_QUERY_URL", "https://yunwu.ai/v1/video/query")
SORA_MODEL = "sora-2"
USE_MOCK = False  # Disable mock mode for production

# Proxy Config (Optional)
# 使用国内中转 API 时通常不需要代理，除非你的网络环境特殊
# Example: "http://127.0.0.1:7890"
HTTP_PROXY = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")

# Task Config
MAX_CONCURRENT = 10 # Aggressive concurrency
MAX_RETRY = 3     # Keep high retry attempts

# Storage
# 使用绝对路径，确保无论从哪里启动脚本，都指向项目根目录下的 data/outputs
import sys
if getattr(sys, 'frozen', False):
    # 如果是打包后的 exe 环境，sys.executable 是 exe 文件的路径
    # 我们希望 data 目录在 exe 同级目录下
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 开发环境
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OUTPUT_DIR = os.path.join(BASE_DIR, "data", "outputs")
