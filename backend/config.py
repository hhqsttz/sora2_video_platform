import os

# API Config
SORA_API_KEY = os.getenv("SORA_API_KEY", "sk-proj-mock-key")
SORA_API_URL = "https://api.openai.com/v1/video/generations"
SORA_MODEL = "sora-2-pro"
USE_MOCK = True  # Enable mock mode for testing

# Task Config
MAX_CONCURRENT = 3
MAX_RETRY = 3

# Storage
OUTPUT_DIR = "data/outputs"
