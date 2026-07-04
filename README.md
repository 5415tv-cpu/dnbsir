# 동네비서 (Dongnebiseo) 🏘️ AI 로컬 비즈니스 어시스턴트

> **운영 주체**: 탄탄제작소 (Tantan Fabrication)  
> **서비스 URL**: [api.dnbsir.com](https://api.dnbsir.com)  
> **타깃**: 시니어·농가·소상공인 AI 키오스크 서비스  
> **아키텍처 버전**: v1.4.0 (2026-07-05)

---

## 🏗️ 시스템 구조 (한눈에)

```
AI_Store/
│
├── dongnebiseo_app/      ← [동네비서 앱] 설정·서비스 레이어
│   ├── config/settings.py   # Pydantic 설정 분리 (탄탄/동네비서)
│   └── services/
│       ├── ai_service.py    # Gemini AI 클라이언트
│       └── rag_service.py   # RAG + 3단계 Fallback + 환각방지
│
├── routers/              ← [동네비서 앱] API 라우터 (21개)
├── templates/            ← [동네비서 앱] 키오스크 UI (뉴브루탈리즘)
├── app.py                ← [동네비서 앱] FastAPI 메인 진입점
│
├── tantan_infra/         ← [탄탄제작소] 웹사이트 (Flask)
├── media_worker/         ← [탄탄제작소] 숏폼 영상 워커 (Celery+Redis)
├── infra/                ← [탄탄제작소] 인프라 설정
│   ├── docker/docker-compose.yml   # 멀티 컨테이너 정의
│   ├── nginx/                       # 리버스 프록시 설정
│   └── scripts/                     # 보안 스크립트
│
└── deprecated/           ← [아카이브] 349개 — 30일 후 삭제 예정
```

---

## 🚀 빠른 시작

```bash
# 1. 환경 설정
cp .env.example .env
# .env에서 GOOGLE_API_KEY, TANTAN_DB_PASSWORD 등 입력

# 2. 전체 서비스 실행
cd infra/docker
docker compose up -d

# 3. 상태 확인
docker compose ps
docker compose logs -f dongnebiseo-app

# 4. 숏폼 워커 포함 실행 (GPU 서버에서만)
docker compose --profile with-worker up -d
```

---

## 📐 3대 코어 원칙

| 원칙 | 구현 방식 |
|------|---------|
| **정확성 최우선** | RAG 그라운딩 — DB 데이터 범위 밖 LLM 추측 원천 차단 |
| **키오스크 UI** | 뉴브루탈리즘 고정형 UI (3px 검정 테두리, #E0E0E0 배경) |
| **인프라 안정성** | 메모리 격리 (앱 2G / 워커 8G), asyncio 3단계 Fallback |

---

## 🔧 환경변수 영역 구분

| Prefix | 영역 | 예시 |
|--------|------|------|
| `TANTAN_*` | 탄탄제작소 인프라 | `TANTAN_DATABASE_URL`, `TANTAN_REDIS_URL` |
| 레거시 키명 | 동네비서 앱 | `GOOGLE_API_KEY`, `SOLAPI_API_KEY` |
| `MEDIA_WORKER_*` | 숏폼 워커 | `MEDIA_WORKER_REDIS_URL` |

---

## 📚 상세 문서

- [media_worker/README.md](media_worker/README.md) — 숏폼 워커 운영 가이드
- [CHANGELOG.md](CHANGELOG.md) — 버전 이력
- [CLAUDE.md](CLAUDE.md) — 개발 코드 철학·디자인 가이드 (필수 참조)
