# Changelog

## 2026-07-05 — 시스템 모듈화 구조조정 Phase 3 (v1.4.0)

### 📁 폴더 경계 확정 (물리적 분리 완성)
- **`dongnebiseo/` → `dongnebiseo_app/`** 이름 변경: 앱 비즈니스 로직 영역 명확화
- **`tantan_web/` → `tantan_infra/`** 이름 변경: 탄탄제작소 인프라 홀더 영역 명확화
- 임포트 경로 전체 갱신: `dongnebiseo.config.settings` → `dongnebiseo_app.config.settings`
- BOM (Byte Order Mark) 인코딩 오류 수정 및 재검증 완료

### 🐳 docker-compose.yml 최종 확정
- 4개 서비스 경계 주석 완성 (탄탄제작소/동네비서 역할 명시)
- `media-worker` → Docker Compose `profiles: [with-worker]`로 분리
  - 기본 `docker compose up`으로는 미시작, GPU 서버에서만 별도 실행
  - Redis DB 인덱스 분리 (DB0: 앱 캐시, DB1: 워커 태스크 큐)
- PostgreSQL 한국 서버 타임존 설정 (`TZ: Asia/Seoul`)
- 무중단 배포 명령어 문서화

### 📚 최종 문서화
- **`docs/ARCHITECTURE.md`** 신설: 시스템 청사진 (아스키 다이어그램 포함)
  - 전체 시스템 구조도 (탄탄제작소/동네비서 경계)
  - 폴더 → 컨테이너 매핑 테이블
  - 부재중 전화 자동 응답 데이터 흐름도
  - 숏폼 영상 생성 데이터 흐름도
  - RAG 환각 방지 프롬프트 구조도
  - 장애 대응 매뉴얼 (정비 최적화)
- **`README.md`** 전면 재작성: 빠른 시작 가이드, 3대 원칙 표, 환경변수 영역 구분

### ✅ 최종 검증 결과 (Phase 3)
- Python 구문 검증: **6/6** 통과
- 핵심 디렉토리 확인: **8/8** 존재
- 핵심 파일 확인: **10/10** 존재
- 임포트 경로 검증: **정상**

---

## 2026-07-05 — 시스템 모듈화 구조조정 Phase 2 (v1.3.0)

### ⚙️ 설정 분리 — Pydantic BaseSettings 도입
- **`dongnebiseo/config/settings.py`** 신설: 탄탄제작소 / 동네비서 영역 코드 레벨 분리
  - `TantanInfraSettings` (TANTAN_ prefix): DB 클러스터, 서버, Redis, GCP — 인프라 홀더 영역
  - `DongnebiseoAppSettings` (레거시 키명 alias 지원): Gemini API, Solapi, Toss, RAG 설정 — 앱 브랜드 영역
  - `get_settings()` 싱글톤: lru_cache 기반, 프로세스 당 1회 로드
- **`config.py`**: 레거시 호환 브릿지로 교체 (기존 `config.get_secret()` 호출 무중단)
- **`.env.example`** 신설: TANTAN_* / 레거시 키명 구분 명시

### 🧠 RAG 서비스 레이어 독립화 — 환각 방지 + Fallback
- **`dongnebiseo/services/rag_service.py`** 신설
  - **환각 방지 시스템 프롬프트**: "제공된 DB 데이터 범위 내에서만 답하라" 강제
  - **3단계 Fallback**: 로컬 캐시 → LLM API → 기본 안내 문구 (사용자 에러 화면 없음)
  - **`asyncio.timeout(8.0s)`**: LLM 타임아웃 즉시 Fallback 전환
  - **`_ResponseCache`**: LRU 인메모리 캐시 (최대 200건, TTL 5분) — 중복 LLM 호출 차단
  - **컨텍스트 타입별 Fallback**: missed_call, order, delivery, timeout, api_error 분류

### 🤖 AI 서비스 리팩토링
- **`dongnebiseo/services/ai_service.py`** 신설 (`ai_manager.py` 리팩토링)
  - `config.get_secret()` → `get_settings().app.gemini_api_key` 로 마이그레이션
  - `generate_grounded()` 인터페이스 신설 (RAGService 전용)
  - 레거시 어댑터 함수 제공 (기존 `ai_manager.get_ai_response()` 호환)

### 📦 requirements.txt
- `pydantic-settings>=2.0.0` 추가 (Pydantic BaseSettings 필수 의존성)

---

## 2026-07-05 — 시스템 모듈화 구조조정 Phase 1 (v1.2.1)

### 🚨 즉시 보안 조치
- **[CRITICAL]** `VERSION` 파일 관리자 우회키(`?access_key=admin777`) 평문 노출 제거 → v1.2.1로 버전 업
- **[FIXED]** 이중 진입점 충돌 해소: `main.py` → `server/webhook_app.py` 레거시 경로 제거, `app.py` 단일 진입점으로 통일
- **[FIXED]** `requirements.txt` 중복 패키지 제거 (gspread, google-auth, sqlalchemy, psycopg2-binary, pydantic 2회씩 선언 정리)

### 📁 deprecated/ 논리적 격리 (폐기 스크립트 아카이브)
| 카테고리 | 수량 |
|----------|------|
| diagnostics/ (check_*.py 등) | 185개 |
| hotfixes/ (fix_*.py) | 20개 |
| debug/ (debug_*.py, diag_*.py) | 12개 |
| deploy_scripts/ (deploy_v*.py 등) | 13개 |
| test_scripts/ (test_*.py) | 37개 |
| temp_logs/ (로그/결과 텍스트) | 81개 |
| **합계** | **349개** |

### 🎬 media_worker/ 숏폼 파이프라인 완전 격리 (핵심)
- `media_worker/` 독립 프로젝트 신설 (메인 앱과 물리적·논리적 분리)
- Celery + Redis 비동기 워커 구조 (`worker.py`) 작성
- OOM 방지 설정: `max_tasks_per_child=5`, `prefetch_multiplier=1`, 30/60분 타임아웃
- `media_worker/Dockerfile.worker`: GPU 서버 전용 독립 컨테이너
- `media_worker/requirements.txt`: 미디어 전용 의존성 분리 (torch 등 GPU 패키지 주석 처리)
- 이관 파일: `batch_svd_renderer.py`, `master_documentary_pipeline.py`, `*.json` 워크플로우, `generate_strawberry_video.py`, `local_gpu_worker.py`

### 🏗️ infra/ 인프라 설정 분리
- `infra/docker/docker-compose.yml` 신설: 멀티 컨테이너 정의 (앱 2G / 워커 8G 메모리 격리)
- `infra/nginx/`: nginx 설정 이관
- `infra/scripts/`: 보안 스크립트 이관

### 📝 .gitignore 강화
- 대용량 바이너리 추가 (`*.zip`, `*.exe`, `*.deb`, `*.apk`, `*.deb`)
- `deprecated/` 폴더 Git 추적 제외
- `media_worker/media_output/` 출력물 제외

---

## 2026-02-09 — Code Audit & Bug Fix Sprint


### webhook_app.py — 8 bugs fixed
- Added missing `_extract_value()` function definition for dangling code block
- Added missing `import openpyxl` for Excel export endpoint
- Fixed double request body consumption in `payment_webhook` (`await request.json()` -> `json.loads(payload)`)
- Fixed XSS vulnerability in 404 handler — added `html_escape()` on `request.url.path`
- Removed duplicate imports (`sms_manager`, `Form`, `UploadFile/File`)
- Removed unused code (`OrderRequest` model, `get_card_session`, `import random`)
- Consolidated all imports at top of file (`hmac`, `hashlib`, `json`, `logen`, `gsheet`)

### db_manager.py — 27 missing wrapper functions added
- Dashboard & Stats: `get_today_stats`
- Auto Reply: `update_store_auto_reply`
- Wallet: `charge_wallet`
- Products: `save_product`, `get_all_products`, `get_product_detail`, `decrease_product_inventory`
- Orders: `save_order`, `get_order_by_id`, `update_order_status`, `update_payment_method`, `update_order_tracking`
- Tax & Expenses: `get_tax_report_data`, `get_tax_stats`, `get_monthly_expenses`, `save_expense`
- Ledger: `get_integrated_ledger`, `lock_ledger`
- Customer CRM: `get_customer`, `get_customer_by_phone`, `save_customer`, `update_customer_field`, `increment_customer_order`

### db_sqlite.py — 9 new implementations + 1 table + 1 column
- New functions: `charge_wallet`, `decrease_product_inventory`, `get_tax_report_data`, `update_order_status`, `get_customer`, `get_customer_by_phone`, `save_customer`, `update_customer_field`, `increment_customer_order`
- New table: `customers` (CRM) with unique constraint on `(customer_id, store_id)`
- New column: `products.inventory` (default 100)

### sms_manager.py — 7 missing imports added
- `requests`, `time`, `datetime`, `uuid`, `hmac`, `hashlib`, `db_manager as db`

### server/logen_service.py — duplicate code removed & bugs fixed
- Removed ~90 lines of duplicated imports, constants, and functions
- Moved `LOGEN_API_URL` and `LOGEN_API_KEY` constants to top of file
- Fixed `db.update_tracking_number` -> `db.update_order_tracking` (3 call sites)
- Added missing return values to `process_refund`

### Summary
| Metric                    | Count |
|---------------------------|-------|
| Files modified            | 6     |
| Bugs fixed (webhook_app)  | 8     |
| Missing functions added   | 36    |
| Missing imports added     | 8     |
| Duplicate code removed    | ~90 lines |
| Security fixes            | 2 (XSS, double body read) |
| New DB tables             | 1 (customers) |
| New DB columns            | 1 (products.inventory) |
