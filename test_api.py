import requests
import time
import sys
import base64
import os

BASE_URL = "http://localhost:8000"

# ANSI Colors
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(msg):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{msg}{Colors.ENDC}")

def print_success(msg):
    print(f"{Colors.OKGREEN}✅ {msg}{Colors.ENDC}")

def print_fail(msg):
    print(f"{Colors.FAIL}❌ {msg}{Colors.ENDC}")

def print_info(msg):
    print(f"{Colors.OKCYAN}ℹ️  {msg}{Colors.ENDC}")

def get_base64_image():
    # Create a simple 100x100 red image
    # This is a minimal valid PNG
    # 100x100 red square
    base64_str = "iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAYAAABw4pVUAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAAZdEVYdFNvZnR3YXJlAHBhaW50Lm5ldCA0LjAuMjWx0ZW4AAAAJUlEQVR42u3BAQ0AAADCoPdPbQ8HFAAAAAAAAAAAAAAAAAAAAAAAAAAAvwZn+gABzKpPEAAAAABJRU5ErkJggg=="
    return f"data:image/png;base64,{base64_str}"

def poll_task(task_id, expect_image=False):
    print_info(f"Start polling task {task_id}...")
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
            
            # Verify has_image field
            if expect_image and not has_image:
                print_fail(f"Expected has_image=True, but got {has_image}")
            elif not expect_image and has_image:
                print_fail(f"Expected has_image=False, but got {has_image}")

            # Overwrite line for cleaner output
            sys.stdout.write(f"\r   Status: {status}, Progress: {progress}%   ")
            sys.stdout.flush()

            if status == "done":
                print() # New line
                result_path = task.get('result_path')
                print_success(f"Task completed! Result path: {result_path}")
                break
            elif status == "failed":
                print()
                print_fail(f"Task failed: {task.get('error')}")
                break
            
            if time.time() - start_time > 300: # 5 minutes timeout
                print()
                print_fail("Test timeout (300s)")
                break

            time.sleep(2)
        except Exception as e:
            print()
            print_fail(f"Polling error: {e}")
            break
            
    return result_path

def verify_video_access(result_path):
    if not result_path:
        return
    
    filename = os.path.basename(result_path)
    video_url = f"{BASE_URL}/outputs/{filename}"
    print_info(f"Verifying video access: {video_url}")
    try:
        v_res = requests.head(video_url)
        if v_res.status_code == 200:
            print_success("Video file is accessible via HTTP")
        else:
            print_fail(f"Video file not accessible: {v_res.status_code}")
    except Exception as e:
        print_fail(f"Request error: {e}")

def test_text_to_video():
    print_header("[1/5] Test Text-to-Video (Standard)")

    payload = {
        "prompt": "A cinematic drone shot of a futuristic cyberpunk city at night, neon lights, rain reflections",
        "duration": 5,
        "size": "large",
        "orientation": "landscape",
        "model": "sora-2"
    }
    
    print_info(f"Submitting task: {payload}")
    try:
        response = requests.post(f"{BASE_URL}/tasks", json=payload)
        response.raise_for_status()
        data = response.json()
        task_id = data["task_id"]
        print_success(f"Task submitted, ID: {task_id}")
        
        result_path = poll_task(task_id, expect_image=False)
        verify_video_access(result_path)
        
    except Exception as e:
        print_fail(f"Submission failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"   Response: {e.response.text}")

def test_image_to_video():
    print_header("[2/5] Test Image-to-Video (Storyboard)")

    # 100x100 red square
    fake_image_base64 = get_base64_image()

    payload = {
        "prompt": "Animate this red square turning into a blue circle, 3d render",
        "duration": 10, # Testing the duration fix
        "size": "medium",
        "orientation": "square",
        "image": fake_image_base64
    }
    
    print_info(f"Submitting task with Image...")
    try:
        response = requests.post(f"{BASE_URL}/tasks", json=payload)
        response.raise_for_status()
        data = response.json()
        task_id = data["task_id"]
        print_success(f"Task submitted, ID: {task_id}")
        
        result_path = poll_task(task_id, expect_image=True)
        verify_video_access(result_path)

    except Exception as e:
        print_fail(f"Submission failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"   Response: {e.response.text}")

def test_parameter_combinations():
    print_header("[3/5] Test Parameter Combinations (Portrait, Small)")

    payload = {
        "prompt": "A vertical video of a waterfall",
        "duration": 5,
        "size": "small",
        "orientation": "portrait"
    }
    
    print_info(f"Submitting task: {payload}")
    try:
        response = requests.post(f"{BASE_URL}/tasks", json=payload)
        response.raise_for_status()
        data = response.json()
        task_id = data["task_id"]
        print_success(f"Task submitted, ID: {task_id}")
        # We don't poll here to save time, just check submission
        print_success("Submission accepted.")
    except Exception as e:
        print_fail(f"Submission failed: {e}")

def test_invalid_params():
    print_header("[4/5] Test Invalid Parameters")
    
    payload = {
        "prompt": "Test invalid size",
        "size": "invalid_size_option", 
        "orientation": "landscape"
    }
    
    print_info(f"Submitting invalid payload: {payload}")
    try:
        response = requests.post(f"{BASE_URL}/tasks", json=payload)
        if response.status_code == 422:
             print_success("Correctly rejected with 422")
        else:
             print_fail(f"Failed to reject: {response.status_code}")
             print(response.text)
    except Exception as e:
        print_fail(f"Request error: {e}")

def test_large_payload():
    print_header("[5/5] Test Large Payload Protection")
    
    # 16MB string
    large_image = "A" * (16 * 1024 * 1024)
    
    payload = {
        "prompt": "Test large payload",
        "image": large_image
    }
    
    print_info(f"Submitting 16MB payload...")
    try:
        response = requests.post(f"{BASE_URL}/tasks", json=payload)
        if response.status_code == 413:
            print_success("Correctly rejected with 413 Payload Too Large")
        else:
            print_fail(f"Failed to reject: {response.status_code}")
    except Exception as e:
        print_fail(f"Request error: {e}")

if __name__ == "__main__":
    # Check health
    try:
        requests.get(f"{BASE_URL}/docs", timeout=2)
    except:
        print_fail(f"Cannot connect to {BASE_URL}. Is the backend running?")
        sys.exit(1)
        
    print("Starting Sora2 Platform Comprehensive Tests...")
    
    test_text_to_video()
    test_image_to_video()
    test_parameter_combinations()
    test_invalid_params()
    test_large_payload()
    
    print("\n✅ All tests completed!")
