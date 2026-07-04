# 동네비서 숏폼 미디어 워커 운영 가이드

> **운영 주체**: 탄탄제작소 (Tantan Fabrication)  
> **서비스**: 동네비서 로컬 홍보 숏폼 영상 생성 파이프라인  
> **격리 원칙**: 메인 웹 서버(api.dnbsir.com)와 물리적·논리적으로 완전 분리  

---

## 아키텍처

```
[동네비서 앱] api.dnbsir.com
    └── routers/video_order.py (업로드 토큰 발급만 담당)
              │
              ↓ (업무 위임 — HTTP 토큰 발급)
[탄탄제작소 인프라]
    ├── Redis (태스크 큐 브로커)
    │       │
    │       ↓ (Celery 태스크)
    └── media_worker/ (이 프로젝트)
            ├── tasks/video_generation.py  ← 숏폼 영상 생성
            ├── tasks/svd_renderer.py      ← SVD 배치 렌더링
            ├── tasks/gpu_worker.py        ← GPU 브릿지 워커
            └── pipeline/master_pipeline.py ← 통합 파이프라인
```

---

## 시작 방법

### 1. 환경 설정
```bash
cp .env.example .env
# .env 파일에서 Redis URL, ComfyUI 주소, GPU 서버 설정
```

### 2. Redis 실행 (Docker)
```bash
docker run -d --name dnbsir-redis -p 6379:6379 redis:7-alpine
```

### 3. Celery 워커 실행

**로컬 GPU 환경:**
```bash
pip install -r requirements.txt
# GPU 전용 패키지 추가 설치
pip install torch diffusers transformers accelerate

celery -A worker worker --loglevel=info --concurrency=1 -Q media_tasks
```

**Docker 환경 (GPU 서버):**
```bash
docker build -f Dockerfile.worker -t dnbsir-media-worker .
docker run --gpus all --memory=8g --shm-size=2g \
    -e REDIS_URL=redis://redis:6379/1 \
    dnbsir-media-worker
```

---

## 태스크 큐 모니터링
```bash
# Celery Flower (웹 모니터링 UI)
pip install flower
celery -A worker flower --port=5555
```

---

## OOM 방지 설정

| 설정 | 값 | 이유 |
|------|----|------|
| `worker_max_tasks_per_child` | 5 | 5개 작업 후 프로세스 재시작 (메모리 해제) |
| `worker_prefetch_multiplier` | 1 | 한 번에 1개 태스크만 |
| `task_soft_time_limit` | 1800s | 30분 소프트 제한 |
| `task_time_limit` | 3600s | 60분 하드 제한 (강제 종료) |
| Docker `--memory` | 8g | 컨테이너 메모리 상한 |

---

## 디렉토리 구조

```
media_worker/
├── worker.py                    ← Celery 앱 진입점
├── requirements.txt             ← 미디어 전용 의존성 (메인 앱과 분리)
├── Dockerfile.worker            ← GPU 워커 전용 Docker
├── README.md                    ← 이 파일
├── config/
│   └── worker_config.py         ← Pydantic BaseSettings
├── tasks/
│   ├── video_generation.py      ← 숏폼 영상 생성 (ComfyUI + SVD)
│   ├── svd_renderer.py          ← 배치 SVD 렌더링
│   └── gpu_worker.py            ← 로컬 GPU ↔ 클라우드 브릿지
├── pipeline/
│   └── master_pipeline.py       ← T2I + SVD 통합 다큐 파이프라인
├── comfy/
│   ├── sd15_t2i_workflow.json   ← SD1.5 텍스트→이미지 워크플로우
│   ├── svd_gui_workflow.json    ← SVD 영상 생성 워크플로우
│   └── svd_highres_workflow.json ← SVD 고해상도 워크플로우
└── scripts/
    ├── start_ai_documentary.bat ← Windows 배치 실행 (레거시 참조용)
    └── run_master_pipeline.bat  ← 파이프라인 배치 실행 (레거시 참조용)
```
