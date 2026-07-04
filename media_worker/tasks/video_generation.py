"""ComfyUI 실행 + SVD 영상 생성 통합 스크립트"""
import subprocess, sys, time, json, urllib.request, shutil, os, glob, threading

COMFY_DIR = r"C:\Users\A\Desktop\AI_Store\core_engine\ComfyUI"
BASE = "http://127.0.0.1:17860"
SRC = r"C:\Users\A\.gemini\antigravity\brain\a20de2cb-8d70-408d-ae8d-fb3c713d3f01\strawberry_family_1781541436520.png"
DST = os.path.join(COMFY_DIR, "input", "strawberry_family.png")
OUT = os.path.join(COMFY_DIR, "output")
FINAL = r"C:\Users\A\Desktop\AI_Store\static\videos\strawberry_family.mp4"

WF = {
  "1":{"class_type":"ImageOnlyCheckpointLoader","inputs":{"ckpt_name":"svd_xt.safetensors"}},
  "2":{"class_type":"LoadImage","inputs":{"image":"strawberry_family.png","upload":"image"}},
  "3":{"class_type":"SVD_img2vid_Conditioning","inputs":{"clip_vision":["1",1],"init_image":["2",0],"vae":["1",2],"width":1024,"height":576,"video_frames":25,"motion_bucket_id":100,"fps":8,"augmentation_level":0.0}},
  "4":{"class_type":"KSampler","inputs":{"model":["1",0],"positive":["3",0],"negative":["3",1],"latent_image":["3",2],"seed":42,"steps":20,"cfg":2.5,"sampler_name":"euler","scheduler":"karras","denoise":1.0}},
  "5":{"class_type":"VAEDecode","inputs":{"samples":["4",0],"vae":["1",2]}},
  "6":{"class_type":"VHS_VideoCombine","inputs":{"images":["5",0],"frame_rate":8,"loop_count":0,"filename_prefix":"strawberry_family","format":"video/h264-mp4","pix_fmt":"yuv420p","crf":19,"save_metadata":True,"pingpong":False,"save_output":True}}
}

# 1. ComfyUI 서브프로세스로 실행 (같은 프로세스 그룹)
print("Starting ComfyUI...")
proc = subprocess.Popen(
    [sys.executable, "main.py", "--port", "17860"],
    cwd=COMFY_DIR,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True, encoding="utf-8", errors="replace"
)

# 로그를 백그라운드 스레드로 출력
def log_reader():
    for line in proc.stdout:
        print("[COMFY]", line.rstrip())
t = threading.Thread(target=log_reader, daemon=True)
t.start()

# 2. READY 대기
print("Waiting for ComfyUI...")
for i in range(60):
    time.sleep(3)
    try:
        urllib.request.urlopen(BASE+"/system_stats", timeout=2)
        print(f"ComfyUI READY at {(i+1)*3}s")
        break
    except:
        pass
else:
    print("TIMEOUT waiting for ComfyUI")
    proc.terminate()
    sys.exit(1)

# 3. 이미지 복사
shutil.copy2(SRC, DST)
print("Image copied to input/")

# 4. 워크플로우 제출
data = json.dumps({"prompt": WF}).encode()
req = urllib.request.Request(BASE+"/prompt", data=data, headers={"Content-Type":"application/json"})
resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
pid = resp["prompt_id"]
print("Job submitted:", pid)

# 5. 완료 대기 + output 폴더 감시
print("Rendering... (RTX 4070 Ti)")
t0 = time.time()
while time.time() - t0 < 600:
    time.sleep(5)
    elapsed = int(time.time()-t0)
    
    # history 확인
    try:
        h = json.loads(urllib.request.urlopen(BASE+"/history/"+pid, timeout=5).read())
        if pid in h and h[pid].get("status",{}).get("completed"):
            print(f"\nCompleted at {elapsed}s!")
            break
    except: pass
    
    # output 폴더에서 새 mp4 확인
    mp4s = sorted(glob.glob(os.path.join(OUT, "strawberry_family*.mp4")), key=os.path.getmtime, reverse=True)
    if mp4s and os.path.getmtime(mp4s[0]) > t0:
        print(f"\nFound output at {elapsed}s: {mp4s[0]}")
        break
    
    print(f"\r[{elapsed}s] rendering...", end="", flush=True)

# 6. 결과 찾기 및 복사
mp4s = sorted(glob.glob(os.path.join(OUT, "strawberry_family*.mp4")), key=os.path.getmtime, reverse=True)
if not mp4s:
    mp4s = sorted(glob.glob(os.path.join(OUT, "*.mp4")), key=os.path.getmtime, reverse=True)

if mp4s:
    newest = mp4s[0]
    os.makedirs(os.path.dirname(FINAL), exist_ok=True)
    shutil.copy2(newest, FINAL)
    mb = round(os.path.getsize(FINAL)/1024/1024, 1)
    print(f"\nDONE: {FINAL} ({mb} MB)")
else:
    print("\nNO MP4 found. Files in output:", os.listdir(OUT)[:10])

proc.terminate()
