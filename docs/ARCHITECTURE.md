# 동네비서 시스템 아키텍처 청사진

> **운영 주체**: 탄탄제작소 (Tantan Fabrication) — 인프라 홀더  
> **서비스 브랜드**: 동네비서 (Dongnebiseo) — AI 키오스크 애플리케이션  
> **최종 구조조정**: 2026-07-05 (v1.3.0)  
> **국내 서버 기준**: `kr-central1` (한국 서버 인프라)

---

## 1. 전체 시스템 구조도

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  탄탄제작소 (Tantan Fabrication)                         │
│                  인프라 홀더 — 서버 루트 권한 영역                        │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Nginx (infra/nginx/nginx_dongnebiseo.conf)                      │   │
│  │  → HTTPS 종료, 리버스 프록시, 업로드 auth_request 검증           │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
│                           │                                             │
│           ┌───────────────┼───────────────────┐                        │
│           ▼               ▼                   ▼                        │
│  ┌────────────────┐  ┌──────────────┐  ┌────────────────────────┐     │
│  │ dongnebiseo-   │  │    Redis     │  │   media-worker         │     │
│  │ app            │  │  (큐 브로커) │  │  (숏폼 워커, 격리)     │     │
│  │ :8080          │  │  DB0: 앱캐시 │  │  Celery + GPU          │     │
│  │ 메모리: 2G     │  │  DB1: 워커큐 │  │  메모리: 8G            │     │
│  └───────┬────────┘  └──────┬───────┘  └──────────┬─────────────┘     │
│          │                  │                      │                   │
│          └──────────────────┼──────────────────────┘                   │
│                             ▼                                           │
│                   ┌─────────────────┐                                  │
│                   │   PostgreSQL    │                                  │
│                   │   (kr-central1) │                                  │
│                   │   메모리: 1G    │                                  │
│                   └─────────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 폴더 구조 → 컨테이너 매핑

```
AI_Store/  (Git 저장소 루트)
│
├── dongnebiseo_app/          ◄─── 🟦 [동네비서 앱 영역]
│   ├── config/
│   │   └── settings.py       # TantanInfraSettings + DongnebiseoAppSettings
│   └── services/
│       ├── ai_service.py     # Gemini API 클라이언트 (설정 주입 방식)
│       └── rag_service.py    # RAG 그라운딩 + 3단계 Fallback
│
├── routers/                  ◄─── 🟦 [동네비서 라우터 21개]
│   ├── auth.py, admin.py, citizen.py, webhooks.py ...
│   └── video_order.py        # 미디어 업로드 토큰 발급 (워커 경계)
│
├── templates/                ◄─── 🟦 [동네비서 UI — 72개 HTML]
├── static/                   ◄─── 🟦 [정적 파일]
├── app.py                    ◄─── 🟦 [FastAPI 진입점]
├── main.py                   # Docker CMD 진입점 (app.py로 라우팅)
│
├── tantan_infra/             ◄─── 🟥 [탄탄제작소 웹사이트]
│   ├── tantan_app.py         # Flask 앱 (영상 제작 서비스 웹사이트)
│   ├── tantan_services_pg.py # DB 서비스 레이어
│   └── Dockerfile            # 탄탄제작소 앱 독립 Docker
│
├── media_worker/             ◄─── 🟨 [숏폼 미디어 워커 — 완전 격리]
│   ├── worker.py             # Celery 워커 진입점
│   ├── tasks/                # 영상 생성, SVD 렌더러, GPU 브릿지
│   ├── pipeline/             # 다큐 파이프라인
│   ├── comfy/                # ComfyUI 워크플로우 JSON
│   ├── requirements.txt      # 미디어 전용 의존성 (torch 등 분리)
│   └── Dockerfile.worker     # GPU 워커 전용 Docker
│
├── infra/                    ◄─── 🟥 [탄탄제작소 인프라 설정]
│   ├── docker/
│   │   └── docker-compose.yml  # 멀티 컨테이너 정의 (이 파일)
│   ├── nginx/
│   │   └── nginx_dongnebiseo.conf
│   └── scripts/
│       └── block_attack.sh
│
├── deprecated/               ◄─── 🗄️ [아카이브 — 30일 후 삭제 예정]
│   ├── diagnostics/ (185개)  # check_*.py
│   ├── hotfixes/ (20개)      # fix_*.py
│   ├── debug/ (12개)
│   ├── deploy_scripts/ (13개)
│   ├── test_scripts/ (37개)
│   └── temp_logs/ (81개)
│
├── db_manager.py             # DB 추상화 레이어 (SQLite ↔ PostgreSQL)
├── config.py                 # 레거시 호환 브릿지 → dongnebiseo_app/config/
├── requirements.txt          # 메인 앱 의존성
├── Dockerfile                # 메인 앱 Docker
└── .env.example              # 환경변수 템플릿 (TANTAN_* / 동네비서 구분)
```

---

## 3. 컨테이너 역할 및 경계

| 컨테이너 | 이미지 | 메모리 | 역할 | 소유 영역 |
|---------|--------|--------|------|----------|
| `dongnebiseo-app` | `dnbsir-app` | **2G** | 키오스크 UI + AI 비즈니스 로직 | 🟦 동네비서 |
| `media-worker` | `dnbsir-media-worker` | **8G** | 숏폼 영상 생성 (Celery) | 🟥 탄탄제작소 |
| `redis` | `redis:7-alpine` | 512MB | 태스크 큐 브로커 | 🟥 탄탄제작소 |
| `db` | `postgres:16-alpine` | **1G** | 메인 데이터베이스 | 🟥 탄탄제작소 |

> [!NOTE]
> `media-worker`는 Docker Compose `profiles: [with-worker]`로 분리되어 있어 기본 `docker compose up`으로는 시작되지 않습니다. GPU 서버에서만 `docker compose --profile with-worker up -d`로 실행합니다.

---

## 4. 데이터 흐름 다이어그램

### 4.1 부재중 전화 자동 응답 (핵심 서비스)

```
고객 전화 ──► NHN 전화 서비스
                    │
                    ▼ POST /webhook/missed-call
            [dongnebiseo-app]
            routers/webhooks.py
                    │
                    ▼
            RAGService.get_missed_call_response()
            ┌───────────────────────────────────┐
            │ ① 로컬 캐시 확인 (즉시 반환)       │
            │ ② DB 컨텍스트 조회 (그라운딩)       │
            │ ③ Gemini API 호출                  │ ◄─ asyncio.timeout(8s)
            │ ④ Fallback (타임아웃/오류 시)       │
            └───────────────────────────────────┘
                    │ SMS 문구 생성
                    ▼
            sms_manager.py (Solapi)
                    │
                    ▼ SMS 발송
              고객 휴대폰
```

### 4.2 숏폼 영상 생성 (미디어 워커)

```
관리자 요청 ──► [dongnebiseo-app]
                routers/video_order.py
                    │ 업로드 토큰 발급 (5분 유효)
                    ▼
              [Redis DB1]  ◄─────────────────┐
                    │ Celery 태스크 큐        │
                    ▼                        │
              [media-worker]                 │ 결과 저장
              tasks/video_generation.py      │
                    │                        │
                    ▼ ComfyUI API            │
              RTX 4070 (로컬 GPU)            │
              또는 Vultr GPU 서버 ───────────┘
```

### 4.3 RAG 환각 방지 프롬프트 구조

```
사용자 쿼리 ("딸기 가격이 얼마에요?")
       │
       ▼
[DB 컨텍스트 조회] ─── stores 테이블에서 매장 정보 추출
       │
       ▼
[그라운딩 프롬프트 구성]
┌────────────────────────────────────────────────────────┐
│ [절대 규칙]                                             │
│ 1. 아래 [매장 정보]에 있는 내용만 사용하여 답변하세요.   │
│ 2. [매장 정보]에 없는 내용은 절대 추측하지 마세요.       │
│ 3. 모르는 내용은 "사장님께 직접 확인이 필요합니다"       │
│                                                        │
│ [매장 정보]                                             │
│ { "store_name": "홍길동 딸기농장",                      │
│   "auto_reply_text": "딸기 2kg 15,000원입니다...",      │
│   "today_orders": 5, "today_sales": 75000 }           │
│                                                        │
│ [고객 문의]                                             │
│ 딸기 가격이 얼마에요?                                    │
└────────────────────────────────────────────────────────┘
       │ Gemini Flash (8초 타임아웃)
       ▼
"딸기 2kg 기준 15,000원입니다. 감사합니다! 🍓"
```

---

## 5. 설정 영역 분리 (코드 레벨)

```python
# dongnebiseo_app/config/settings.py

# 🟥 탄탄제작소 인프라 영역 (TANTAN_ prefix)
class TantanInfraSettings(BaseSettings):
    database_url: str       # PostgreSQL (한국 서버)
    redis_url: str          # Celery 큐 브로커
    server_region: str      # "kr-central1"
    tantan_upload_secret: str  # 미디어 워커 시크릿
    # ...
    class Config:
        env_prefix = "TANTAN_"

# 🟦 동네비서 앱 영역 (레거시 키명 alias)
class DongnebiseoAppSettings(BaseSettings):
    gemini_api_key: str     # alias="GOOGLE_API_KEY"
    solapi_api_key: str     # alias="SOLAPI_API_KEY"
    toss_secret_key: str    # alias="TOSS_SECRET_KEY"
    ai_timeout_sec: float   # 8.0초 (Fallback 트리거)
    ai_hallucination_guard: bool  # True (환각 방지 강제)
    # ...
```

---

## 6. 운영 명령어 치트시트

### 기본 실행 (메인 앱만)
```bash
cd infra/docker
docker compose up -d
docker compose logs -f dongnebiseo-app
```

### 숏폼 워커 포함 실행 (GPU 서버)
```bash
docker compose --profile with-worker up -d
docker compose logs -f media-worker
```

### 무중단 배포 (Zero-downtime)
```bash
# 1. 새 이미지 빌드
docker compose build dongnebiseo-app

# 2. 롤링 재시작 (Nginx가 트래픽 유지)
docker compose up -d --no-deps --scale dongnebiseo-app=2 dongnebiseo-app
sleep 10
docker compose up -d --no-deps --scale dongnebiseo-app=1 dongnebiseo-app
```

### 서비스별 재시작
```bash
docker compose restart dongnebiseo-app   # 메인 앱만
docker compose restart media-worker       # 미디어 워커만 (메인 앱 무영향)
docker compose restart redis              # 캐시 초기화
```

### deprecated/ 폴더 최종 삭제 (30일 후)
```bash
# 운영 서버에서 참조 여부 확인 후 실행
rm -rf deprecated/
git add .gitignore
git commit -m "chore: remove deprecated archive folder"
```

---

## 7. 장애 대응 매뉴얼 (정비 최적화)

| 증상 | 격리 범위 | 조치 |
|------|---------|------|
| AI 응답 없음 | 🟦 동네비서만 | RAGService Fallback 자동 발동 (서비스 무중단) |
| Gemini API 할당량 초과 | 🟦 AI 레이어만 | `ai_timeout_sec` 조정, Flash 모델로 전환 |
| 영상 생성 실패 | 🟨 media-worker만 | 메인 앱 무영향, 워커만 재시작 |
| DB 연결 오류 | 🟥 탄탄제작소 | `docker compose restart db`, 백업 복구 |
| Redis 다운 | 🟥 탄탄제작소 | 앱 캐시 초기화되나 서비스 지속, 재시작 |
| OOM (메모리 초과) | 컨테이너별 격리 | 해당 컨테이너만 재시작 (다른 서비스 무영향) |

> [!TIP]
> 메모리 격리가 핵심: `media-worker`(8G)가 OOM으로 사망해도 `dongnebiseo-app`(2G)은 계속 운영됩니다.

---

## 8. 버전 이력

| 버전 | 날짜 | 주요 변경 |
|------|------|---------|
| v1.0.0 | 2026-02-10 | 최초 릴리즈 (단일 서버 구조) |
| v1.2.1 | 2026-07-05 | Phase 1: 보안 패치, 파일 격리 (349개 deprecated) |
| v1.3.0 | 2026-07-05 | Phase 2: Pydantic 설정 분리, RAG 서비스 독립화 |
| **v1.4.0** | **2026-07-05** | **Phase 3: 폴더 경계 확정, 멀티 컨테이너 완성** |
