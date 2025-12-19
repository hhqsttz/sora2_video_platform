import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def test_text_to_video():
    print("\n🚀 [1/4] 测试纯文本生成视频 (Text-to-Video)...")

    # 1. 提交任务
    payload = {
        "prompt": "Test video text only",
        "duration": 5,
        "size": "large",
        "orientation": "landscape"
    }
    
    print(f"📤 提交任务: {payload}")
    try:
        response = requests.post(f"{BASE_URL}/tasks", json=payload)
        response.raise_for_status()
        data = response.json()
        task_id = data["task_id"]
        print(f"✅ 任务提交成功，ID: {task_id}")
    except Exception as e:
        print(f"❌ 任务提交失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   响应内容: {e.response.text}")
        return

    # 2. 轮询状态
    result_path = poll_task(task_id, expect_image=False)
    
    # 3. 验证视频文件访问
    if result_path:
        # result_path 是本地文件路径，我们需要提取文件名来构建 URL
        # 假设 result_path 格式为 data/outputs/xxxx.mp4
        import os
        filename = os.path.basename(result_path)
        video_url = f"{BASE_URL}/outputs/{filename}"
        print(f"🎥 验证视频访问: {video_url}")
        try:
            v_res = requests.head(video_url)
            if v_res.status_code == 200:
                print("✅ 视频文件可访问")
            else:
                print(f"❌ 视频文件无法访问: {v_res.status_code}")
        except Exception as e:
            print(f"❌ 请求视频出错: {e}")

def test_image_to_video():
    print("\n🚀 [2/4] 测试图生视频 (Image-to-Video)...")

    # 模拟一个极简的 Base64 图片 (1x1 pixel PNG)
    fake_image_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

    # 1. 提交任务
    payload = {
        "prompt": "Test video with image reference",
        "duration": 10,
        "size": "medium",
        "orientation": "portrait",
        "image": fake_image_base64
    }
    
    print(f"📤 提交任务: prompt='...', size='medium', orientation='portrait', image='(base64 data...)'")
    try:
        response = requests.post(f"{BASE_URL}/tasks", json=payload)
        response.raise_for_status()
        data = response.json()
        task_id = data["task_id"]
        print(f"✅ 任务提交成功，ID: {task_id}")
    except Exception as e:
        print(f"❌ 任务提交失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   响应内容: {e.response.text}")
        return

    # 2. 轮询状态
    poll_task(task_id, expect_image=True)

def test_invalid_params():
    print("\n🚀 [3/4] 测试参数校验 (Invalid Params)...")
    
    # 测试非法的 size
    payload = {
        "prompt": "Test invalid size",
        "size": "super-giant", # Invalid
        "orientation": "landscape"
    }
    
    print(f"📤 提交非法参数任务: {payload}")
    try:
        response = requests.post(f"{BASE_URL}/tasks", json=payload)
        if response.status_code == 422:
             print("✅ 成功拦截非法参数: 返回 422 Unprocessable Entity")
             # print(f"   错误详情: {response.json()}")
        else:
             print(f"❌ 拦截失败: 期望 422，实际返回 {response.status_code}")
             print(f"   响应内容: {response.text}")
    except Exception as e:
        print(f"❌ 请求出错: {e}")

def test_large_payload():
    print("\n🚀 [4/4] 测试超大 Payload 拦截...")
    
    # 模拟 16MB 的 Base64 字符串
    large_image = "A" * (16 * 1024 * 1024)
    
    payload = {
        "prompt": "Test large payload",
        "image": large_image
    }
    
    print(f"📤 提交 16MB 的 Payload...")
    try:
        response = requests.post(f"{BASE_URL}/tasks", json=payload)
        if response.status_code == 413:
            print("✅ 成功拦截: 返回 413 Payload Too Large")
        else:
            print(f"❌ 拦截失败: 返回 {response.status_code}")
    except Exception as e:
        print(f"❌ 请求出错: {e}")

def poll_task(task_id, expect_image=False):
    print("🔄 开始轮询任务状态...")
    start_time = time.time()
    result_path = None
    
    while True:
        try:
            status_res = requests.get(f"{BASE_URL}/tasks/{task_id}")
            status_res.raise_for_status()
            task = status_res.json()
            
            status = task["status"]
            progress = task.get("progress", 0)
            has_image = task.get("has_image", False)
            
            # 验证 has_image 字段
            if expect_image and not has_image:
                print(f"❌ 错误: 期望 has_image=True，但实际为 {has_image}")
            elif not expect_image and has_image:
                print(f"❌ 错误: 期望 has_image=False，但实际为 {has_image}")

            print(f"   - 状态: {status}, 进度: {progress}%, 含图片: {has_image}")

            if status == "done":
                result_path = task.get('result_path')
                print(f"🎉 任务完成! 结果路径: {result_path}")
                break
            elif status == "failed":
                print(f"❌ 任务失败: {task.get('error')}")
                break
            
            if time.time() - start_time > 60:
                print("❌ 测试超时")
                break

            time.sleep(1)
        except Exception as e:
            print(f"❌ 轮询出错: {e}")
            break
            
    return result_path

if __name__ == "__main__":
    # 检查服务是否健康
    try:
        requests.get(f"{BASE_URL}/docs", timeout=2)
    except:
        print(f"❌ 无法连接到后端服务 {BASE_URL}，请确保服务已启动 (python backend/main.py)")
        sys.exit(1)
        
    test_text_to_video()
    test_image_to_video()
    test_invalid_params()
    test_large_payload()
