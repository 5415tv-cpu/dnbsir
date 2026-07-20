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
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def render_short_form_video(self, user_id, script_json, image_urls=None):
    """
    클라우드 웹 서버에서 이 함수를 호출하면, 
    로컬 PC가 이 함수 안의 내용을 실행합니다.
    """
    import time
    import shutil
    import requests
    from pathlib import Path
    import sys

    # media_worker 연동
    ROOT = Path(r"C:\Users\A\Desktop\AI_Store")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    
    from media_worker.pipeline.tts_sync import generate_sync_metadata
    from media_worker.renderer.video_renderer import render_premium_shortform_video
    
    print(f"[작업 시작] 사용자 {user_id}의 프리미엄 영상 렌더링 지시 수신 완료")
    
    try:
        JOB_ID = f"premium-{user_id}-{int(time.time())}"
        
        # 1. TTS 생성
        TTS_DIR = ROOT / "media_worker" / "output" / f"{JOB_ID}_tts"
        TTS_DIR.mkdir(parents=True, exist_ok=True)
        
        print(f"[{user_id}] 1. TTS 생성 시작...")
        sync_metadata = generate_sync_metadata(
            script=script_json,
            work_dir=TTS_DIR,
            google_voice="ko-KR-Neural2-C",
            openai_voice="onyx",
            openai_model="tts-1-hd",
            bgm_preset=1
        )
        
        # 2. 프리미엄 렌더링
        print(f"[{user_id}] 2. GPU 가속 영상 렌더링 시작...")
        assets = {
            "bg_images": [], # 추후 image_urls 다운로드 로직 추가 시 확장
            "tts_voice": "onyx",
            "tts_model": "tts-1-hd",
            "bgm_preset": 1,
            "render": {
                "resolution": "1080x1920",
                "fps": 30,
                "bitrate": "8M",
                "bg_color": "#0A0E1A"
            },
            "subtitle_style": {
                "title_size": 68,
                "body_size":  46,
                "color":      "#FFFFFF",
                "highlight":  "#FFD700"
            }
        }
        
        render_result = render_premium_shortform_video(
            job_id=JOB_ID,
            script_json=script_json,
            sync_metadata=sync_metadata,
            assets=assets
        )
        
        # 3. 완성된 영상을 정적 서빙 폴더로 이동
        final_video_path = Path(render_result["output_path"])
        static_video_dir = ROOT / "static" / "videos"
        static_video_dir.mkdir(parents=True, exist_ok=True)
        
        serve_path = static_video_dir / f"{JOB_ID}.mp4"
        shutil.copy(str(final_video_path), str(serve_path))
        print(f"[{user_id}] 3. 영상 렌더링 성공! 웹 서빙 경로: {serve_path}")
        
        base_url = os.environ.get("APP_BASE_URL", "https://dongnebiseo.com")
        video_url = f"{base_url.rstrip('/')}/videos/{JOB_ID}.mp4"
        
        import urllib.request
        from datetime import datetime
        import uuid
        import hmac
        import hashlib
        import json
        
        api_key = os.environ.get("SOLAPI_API_KEY")
        api_secret = os.environ.get("SOLAPI_API_SECRET")
        sender = os.environ.get("SOLAPI_SENDER_NUMBER")
        pf_id = os.environ.get("SOLAPI_PF_ID")
        template_id = os.environ.get("SOLAPI_TEMPLATE_ID")
        
        if api_key and api_secret and pf_id:
            print(f"[{user_id}] 4. 카카오 알림톡 발송 시작...")
            receiver = user_id if user_id.startswith('010') else sender 
            
            date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            salt = str(uuid.uuid4().hex)
            msg = date + salt
            signature = hmac.new(api_secret.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()
            auth = f'HMAC-SHA256 apiKey={api_key}, date={date}, salt={salt}, signature={signature}'
            
            headers = {
                'Authorization': auth,
                'Content-Type': 'application/json'
            }
            
            # 테스트용 변수. 템플릿에 맞게 수정 필요 시 여기에 매핑
            variables = {
                "#{url}": video_url
            }
            
            data = {
                "message": {
                    "to": receiver,
                    "from": sender,
                    "kakaoOptions": {
                        "pfId": pf_id,
                        "templateId": template_id,
                        # "variables": variables # 실제 템플릿 변수가 있을 경우 사용
                    },
                    "text": f"[동네비서] 고객님의 홍보 영상이 완성되었습니다!\n확인하기: {video_url}"
                }
            }
            
            try:
                req = urllib.request.Request("https://api.solapi.com/messages/v4/send", data=json.dumps(data).encode('utf-8'), headers=headers)
                response = urllib.request.urlopen(req)
                print(f"[{user_id}] - 알림톡/메시지 발송 완료! Response: {response.read().decode('utf-8')}")
            except Exception as e:
                print(f"[{user_id}] - 카카오 발송 실패: {e}")
        else:
            print(f"[{user_id}] - SOLAPI 설정이 누락되어 발송하지 않습니다.")
        
        return {
            'status': 'success',
            'user_id': user_id,
            'result': video_url
        }

    except Exception as exc:
        print(f"[에러 발생] {user_id} 렌더링 중 오류: {exc}")
        import traceback
        traceback.print_exc()
        raise self.retry(exc=exc)

if __name__ == '__main__':
    # 이 스크립트를 직접 실행할 때 터미널에 띄울 안내 메시지
    print("==========================================================")
    print(" 동네비서 로컬 렌더링 워커 (RTX 4070) 준비 완료")
    print(" 실행 방법: 터미널에서 'celery -A worker worker --loglevel=info' 입력")
    print("==========================================================")
