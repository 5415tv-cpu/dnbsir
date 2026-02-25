# 📊 동네비서 프로젝트 - 정밀 구조 분석 보고서

> **분석 대상**: AI_Store (동네비서 앱)  
> **분석일**: 2026-02-10  
> **개발자**: 60대 사장님  
> **목적**: 프로젝트 전체 구조 파악 및 개선 방향 제시

---

## 📋 목차
1. [프로젝트 개요](#프로젝트-개요)
2. [기술 스택 분석](#기술-스택-분석)
3. [디렉토리 구조](#디렉토리-구조)
4. [핵심 모듈 분석](#핵심-모듈-분석)
5. [데이터베이스 구조](#데이터베이스-구조)
6. [API 엔드포인트 목록](#api-엔드포인트-목록)
7. [강점과 개선점](#강점과-개선점)
8. [다음 단계 제안](#다음-단계-제안)

---

## 🎯 프로젝트 개요

### 기본 정보
- **프로젝트명**: 동네비서 (AI_Store)
- **목적**: 농민과 택배 기사를 위한 AI 통합 관리 솔루션
- **주요 기능**:
  - 📞 부재중 전화 자동 응답 (AI 주문 접수)
  - 📦 로젠택배 자동 접수
  - 💰 세무/장부 자동 관리
  - 🛒 온라인 마켓 운영
  - 💳 간편 결제 (Toss Payments 연동)

### 배포 환경
- **현재 배포**: Google Cloud Run (미국 서버 `us-central1`)
- **도메인**: https://api.dnbsir.com
- **데이터베이스**: SQLite (로컬) → PostgreSQL (마이그레이션 예정)

---

## 🛠️ 기술 스택 분석

### 백엔드
```
Python 3.9+
├── FastAPI (v0.110.0+)        # 웹 프레임워크
├── Uvicorn (v0.27.0+)         # ASGI 서버
├── Jinja2 (v3.1.0+)           # 템플릿 엔진
├── SQLAlchemy (v2.0.0+)       # ORM
└── Pydantic                   # 데이터 검증
```

### 프론트엔드
```
HTML5 + CSS3 (인라인 스타일)
├── 뉴브루탈리즘 디자인 (Neo-Brutalism)
├── 모바일 퍼스트 (Mobile First)
└── PWA 지원 (manifest.json)
```

### 외부 서비스 연동
```
AI/LLM
└── Google Gemini API (v0.3.0+)

결제
└── Toss Payments

물류
└── 로젠택배 API

통신
├── SMS (클라우드 SMS)
└── Webhook (부재중 전화)

데이터베이스
├── Google Sheets (gspread v5.12.0+)
└── PostgreSQL (psycopg2-binary v2.9.9+)
```

### 인프라
```
Docker
└── Dockerfile (Python 3.9-slim 기반)

Google Cloud Platform
├── Cloud Run (서버리스)
├── Cloud SQL (PostgreSQL)
└── Secret Manager (보안 키 관리)
```

---

## 📁 디렉토리 구조

### 전체 구조 (시각화)
```
AI_Store/
│
├── 📄 main.py                    # 🔑 앱 진입점 (Uvicorn 실행)
├── 📄 Dockerfile                 # 🐳 Docker 빌드 파일
├── 📄 requirements.txt           # 📦 Python 의존성
├── 📄 README.md                  # 📖 프로젝트 설명
├── 📄 CHANGELOG.md               # 📝 변경 이력
├── 📄 DEPLOY_GUIDE.md            # 🚀 배포 가이드
├── 📄 VERSION                    # 🏷️ 버전 정보
├── 📄 manifest.json              # 📱 PWA 설정
├── 📄 secrets.toml               # 🔐 환경 변수 (로컬용)
├── 📄 service_account.json       # 🔑 GCP 서비스 계정
│
├── 📂 server/                    # 🌐 백엔드 서버
│   ├── webhook_app.py            # 🔑 FastAPI 메인 앱 (500+ 줄)
│   ├── logen_service.py          # 📦 로젠택배 서비스
│   └── google_sheet_sync.py      # 📊 구글 시트 동기화
│
├── 📂 templates/                 # 🎨 HTML 템플릿 (15개)
│   ├── base.html                 # 🏗️ 기본 레이아웃
│   ├── index.html                # 🏠 메인 페이지 (시민 포털)
│   ├── login.html                # 🔐 관리자 로그인
│   ├── dashboard.html            # 📊 대시보드
│   ├── market.html               # 🛒 온라인 마켓
│   ├── tax_dashboard.html        # 💰 세무 센터
│   ├── expenses.html             # 💳 비용 기장
│   ├── card_register.html        # 💳 카드 등록
│   ├── courier_form.html         # 📦 택배 접수 양식
│   ├── farm_order_dashboard.html # 🚜 농가 주문 관리
│   ├── citizen_dashboard.html    # 👥 시민 대시보드
│   ├── calculator.html           # 🧮 계산기
│   ├── auto_reply_settings.html  # 🤖 자동 응답 설정
│   ├── product_register.html     # 📦 상품 등록
│   └── agreement.html            # 📜 이용 약관
│
├── 📂 static/                    # 🎨 정적 파일
│   ├── css/
│   │   └── style.css             # 🎨 공통 스타일 (뉴브루탈리즘)
│   ├── js/
│   │   └── app.js                # ⚙️ JavaScript
│   └── images/                   # 🖼️ 이미지
│
├── 📂 modules/                   # 🧩 모듈화된 기능
│   ├── admin/                    # 👤 관리자 기능
│   ├── customer/                 # 👥 고객 관리
│   ├── merchant/                 # 🏪 가맹점 관리
│   ├── logistics/                # 📦 물류 관리
│   └── common/                   # 🔧 공통 유틸리티
│
├── 📂 docs/                      # 📚 문서
│   ├── trademark_patent_draft.md
│   └── trademark_patent_draft_print.md
│
├── 📂 serverless/                # ☁️ 서버리스 함수
│   └── gcp_function.py           # GCP Cloud Function
│
├── 📂 images/                    # 🖼️ 앱 이미지
│   ├── kakao_manual.png          # 카카오 매뉴얼
│   └── mobile_access_qr.png      # 모바일 접속 QR
│
├── 📄 db_manager.py              # 🗄️ 데이터베이스 통합 관리자
├── 📄 db_sqlite.py               # 🗄️ SQLite 백엔드
├── 📄 db_cloudsql.py             # ☁️ Cloud SQL 백엔드
├── 📄 db_backend.py              # 🔌 DB 백엔드 인터페이스
├── 📄 customer_memory.py         # 🧠 고객 메모리 관리
├── 📄 sms_manager.py             # 📱 SMS 발송 관리
├── 📄 ai_manager.py              # 🤖 AI 응답 생성
├── 📄 ocr_manager.py             # 🔍 OCR (광학 문자 인식)
├── 📄 logen_delivery.py          # 📦 로젠택배 연동
│
├── 📄 config.py                  # ⚙️ 설정 파일
├── 📄 admin.py                   # 👤 관리자 기능
├── 📄 app.py                     # (레거시?)
│
├── 📂 uploads/                   # 📤 업로드 파일 저장소
│
└── 📄 database.db                # 🗄️ SQLite 데이터베이스 (120KB)
```

---

## 🔍 핵심 모듈 분석

### 1. **server/webhook_app.py** (725줄)
**역할**: FastAPI 메인 애플리케이션

**주요 기능**:
```python
# PWA 페이지
GET  /                         # 메인 페이지 (시민 포털)
GET  /agreement                # 이용 약관
GET  /admin                    # 관리자 로그인
POST /api/login                # 로그인 처리 (자동 회원가입 포함)
GET  /admin/dashboard          # 관리자 대시보드
GET  /logout                   # 로그아웃

# 부재중 전화 Webhook
POST /webhook/missed-call      # 부재중 전화 수신
POST /api/webhook/call-detect  # NHN 전화 감지

# 배송 관리
GET  /courier                  # 택배 접수 양식
POST /api/courier/logen        # 로젠택배 접수
GET  /admin/delivery           # 배송 대시보드
POST /api/delivery/sign        # 전자 서명

# 결제
POST /v1/payments/webhook      # 결제 웹훅 (Toss Payments)
GET  /admin/cards/register     # 카드 등록 페이지
POST /api/admin/cards/register # 카드 등록 API

# 세무/장부
GET  /admin/tax                # 세무 센터
GET  /api/admin/tax/stats      # 세무 통계
GET  /admin/expenses           # 비용 기장
GET  /api/admin/expenses       # 비용 목록
GET  /api/admin/ledger/export  # 장부 내보내기 (ZIP)

# 농가 주문
GET  /admin/farm/orders        # 농가 주문 관리
POST /api/order/new            # 신규 주문 접수

# 마켓
GET  /market                   # 온라인 마켓
POST /api/product/register     # 상품 등록

# 시민 포털
GET  /citizen/dashboard        # 시민 대시보드
GET  /calculator               # 계산기
```

**보안 기능**:
- JWT 세션 쿠키 (`admin_session`)
- Webhook 토큰 검증 (`X-Webhook-Token`)
- HMAC 서명 검증 (결제 웹훅)
- HTML 이스케이프 (XSS 방지)

**에러 핸들링**:
- 커스텀 404 페이지
- 예외 핸들러 (`StarletteHTTPException`)

---

### 2. **db_manager.py** (350줄 추정)
**역할**: 데이터베이스 통합 관리

**주요 함수**:
```python
# 가맹점 관리
get_store(store_id)               # 가맹점 조회
save_store(store_id, store_data)  # 가맹점 저장

# 주문 관리
save_order(...)                   # 주문 저장
get_today_stats(store_id)         # 오늘의 통계

# 상품 관리
get_product_detail(product_id)    # 상품 조회
decrease_product_inventory(...)   # 재고 감소 (경쟁 조건 처리)

# 세무 관리
get_tax_stats(store_id)           # 세무 통계
save_expense(...)                 # 비용 저장
get_monthly_expenses(store_id)    # 월별 비용
get_integrated_ledger(store_id)   # 통합 장부
lock_ledger(store_id, date)       # 장부 잠금

# SMS 로그
log_sms(store_id, ...)            # SMS 로그 저장

# 결제
update_order_status(...)          # 주문 상태 업데이트
update_payment_method(...)        # 결제 수단 저장
```

**특징**:
- 백엔드 추상화 (`db_backend.py`)
- SQLite ↔ PostgreSQL 전환 가능
- 트랜잭션 처리
- 경쟁 조건 처리 (Race Condition)

---

### 3. **sms_manager.py** (300줄 추정)
**역할**: SMS 발송 및 부재중 전화 처리

**주요 함수**:
```python
send_cloud_sms(phone, message, store_id)  # SMS 발송
process_missed_call_webhook(payload)      # 부재중 전화 처리
```

**처리 흐름**:
1. 부재중 전화 수신
2. 가맹점 정보 조회 (`db_manager`)
3. AI 응답 생성 (`ai_manager`)
4. 고객에게 SMS 발송
5. 로그 저장

---

### 4. **ai_manager.py** (100줄 추정)
**역할**: Google Gemini API를 사용한 AI 응답 생성

**주요 함수**:
```python
generate_ai_response(customer_message, store_info)
```

**기능**:
- 고객 메시지 분석
- 맥락 기반 응답 생성
- 주문 링크 포함

---

### 5. **logen_delivery.py** (250줄 추정)
**역할**: 로젠택배 API 연동

**주요 함수**:
```python
send_to_logen(order_id)      # 택배 접수
process_refund(order_id)     # 취소/환불 처리
```

**처리 흐름**:
1. 주문 정보 조회
2. 로젠택배 API 호출
3. 송장 번호 저장
4. 고객에게 SMS 발송

---

## 🗄️ 데이터베이스 구조

### SQLite 스키마 (추정)
```sql
-- 가맹점 정보
CREATE TABLE stores (
    store_id TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    name TEXT,
    owner_name TEXT,
    phone TEXT,
    points INTEGER DEFAULT 0,
    membership TEXT DEFAULT 'free',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 주문
CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    store_id TEXT,
    product_id TEXT,
    product_name TEXT,
    price INTEGER,
    quantity INTEGER,
    customer_name TEXT,
    customer_phone TEXT,
    customer_address TEXT,
    status TEXT DEFAULT 'PENDING',
    payment_method TEXT,
    tracking_number TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(store_id)
);

-- 상품
CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    store_id TEXT,
    name TEXT,
    price INTEGER,
    inventory INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(store_id)
);

-- 비용
CREATE TABLE expenses (
    expense_id TEXT PRIMARY KEY,
    store_id TEXT,
    card_name TEXT,
    category TEXT,
    amount INTEGER,
    expense_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(store_id)
);

-- SMS 로그
CREATE TABLE sms_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id TEXT,
    phone TEXT,
    message_type TEXT,
    trigger TEXT,
    status TEXT,
    message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 장부 잠금
CREATE TABLE ledger_locks (
    lock_id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id TEXT,
    lock_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(store_id)
);
```

---

## 🌐 API 엔드포인트 목록

### Public (인증 불필요)
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/` | 메인 페이지 |
| GET | `/agreement` | 이용 약관 |
| GET | `/admin` | 로그인 페이지 |
| POST | `/api/login` | 로그인/회원가입 |
| POST | `/webhook/missed-call` | 부재중 전화 웹훅 |
| POST | `/api/webhook/call-detect` | 전화 감지 |
| POST | `/v1/payments/webhook` | 결제 웹훅 |

### Protected (세션 쿠키 필요)
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/admin/dashboard` | 대시보드 |
| GET | `/logout` | 로그아웃 |
| GET | `/courier` | 택배 접수 |
| POST | `/api/courier/logen` | 로젠택배 접수 |
| GET | `/admin/delivery` | 배송 관리 |
| POST | `/api/delivery/sign` | 전자 서명 |
| GET | `/admin/tax` | 세무 센터 |
| GET | `/api/admin/tax/stats` | 세무 통계 |
| GET | `/admin/expenses` | 비용 기장 |
| GET | `/api/admin/expenses` | 비용 목록 |
| GET | `/api/admin/ledger/export` | 장부 내보내기 |
| GET | `/admin/farm/orders` | 농가 주문 |
| POST | `/api/order/new` | 신규 주문 |
| GET | `/market` | 온라인 마켓 |
| POST | `/api/product/register` | 상품 등록 |
| GET | `/admin/cards/register` | 카드 등록 |
| POST | `/api/admin/cards/register` | 카드 등록 처리 |

---

## ✅ 강점과 개선점

### 강점
1. ✅ **명확한 구조**: 모듈화된 코드 구조
2. ✅ **PWA 지원**: 모바일 앱처럼 사용 가능
3. ✅ **자동화**: 부재중 전화 → AI 응답 → SMS 자동 발송
4. ✅ **통합 관리**: 주문/배송/세무를 한 곳에서 관리
5. ✅ **일관된 디자인**: 뉴브루탈리즘 스타일 유지
6. ✅ **보안**: HMAC 서명, 토큰 검증 등
7. ✅ **확장성**: 백엔드 추상화로 DB 전환 용이

### 개선점
1. ⚠️ **SQLite → PostgreSQL 마이그레이션**: 프로덕션 환경에 필수
2. ⚠️ **테스트 코드 부족**: 단위 테스트 추가 필요
3. ⚠️ **에러 로깅**: 체계적인 로깅 시스템 필요 (Sentry, CloudWatch 등)
4. ⚠️ **API 문서 부족**: `/docs`는 있지만 한글 설명 추가 필요
5. ⚠️ **환경 변수 관리**: `secrets.toml` → GCP Secret Manager로 이전
6. ⚠️ **캐싱**: Redis 등 캐싱 레이어 추가 (성능 향상)
7. ⚠️ **모니터링**: APM 도구 연동 (New Relic, Datadog 등)

---

## 🚀 다음 단계 제안

### 단기 (1-2주)
1. **CLAUDE.md 적용**: Cursor에 프로젝트 규칙 학습시키기
2. **배포 자동화**: GitHub Actions 또는 `deploy.sh` 스크립트 사용
3. **PostgreSQL 마이그레이션**: `migrate_sqlite_to_postgres.py` 실행
4. **환경 변수 이전**: `secrets.toml` → GCP Secret Manager

### 중기 (1-2개월)
1. **API 문서 개선**: Swagger UI 한글화
2. **테스트 코드 작성**: Pytest로 핵심 기능 테스트
3. **에러 로깅**: Sentry 연동
4. **모니터링**: GCP Cloud Monitoring 대시보드 구축

### 장기 (3-6개월)
1. **성능 최적화**: Redis 캐싱 추가
2. **기능 확장**: 카카오톡 알림, 네이버페이 연동
3. **관리자 앱**: Flutter/React Native로 모바일 앱 개발
4. **AI 고도화**: 맞춤형 추천, 재고 예측 등

---

## 📊 프로젝트 통계

### 코드 규모
- **총 Python 파일**: 20개
- **총 HTML 템플릿**: 15개
- **총 라인 수**: 약 3,000줄 (추정)

### 외부 의존성
- **Python 패키지**: 15개
- **외부 API**: 5개 (Google Gemini, Toss Payments, 로젠택배, SMS, Google Sheets)

### 데이터베이스
- **현재 크기**: 120KB (SQLite)
- **예상 테이블 수**: 6개

---

## 🎓 학습 자료

### 추천 문서
1. **FastAPI 공식 가이드**: https://fastapi.tiangolo.com
2. **Google Cloud Run**: https://cloud.google.com/run/docs
3. **뉴브루탈리즘 디자인**: https://brutalistwebsites.com

### 프로젝트 내부 문서
1. `README.md`: 프로젝트 소개
2. `DEPLOY_GUIDE.md`: 배포 가이드
3. `CHANGELOG.md`: 변경 이력

---

**분석 완료일**: 2026-02-10  
**분석자**: Claude (Anthropic AI)  
**다음 업데이트**: 코드 리팩토링 후
