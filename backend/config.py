import os

# API Config
SORA_API_KEY = os.getenv("SORA_API_KEY", "sk-proj-mock-key")
# 替换为第三方中转 API 地址
SORA_CREATE_URL = "https://yunwu.ai/v1/video/create"
SORA_QUERY_URL = "https://yunwu.ai/v1/video/query"
SORA_MODEL = "sora-2-pro"
USE_MOCK = True  # Enable mock mode for testing

# Proxy Config (Optional)
# 使用国内中转 API 时通常不需要代理，除非你的网络环境特殊
# Example: "http://127.0.0.1:7890"
HTTP_PROXY = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")

# Task Config
MAX_CONCURRENT = 3
MAX_RETRY = 3

# Storage
# 使用绝对路径，确保无论从哪里启动脚本，都指向项目根目录下的 data/outputs
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "outputs")
