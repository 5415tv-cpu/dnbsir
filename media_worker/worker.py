"""
동네비서 숏폼 마케팅 — Celery 워커 진입점
운영 주체: 탄탄제작소 (Tantan Fabrication) 인프라
서비스: 동네비서 (Dongnebiseo) 로컬 홍보 숏폼 영상 생성 파이프라인

[격리 원칙]
- 이 워커는 메인 웹/API 서버(dongnebiseo FastAPI)와 물리적·논리적으로 완전히 분리됨
- 메모리 초과(OOM) 방지를 위해 Docker 컨테이너 메모리 상한 설정 필수
- 외부 의존: Redis(태스크 큐) + ComfyUI API(로컬 GPU 또는 클라우드)

[실행 방법]
    # Redis 실행 (별도 컨테이너)
    # docker run -d -p 6379:6379 redis:7-alpine

    # Celery 워커 실행
    celery -A worker worker --loglevel=info --concurrency=1 -Q media_tasks
    
    # 또는 Docker
    docker build -f Dockerfile.worker -t dnbsir-media-worker .
    docker run --gpus all --memory=8g dnbsir-media-worker
"""
import os
from celery import Celery
from celery.utils.log import get_task_logger
from config.worker_config import WorkerConfig

logger = get_task_logger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Celery 앱 초기화 — Redis 브로커 (탄탄제작소 인프라 영역)
# ─────────────────────────────────────────────────────────────────────
cfg = WorkerConfig()

celery_app = Celery(
    "dnbsir_media_worker",
    broker=cfg.redis_url,
    backend=cfg.redis_url,
    include=[
        "tasks.video_generation",
        "tasks.svd_renderer",
        "tasks.gpu_worker",
    ]
)

# Celery 설정
celery_app.conf.update(
    # 큐 설정
    task_queues={
        "media_tasks": {"exchange": "media_tasks", "routing_key": "media_tasks"},
    },
    task_default_queue="media_tasks",
    
    # 재시도 정책 (OOM/타임아웃 대비)
    task_acks_late=True,               # 작업 완료 후 ACK (재시도 보장)
    task_reject_on_worker_lost=True,   # 워커 사망 시 재큐잉
    task_max_retries=3,
    
    # 메모리 OOM 방지
    worker_max_tasks_per_child=5,      # 5개 작업 후 워커 프로세스 재시작 (메모리 해제)
    worker_prefetch_multiplier=1,      # 한 번에 1개 태스크만 가져옴
    
    # 타임아웃
    task_soft_time_limit=1800,         # 30분 소프트 제한
    task_time_limit=3600,              # 60분 하드 제한
    
    # 직렬화
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    
    # 타임존 (한국 서버 기준)
    timezone="Asia/Seoul",
    enable_utc=True,
)


# ─────────────────────────────────────────────────────────────────────
# 헬스체크 태스크
# ─────────────────────────────────────────────────────────────────────
@celery_app.task(name="worker.health_check")
def health_check():
    """워커 상태 확인 태스크"""
    logger.info("media_worker health check OK")
    return {"status": "ok", "worker": "dnbsir_media_worker"}


if __name__ == "__main__":
    celery_app.start()
