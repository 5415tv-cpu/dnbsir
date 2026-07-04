import os
import json
import urllib.request
import urllib.error
import time
import shutil
import glob
import subprocess
from datetime import datetime

# 설정
COMFYUI_SERVER = "http://127.0.0.1:8188"
BATCH_INPUT_DIR = r"C:\Users\A\Desktop\SVD_Input"
COMFYUI_INPUT_DIR = r"C:\Users\A\Desktop\AI_Store\core_engine\ComfyUI\input"
COMFYUI_OUTPUT_DIR = r"C:\Users\A\Desktop\AI_Store\core_engine\ComfyUI\output"
DESKTOP_OUTPUT_DIR = r"C:\Users\A\Desktop\SVD_Output"
SVD_WORKFLOW_PATH = r"C:\Users\A\Desktop\AI_Store\core_engine\svd_highres_workflow.json"
T2I_WORKFLOW_PATH = r"C:\Users\A\Desktop\AI_Store\core_engine\sd15_t2i_workflow.json"
TARGET_TOTAL_IMAGES = 150

# 환경변수 파일 파싱 (단순 야매 파싱)
def get_api_key(env_path=r"C:\Users\A\Desktop\AI_Store\env_vars.yaml"):
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("GOOGLE_API_KEY:"):
                    return line.split(":")[1].strip()
    except Exception:
        pass
    return None

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
    except Exception:
        print(" -> Auto GC triggered.")

def generate_prompts(text, mood, count):
    api_key = get_api_key()
    if not api_key:
        print("GOOGLE_API_KEY not found in env_vars.yaml. Cannot generate prompts.")
        return []
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt_instruction = (
            f"We are making a documentary video with a mood of '{mood}'. "
            f"The client's story is: {text}\n"
            f"Generate {count} unique, highly descriptive image prompts in English for a Text-to-Image AI model. "
            "The prompts should visualize various scenes, details, objects, environments, and emotional atmospheres related to the story to serve as B-Roll footage. "
            "Output ONLY a valid JSON array of strings, with no markdown block formatting."
        )
        
        print("Call LLM (Gemini) for prompt generation...")
        response = model.generate_content(prompt_instruction)
        
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:-3]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:-3]
            
        prompts = json.loads(raw_text)
        if isinstance(prompts, list):
            return prompts[:count]
        return []
    except Exception as e:
        print(f"Failed to generate prompts via Gemini: {e}")
        return []

def run_t2i_generation(prompts):
    workflow = load_workflow(T2I_WORKFLOW_PATH)
    print(f"Generating {len(prompts)} missing images using SD1.5...")
    
    for i, p_text in enumerate(prompts, 1):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"ai_gen_{timestamp}_{i}"
        
        workflow["6"]["inputs"]["text"] = p_text
        workflow["9"]["inputs"]["filename_prefix"] = prefix
        
        print(f"[T2I {i}/{len(prompts)}] Generating image for prompt: {p_text[:30]}...")
        resp = send_prompt(workflow)
        if not resp:
            continue
            
        pid = resp["prompt_id"]
        while True:
            time.sleep(2)
            hist = get_history(pid)
            if hist and pid in hist:
                # ComfyUI outputs to its output dir. Move to SVD_Input
                comfy_out = os.path.join(COMFYUI_OUTPUT_DIR, prefix + "_00001.png")
                if os.path.exists(comfy_out):
                    shutil.move(comfy_out, os.path.join(BATCH_INPUT_DIR, f"{prefix}.png"))
                break
        free_memory()
        time.sleep(3)

def run_svd_rendering():
    valid_exts = ('.png', '.jpg', '.jpeg', '.webp')
    images = [f for f in os.listdir(BATCH_INPUT_DIR) if f.lower().endswith(valid_exts)]
    workflow = load_workflow(SVD_WORKFLOW_PATH)
    total = len(images)
    print(f"Starting SVD Video Rendering for {total} images...")
    
    for i, img_filename in enumerate(images, 1):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = f"batch_{timestamp}_{img_filename}"
        
        src_path = os.path.join(BATCH_INPUT_DIR, img_filename)
        dest_path = os.path.join(COMFYUI_INPUT_DIR, safe_name)
        shutil.copy2(src_path, dest_path)
        
        workflow["2"]["inputs"]["image"] = safe_name
        out_prefix = f"svd_hq_{timestamp}_{os.path.splitext(img_filename)[0]}"
        workflow["10"]["inputs"]["filename_prefix"] = out_prefix
        
        print(f"[SVD {i}/{total}] Processing: {img_filename} ...", end="", flush=True)
        response = send_prompt(workflow)
        if not response:
            print(" FAILED")
            continue
            
        pid = response["prompt_id"]
        while True:
            time.sleep(2)
            history = get_history(pid)
            if history and pid in history:
                print(f" DONE!")
                comfy_out_path = os.path.join(COMFYUI_OUTPUT_DIR, out_prefix + ".mp4")
                if os.path.exists(comfy_out_path):
                    final_path = os.path.join(DESKTOP_OUTPUT_DIR, out_prefix + ".mp4")
                    shutil.move(comfy_out_path, final_path)
                break
        
        if i < total:
            free_memory()
            time.sleep(5)

def concatenate_videos():
    print("Concatenating all videos in SVD_Output into one 10-minute clip...")
    videos = glob.glob(os.path.join(DESKTOP_OUTPUT_DIR, "*.mp4"))
    if not videos:
        print("No videos found to concatenate.")
        return
        
    concat_list_path = os.path.join(DESKTOP_OUTPUT_DIR, "concat_list.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for v in videos:
            if "final_documentary" in v: continue
            f.write(f"file '{os.path.basename(v)}'\n")
            
    final_output = os.path.join(DESKTOP_OUTPUT_DIR, f"final_documentary_{datetime.now().strftime('%Y%m%d_%H%M')}.mp4")
    
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list_path, "-c", "copy", final_output
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Successfully created: {final_output}")
    except Exception as e:
        print(f"FFmpeg concatenation failed: {e}")

def main():
    current_hour = datetime.now().hour
    # 7 PM (19:00) 이전에는 실행 불가 (오전 6시 ~ 오후 6시 59분까지 차단)
    if 6 <= current_hour < 19:
        print("="*60)
        print("❌ [가동 거부] 과부하 방지 및 주간 업무 보호 시스템 작동 중 ❌")
        print("오후 7시 이전에는 대규모 렌더링 공장을 가동할 수 없습니다.")
        print(f"현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("오후 7시 이후에 다시 실행해 주십시오.")
        print("="*60)
        return

    os.makedirs(BATCH_INPUT_DIR, exist_ok=True)
    os.makedirs(DESKTOP_OUTPUT_DIR, exist_ok=True)
    
    # 1. Read context
    context_path = os.path.join(BATCH_INPUT_DIR, "story_context.json")
    text = "A beautiful documentary"
    mood = "nostalgic"
    if os.path.exists(context_path):
        with open(context_path, "r", encoding="utf-8") as f:
            ctx = json.load(f)
            text = ctx.get("text", text)
            mood = ctx.get("mood", mood)
            
    valid_exts = ('.png', '.jpg', '.jpeg', '.webp')
    current_images = [f for f in os.listdir(BATCH_INPUT_DIR) if f.lower().endswith(valid_exts)]
    current_count = len(current_images)
    
    print(f"Found {current_count} images in SVD_Input.")
    needed = TARGET_TOTAL_IMAGES - current_count
    
    if needed > 0:
        print(f"We need {needed} more images to reach {TARGET_TOTAL_IMAGES}.")
        prompts = generate_prompts(text, mood, needed)
        if prompts:
            run_t2i_generation(prompts)
        else:
            print("Skipping T2I generation due to LLM failure.")
    else:
        print("Target image count met or exceeded. Skipping T2I generation.")
        
    # 2. Render all with SVD
    run_svd_rendering()
    
    # 3. Concatenate
    concatenate_videos()
    
    print("\n🎉 PHASE 2 PIPELINE FULLY COMPLETED!")

if __name__ == "__main__":
    main()
