from celery import Celery
import time
import os
import requests
import json
import urllib.request
import urllib.error
import subprocess

# 1단계: Celery 인스턴스 설정 및 클라우드 Redis 연결
# 환경 변수 DONGNE_REDIS_URL로 암호화 및 하드코딩 방지
REDIS_URL = os.environ.get('DONGNE_REDIS_URL', 'redis://localhost:6379/0')

app = Celery(
    'dongne_biseo_worker',
    broker=REDIS_URL,
    backend=REDIS_URL  # 작업 결과(상태)를 저장할 곳도 동일한 Redis 사용
)

# Celery 옵션 설정 (에러 통제 및 로컬 하드웨어 보호)
app.conf.update(
    worker_concurrency=1,            # 중요: RTX 4070 1대로 동시 렌더링 시 OOM 방지를 위해 한 번에 1개의 작업만 직렬 처리
    worker_prefetch_multiplier=1,    # 워커가 미리 가져올 작업 수 1개로 고정 (메모리 독점 방지)
    task_acks_late=True,             # 작업이 완전히 끝난 후(성공)에만 큐에서 삭제 (중간에 뻗어도 재시도 가능)
    task_reject_on_worker_lost=True, # 워커 프로세스가 비정상 종료되면 작업을 큐로 반환
    task_time_limit=300              # 중요: 1개의 영상 렌더링이 5분(300초)을 넘기면 강제 종료 (무한 루프 에러 차단)
)

# ComfyUI 서버 기본 주소 (로컬 PC)
COMFYUI_SERVER_URL = "http://127.0.0.1:8188"

def queue_prompt(prompt_workflow):
    """ComfyUI에 렌더링 작업을 큐(Queue)에 넣는 함수"""
    p = {"prompt": prompt_workflow}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"{COMFYUI_SERVER_URL}/prompt", data=data, headers={'Content-Type': 'application/json'})
    response = urllib.request.urlopen(req)
    return json.loads(response.read())

def get_history(prompt_id):
    """ComfyUI의 작업 완료 기록을 확인하는 함수"""
    with urllib.request.urlopen(f"{COMFYUI_SERVER_URL}/history/{prompt_id}") as response:
        return json.loads(response.read())

# 2단계: 실제 렌더링 작업을 수행하는 함수 정의 (Task)
# @app.task 데코레이터가 붙은 함수가 Redis 큐에 들어오는 작업 단위가 됩니다.
@app.task(bind=True, max_retries=2, default_retry_delay=60) # 실패 시 60초 후 재시도 (최대 2번)
def render_short_form_video(self, user_id, image_url, text_prompt):
    """
    클라우드 웹 서버에서 이 함수를 호출하면, 
    로컬 PC가 이 함수 안의 내용을 실행합니다.
    """
    print(f"[작업 시작] 사용자 {user_id}의 영상 렌더링 지시 수신 완료")
    
    try:
        print(f"[{user_id}] 1. 원본 이미지 데이터 확인: {image_url}")
        
        # 주의: 실제 상용 서비스 시에는 ComfyUI에서 'Save (API Format)'로 내보낸 
        # 복잡한 워크플로우 JSON으로 교체해야 합니다. 아래는 가장 기초적인 Text-to-Image 예시입니다.
        prompt_workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": int(time.time()), # 매번 다른 결과 생성을 위한 난수 시드
                    "steps": 20,
                    "cfg": 8,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                }
            },
            "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}},
            "5": {"class_type": "EmptyLatentImage", "inputs": {"batch_size": 1, "width": 512, "height": 512}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": text_prompt, "clip": ["4", 1]}}, # 고객 프롬프트 주입
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "bad quality, blurry, worst quality", "clip": ["4", 1]}},
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": f"dongne_{user_id}", "images": ["8", 0]}}
        }
        
        print(f"[{user_id}] 2. RTX 4070 GPU 렌더링 시작 (ComfyUI 연동)... 프롬프트: {text_prompt}")
        
        # ComfyUI로 작업 전송
        queued_data = queue_prompt(prompt_workflow)
        prompt_id = queued_data['prompt_id']
        print(f"[{user_id}] - ComfyUI 작업 할당 성공 (Prompt ID: {prompt_id})")
        
        # 작업 완료 대기 (무한 루프 방지를 위해 Celery 타임아웃 300초 제한의 보호를 받음)
        result_filename = "unknown_error.png"
        while True:
            history = get_history(prompt_id)
            # 렌더링이 끝나면 history 딕셔너리에 prompt_id 키가 생성됨
            if prompt_id in history:
                print(f"[{user_id}] - ComfyUI 렌더링 완료!")
                
                # 결과물 파일명 추출 로직
                outputs = history[prompt_id]['outputs']
                for node_id in outputs:
                    node_output = outputs[node_id]
                    if 'images' in node_output: # 또는 영상일 경우 'gifs', 'videos' 등
                        image_data = node_output['images'][0]
                        result_filename = image_data['filename']
                        break
                break
            
            print(f"[{user_id}] - 렌더링 진행 중... (5초 후 상태 재확인)")
            time.sleep(5)
            
        # ComfyUI 기본 output 폴더 경로 (환경에 따라 수정 필요)
        comfy_output_path = f"C:/ComfyUI/output/{result_filename}"
        
        # 3. FFmpeg를 이용한 영상 인코딩 및 워터마크 합성
        final_video_path = f"C:/ComfyUI/output/final_{user_id}.mp4"
        print(f"[{user_id}] 3. FFmpeg 영상 인코딩 및 워터마크 합성 시작")
        
        # 예시: 생성된 이미지를 바탕으로 5초짜리 mp4 영상 생성 (실제로는 프레임 이미지 조합 등 사용)
        try:
            subprocess.run([
                "ffmpeg", "-y", 
                "-loop", "1", "-i", comfy_output_path, 
                "-c:v", "libx264", "-t", "5", "-pix_fmt", "yuv420p", 
                final_video_path
            ], check=True, capture_output=True)
            print(f"[{user_id}] - FFmpeg 렌더링 성공! 최종 영상: {final_video_path}")
        except Exception as e:
            print(f"[{user_id}] - FFmpeg 인코딩 에러 발생: {e}")
            final_video_path = comfy_output_path # 실패 시 원본 이미지 경로 반환
            
        # 4단계: 렌더링 완료된 영상을 클라우드 웹 서버로 전송 (또는 스토리지 업로드)
        # 렌더링 결과(URL 등)를 클라우드 웹 서버의 Webhook으로 쏴주어, 
        # 클라우드 서버가 고객에게 카카오 알림톡을 발송하게 합니다.
        # webhook_url = 'http://cloud-server-ip/api/rendering/complete'
        # requests.post(webhook_url, json={'user_id': user_id, 'video_url': final_video_path})
        
        return {
            'status': 'success',
            'user_id': user_id,
            'result': final_video_path
        }

    except Exception as exc:
        print(f"[에러 발생] {user_id} 렌더링 중 오류: {exc}")
        # 예상치 못한 에러(메모리 부족, 네트워크 단절 등) 발생 시 재시도 트리거
        raise self.retry(exc=exc)

if __name__ == '__main__':
    # 이 스크립트를 직접 실행할 때 터미널에 띄울 안내 메시지
    print("==========================================================")
    print(" 동네비서 로컬 렌더링 워커 (RTX 4070) 준비 완료")
    print(" 실행 방법: 터미널에서 'celery -A worker worker --loglevel=info' 입력")
    print("==========================================================")
