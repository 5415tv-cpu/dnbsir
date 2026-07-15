"""
media_worker 설정 — Pydantic BaseSettings
탄탄제작소 인프라 설정과 분리된 워커 전용 설정
"""
from pydantic_settings import BaseSettings
import os


class WorkerConfig(BaseSettings):
    """숏폼 미디어 워커 전용 설정 — 환경변수 자동 주입"""
    
    # Redis (탄탄제작소 인프라 영역)
    redis_url: str = os.environ.get('DONGNE_REDIS_URL', 'redis://localhost:6379/1')
    
    # ComfyUI 연결 (로컬 GPU 서버)
    comfyui_host: str = "localhost"
    comfyui_port: int = 8188
    
    # GPU 작업 큐 (Vultr 클라우드 — tantanfab.com)
    tantan_gpu_api_url: str = "http://tantanfab.com/api/gpu"
    tantan_api_key: str = ""
    
    # 동네비서 업로드 토큰 검증 (분리된 서비스 경계)
    dnbsir_upload_secret: str = "dnbsir-tantan-2024"
    dnbsir_api_base: str = "https://api.dnbsir.com"
    
    # 미디어 설정 — 환경변수 MEDIA_WORKER_OUTPUT_DIR 또는 기본값
    output_dir: str = "/var/www/dnbsir/static/output"
    max_video_duration_sec: int = 60
    default_fps: int = 8
    
    class Config:
        env_file = ".env"
        env_prefix = "MEDIA_WORKER_"
        case_sensitive = False
