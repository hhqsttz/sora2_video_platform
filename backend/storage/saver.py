import os
from config import OUTPUT_DIR

def save_video(task_id: str, data: bytes):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = f"{OUTPUT_DIR}/{task_id}.mp4"
    with open(path, "wb") as f:
        f.write(data)
    return path
