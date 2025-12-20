# Sora2 Video Platform

一个基于 FastAPI 和 Yunwu.ai (Sora 2) API 的现代化视频生成平台。支持双模式生成（创作中心 & 故事板），具备高并发管理、实时进度追踪、智能图片压缩和安全防护功能。

## ✨ 核心特性

*   **🎬 双模式创作引擎**：
    *   **创作中心 (Studio Mode)**: 
        *   **Text-to-Video**: 输入提示词生成高清视频。
        *   **Image-to-Video**: 支持上传参考图片生成视频。
        *   **灵活参数**: 支持 Large/Small 尺寸，Landscape/Portrait 方向，10s 默认时长。
    *   **故事板 (Storyboard Mode) (Beta)**:
        *   **分镜叙事**: 支持逐个分镜（Scene）规划剧情，每个分镜可独立设置提示词和精确时长（支持小数，如 1.2s）。
        *   **全局控制**: 统一设置总时长（10s, 15s, 25s）、模型版本和画幅比例。
        *   **智能拼接**: 前端自动校验分镜总时长，自动整合成长 Prompt 提交。
        *   **首帧参考**: 支持上传故事板起始帧图片。

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
    *   **实时进度条**: 任务状态实时轮询，支持百分比显示。
    *   **可视化展示**: 任务卡片展示详细参数（📏 尺寸 | 🧭 方向 | ⏱️ 模式）。
    *   **在线预览**: 视频生成后自动加载播放，支持一键下载。

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
# 进入后端目录
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

启动成功后，API 地址为 `http://localhost:8000`。
视频文件服务地址为 `http://localhost:8000/outputs/`。

## 📖 使用指南

### 1. 配置 API Key
在前端页面的 **"Sora API Key"** 输入框中填入你的 Yunwu.ai API Key。
*   **Mock 模式**: 如果留空不填，系统将自动进入 Mock 模式（生成假视频，用于测试流程）。
*   **真实调用**: 输入 Key 后，系统会强制调用真实 Yunwu.ai API。Key 会自动保存到浏览器本地缓存。

### 2. 选择创作模式

#### 🎨 创作中心 (Studio)
适合生成单段、高质量的视频片段。
*   **提示词 (Prompt)**: 描述你想生成的视频内容。
*   **参考图片**: 可选上传参考图（自动压缩处理）。
*   **尺寸与方向**: 支持 Large/Small 尺寸及 Landscape/Portrait 方向。
*   **模型**: 选择 Sora-2 或 Sora-2 Pro。

#### 🎬 故事板 (Storyboard)
适合精细化控制剧情节奏。
1.  **全局设置**: 设置总时长（如 15s）、比例和模型。
2.  **上传首帧**: 可选上传起始帧图片。
3.  **添加分镜**: 点击 "+ 添加场景"。
4.  **分镜编辑**:
    *   **时长**: 精确输入每个分镜的时间（支持 0.1s 精度，如 3.5s）。
    *   **剧情**: 描述该分镜发生的故事。
5.  **提交**: 系统会自动校验分镜总时长是否等于全局总时长。

### 3. 查看结果
点击生成按钮后，任务会进入队列。
*   列表卡片会显示任务 ID、状态、进度以及详细参数。
*   任务完成后，视频会自动加载，支持在线播放和下载。

## ⚙️ 后端配置

配置文件位于 `backend/config.py`：

```python
# API 设置
SORA_CREATE_URL = "https://yunwu.ai/v1/video/create"
SORA_STORYBOARD_URL = "https://yunwu.ai/v1/video/storyboard" # 故事板接口
SORA_QUERY_URL = "https://yunwu.ai/v1/video/query"
SORA_MODEL = "sora-2-pro"  # 默认模型

# 并发控制
MAX_CONCURRENT = 3     # 最大同时处理任务数

# 存储路径
OUTPUT_DIR = "data/outputs"
```

## 🔌 API 文档

后端启动后，访问 Swagger UI 查看完整接口文档：
`http://localhost:8000/docs`

### 主要接口
*   `POST /tasks`: 提交生成任务
    *   支持 `mode="studio"` (JSON Body) 和 `mode="storyboard"` (Multipart/Form-Data)。
    *   **Studio**: 接收 `size`, `orientation`, `duration` (int)。
    *   **Storyboard**: 接收 `seconds` (float), `size` (aspect ratio string), `prompt` (aggregated)。
*   `GET /tasks`: 获取任务列表。
*   `GET /tasks/{task_id}`: 获取任务详情。

## 📝 开发日志

*   **v2.0**: 
    *   **重磅更新**: 引入故事板 (Storyboard) 模式。
    *   支持高精度时长控制（浮点数秒）。
    *   重构前端 UI，实现双模式切换。
    *   后端适配 Multipart/Form-Data 协议对接故事板接口。
*   **v1.5**: 
    *   优化 Git 仓库结构，过滤构建产物。
    *   修正 API 参数映射（Size/Orientation 自动转换）。
*   **v1.4**: 
    *   优化资源路径加载逻辑，兼容开发环境。
*   **v1.3**: 
    *   全面适配 Yunwu.ai API 接口。
    *   新增 `size` 和 `orientation` 参数控制。
