import os
import json
import urllib.request
import urllib.error
import time
import shutil
from datetime import datetime

# 설정
COMFYUI_SERVER = "http://127.0.0.1:8188"
BATCH_INPUT_DIR = r"C:\Users\A\Desktop\SVD_Input"
COMFYUI_INPUT_DIR = r"C:\Users\A\Desktop\AI_Store\core_engine\ComfyUI\input"
COMFYUI_OUTPUT_DIR = r"C:\Users\A\Desktop\AI_Store\core_engine\ComfyUI\output"
DESKTOP_OUTPUT_DIR = r"C:\Users\A\Desktop\SVD_Output"
WORKFLOW_PATH = r"C:\Users\A\Desktop\AI_Store\core_engine\svd_highres_workflow.json"

def load_workflow(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def send_prompt(prompt):
    data = json.dumps({"prompt": prompt}).encode('utf-8')
    req = urllib.request.Request(f"{COMFYUI_SERVER}/prompt", data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read())
    except urllib.error.URLError as e:
        print(f"Error connecting to ComfyUI: {e}")
        return None

def get_history(prompt_id):
    try:
        with urllib.request.urlopen(f"{COMFYUI_SERVER}/history/{prompt_id}") as response:
            return json.loads(response.read())
    except urllib.error.URLError:
        return None

def free_memory():
    data = json.dumps({"unload_models": True, "free_memory": True}).encode('utf-8')
    req = urllib.request.Request(f"{COMFYUI_SERVER}/free", data=data, headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req)
        print(" -> Garbage Collection completed.")
    except Exception as e:
        print(" -> Custom GC endpoint failed. Letting ComfyUI auto-manage VRAM.")

def main():
    if not os.path.exists(BATCH_INPUT_DIR):
        print(f"Input folder not found: {BATCH_INPUT_DIR}")
        return
    if not os.path.exists(DESKTOP_OUTPUT_DIR):
        os.makedirs(DESKTOP_OUTPUT_DIR)
        
    valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')
    images = [f for f in os.listdir(BATCH_INPUT_DIR) if f.lower().endswith(valid_extensions)]
    
    if not images:
        print("No images found in SVD_Input folder.")
        return
        
    workflow = load_workflow(WORKFLOW_PATH)
    total = len(images)
    print(f"Found {total} images. Starting batch processing...")
    
    for i, img_filename in enumerate(images, 1):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = f"batch_{timestamp}_{img_filename}"
        
        # 1. Copy image to ComfyUI input folder
        src_path = os.path.join(BATCH_INPUT_DIR, img_filename)
        dest_path = os.path.join(COMFYUI_INPUT_DIR, safe_name)
        shutil.copy2(src_path, dest_path)
        
        # 2. Update Workflow JSON
        workflow["2"]["inputs"]["image"] = safe_name
        
        out_prefix = f"svd_hq_{timestamp}_{os.path.splitext(img_filename)[0]}"
        workflow["10"]["inputs"]["filename_prefix"] = out_prefix
        
        # 3. Send Prompt
        print(f"[{i}/{total}] Processing: {img_filename} ...", end="", flush=True)
        response = send_prompt(workflow)
        
        if not response or "prompt_id" not in response:
            print(" FAILED to queue prompt.")
            continue
            
        prompt_id = response["prompt_id"]
        
        # 4. Wait for completion
        while True:
            time.sleep(2)
            history = get_history(prompt_id)
            if history and prompt_id in history:
                print(f" DONE!")
                # Move from ComfyUI output to Desktop output
                comfy_out_path = os.path.join(COMFYUI_OUTPUT_DIR, out_prefix + ".mp4")
                if os.path.exists(comfy_out_path):
                    final_path = os.path.join(DESKTOP_OUTPUT_DIR, out_prefix + ".mp4")
                    shutil.move(comfy_out_path, final_path)
                    print(f" -> Video saved to Desktop\\SVD_Output\\{out_prefix}.mp4")
                break
                
        # 5. Cool down & GC
        if i < total:
            print(" -> Triggering VRAM Cleanup for next image...", end="")
            free_memory()
            time.sleep(5) # Give GPU time to settle

    print("\n🎉 Batch processing completed successfully!")

if __name__ == "__main__":
    main()
