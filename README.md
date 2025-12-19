# Sora2 Video Platform

一个基于 FastAPI 和 Yunwu.ai (Sora 2) API 的现代化视频生成平台。支持 Text-to-Video 和 Image-to-Video，具备高并发管理、实时进度追踪、智能图片压缩和安全防护功能。

## ✨ 核心特性

*   **🎬 多模态生成**：
    *   **Text-to-Video**: 输入提示词生成高清视频。
    *   **Image-to-Video**: 支持上传参考图片生成视频（新增）。
*   **⚙️ 灵活参数控制**：
    *   **尺寸选择**: 支持 Large, Medium, Small 等多种尺寸。
    *   **方向控制**: 支持 Landscape (横屏), Portrait (竖屏), Square (方形)。
    *   **时长控制**: 自定义视频生成时长（5s, 10s, 15s）。
*   **⚡ 高性能与优化**：
    *   **智能前端压缩**: 上传大图（>2MB）时自动进行无损压缩，最大限制 10MB，显著提升传输速度。
    *   **并发任务管理**: 后端使用异步队列处理任务，支持 `MAX_CONCURRENT` 并发控制。
    *   **内存自动清理**: 自动清理过期的任务状态，防止服务器内存泄漏。
*   **🛡️ 安全与健壮**：
    *   **动态鉴权**: 支持前端传入 API Key，后端透传鉴权，保护密钥安全。
    *   **Payload 校验**: 后端自动拦截超大恶意请求（>15MB）。
    *   **Mock 模式**: 内置全流程模拟模式，无需消耗 API 额度即可进行开发测试。
    *   **持久化存储**: 生成的视频自动保存到本地 `data/outputs`，并支持通过 URL 直接访问。
*   **💻 现代化界面**：
    *   实时进度条、任务状态轮询。
    *   支持视频在线预览和下载。
    *   可视化展示任务详情（尺寸、方向、是否包含参考图）。

## 🛠️ 安装与运行

### 1. 环境准备

确保已安装 Python 3.8+。

```bash
# 进入项目目录
cd sora2_video_platform

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动后端服务

```bash
# 在项目根目录下运行
python backend/main.py
# 或者
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

启动成功后，API 地址为 `http://localhost:8000`。
视频文件服务地址为 `http://localhost:8000/outputs/`。

### 3. 使用前端

直接在浏览器中打开 `frontend/index.html` 文件即可开始使用。

## 📖 使用指南

### 1. 配置 API Key
在前端页面的 **"Sora API Key"** 输入框中填入你的 Yunwu.ai API Key。
*   **Mock 模式**: 如果留空不填，系统将自动进入 Mock 模式（生成假视频，用于测试流程）。
*   **真实调用**: 输入 Key 后，系统会强制调用真实 Yunwu.ai API。Key 会自动保存到浏览器本地缓存。

### 2. 设置生成参数
*   **提示词 (Prompt)**: 描述你想生成的视频内容（必填）。
*   **参考图片 (可选)**: 点击上传一张图片作为参考。
    *   支持 JPG/PNG 格式。
    *   前端会自动压缩 >2MB 的图片（最大 2048px），无需手动处理。
    *   最大上传限制为 10MB。
*   **时长**: 视频时长（推荐 5s）。
*   **尺寸 (Size)**: 选择生成视频的尺寸规格 (Large/Medium/Small)。
*   **方向 (Orientation)**: 选择视频方向 (Landscape/Portrait/Square)。

### 3. 查看结果
点击 **"✨ 生成视频"** 后，任务会进入队列。
*   列表卡片会显示任务 ID、状态、进度以及详细参数（📏 尺寸 | 🧭 方向）。
*   任务完成后，视频会自动加载，支持在线播放和下载。

## ⚙️ 后端配置

配置文件位于 `backend/config.py`：

```python
# API 设置
SORA_CREATE_URL = "https://yunwu.ai/v1/video/create"
SORA_QUERY_URL = "https://yunwu.ai/v1/video/query"
SORA_MODEL = "sora-2-pro"  # 模型版本
USE_MOCK = True        # 默认 Mock 开关

# 并发控制
MAX_CONCURRENT = 3     # 最大同时处理任务数

# 存储路径
OUTPUT_DIR = "data/outputs"
```

## 🔌 API 文档

后端启动后，访问 Swagger UI 查看完整接口文档：
`http://localhost:8000/docs`

### 主要接口
*   `POST /tasks`: 提交生成任务（支持 JSON body，含 Base64 图片，Size，Orientation 等参数）。
*   `GET /tasks`: 获取任务列表（返回轻量级数据，不含 Base64）。
*   `GET /tasks/{task_id}`: 获取任务详情。

## 📝 开发日志

*   **v1.3**: 
    *   全面适配 Yunwu.ai API 接口 (`/v1/video/create`, `/v1/video/query`)。
    *   新增 `size` 和 `orientation` 参数控制，移除旧版 `resolution`。
    *   实现前端 API Key 动态透传鉴权。
    *   支持 `sora-2-pro` 模型。
*   **v1.2**: 增加图片上传功能，实现前端压缩与后端校验；优化内存管理。
*   **v1.1**: 适配 Sora 2 API 参数；完善错误日志。
*   **v1.0**: 初始化项目，支持 Mock 模式和基础文本生成。
