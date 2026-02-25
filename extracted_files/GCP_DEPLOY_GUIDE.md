# 🚀 동네비서 - GCP 배포 자동화 가이드

> **대상**: 60대 개발자님의 미국 서버(GCP) 배포  
> **목표**: 배포 과정의 모든 에러 변수를 사전 체크하고 자동화  
> **버전**: v2.0.0  
> **최종 수정**: 2026-02-10

---

## 📋 목차
1. [배포 전 체크리스트](#배포-전-체크리스트)
2. [배포 에러 변수 사전 점검](#배포-에러-변수-사전-점검)
3. [배포 자동화 스크립트](#배포-자동화-스크립트)
4. [단계별 배포 가이드](#단계별-배포-가이드)
5. [문제 해결 가이드](#문제-해결-가이드)

---

## ✅ 배포 전 체크리스트

### 1단계: 로컬 환경 확인 (필수)
```bash
# Python 버전 확인 (3.9 이상이어야 함)
python --version

# 필수 패키지 설치 확인
pip install -r requirements.txt

# 로컬 서버 실행 테스트
uvicorn main:app --host 0.0.0.0 --port 8080

# 브라우저에서 확인
# http://127.0.0.1:8080/docs
```

**통과 조건**:
- [ ] Python 3.9 이상
- [ ] 모든 패키지 설치 성공
- [ ] `Application startup complete` 메시지 확인
- [ ] `/docs` 페이지 정상 로드

---

### 2단계: 코드 품질 검증
```bash
# 1. 문법 오류 확인
python -m py_compile server/webhook_app.py
python -m py_compile main.py
python -m py_compile db_manager.py

# 2. Import 오류 확인
python -c "import server.webhook_app"
python -c "import db_manager"
python -c "import sms_manager"

# 3. 환경 변수 확인
python -c "import toml; print(toml.load('secrets.toml'))"
```

**통과 조건**:
- [ ] 모든 Python 파일 컴파일 성공
- [ ] Import 에러 없음
- [ ] `secrets.toml` 파일 존재 및 유효

---

### 3단계: Docker 빌드 테스트
```bash
# Dockerfile 빌드 (로컬)
docker build -t dnbsir-local:latest .

# 컨테이너 실행 테스트
docker run -p 8080:8080 dnbsir-local:latest

# 브라우저에서 확인
# http://127.0.0.1:8080/docs
```

**통과 조건**:
- [ ] Docker 이미지 빌드 성공
- [ ] 컨테이너 실행 성공
- [ ] 8080 포트로 접속 가능

---

### 4단계: GCP 환경 변수 설정
```bash
# GCP 프로젝트 확인
gcloud config get-value project

# 서비스 계정 확인
gcloud iam service-accounts list

# Cloud Run 서비스 확인
gcloud run services list --region=us-central1
```

**통과 조건**:
- [ ] GCP 프로젝트 ID 확인
- [ ] 서비스 계정 존재 확인
- [ ] Cloud Run 리전 확인 (`us-central1`)

---

## 🚨 배포 에러 변수 사전 점검

### 에러 유형 1: Python 버전 불일치
**증상**: `SyntaxError: invalid syntax` 또는 타입 힌트 에러
```python
# 문제가 되는 코드
store_id: str | None = None  # Python 3.10+ 문법

# 해결 방법 (Python 3.9 호환)
from typing import Union, Optional
store_id: Optional[str] = None
```

**사전 점검**:
```bash
# Dockerfile의 Python 버전과 로컬 버전 일치 여부 확인
cat Dockerfile | grep "FROM python"
python --version
```

---

### 에러 유형 2: 포트 설정 오류
**증상**: `Connection refused` 또는 `Service Unavailable`

**체크 포인트**:
1. `main.py`의 포트: `8080` ✅
2. `Dockerfile`의 `EXPOSE`: `8080` ✅
3. Cloud Run 설정: `Container port = 8080` ✅

**검증 스크립트**:
```bash
#!/bin/bash
# check_port.sh

echo "Checking port configuration..."

# main.py 확인
PORT_MAIN=$(grep -oP 'port=\K\d+' main.py | head -1)
echo "main.py port: $PORT_MAIN"

# Dockerfile 확인
PORT_DOCKER=$(grep -oP 'EXPOSE \K\d+' Dockerfile)
echo "Dockerfile EXPOSE: $PORT_DOCKER"

if [ "$PORT_MAIN" != "8080" ] || [ "$PORT_DOCKER" != "8080" ]; then
    echo "❌ ERROR: Port mismatch detected!"
    exit 1
else
    echo "✅ Port configuration is correct (8080)"
fi
```

---

### 에러 유형 3: 필수 파일 누락
**증상**: `ModuleNotFoundError` 또는 `FileNotFoundError`

**필수 파일 목록**:
```
AI_Store/
├── main.py                    ✅ 진입점
├── requirements.txt           ✅ 의존성
├── Dockerfile                 ✅ 빌드 파일
├── server/
│   └── webhook_app.py         ✅ FastAPI 앱
├── templates/
│   ├── base.html              ✅ 기본 템플릿
│   └── *.html                 ✅ 모든 페이지
├── static/
│   └── css/style.css          ✅ 스타일
├── db_manager.py              ✅ DB 모듈
├── sms_manager.py             ✅ SMS 모듈
└── secrets.toml               ⚠️ (로컬용, 배포 시 환경변수로)
```

**검증 스크립트**:
```bash
#!/bin/bash
# check_files.sh

REQUIRED_FILES=(
    "main.py"
    "requirements.txt"
    "Dockerfile"
    "server/webhook_app.py"
    "templates/base.html"
    "static/css/style.css"
    "db_manager.py"
)

echo "Checking required files..."
MISSING=0

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Missing: $file"
        MISSING=$((MISSING + 1))
    else
        echo "✅ Found: $file"
    fi
done

if [ $MISSING -gt 0 ]; then
    echo "❌ ERROR: $MISSING file(s) missing!"
    exit 1
else
    echo "✅ All required files present"
fi
```

---

### 에러 유형 4: 환경 변수 누락
**증상**: `KeyError` 또는 `None` 값 에러

**Cloud Run에 설정해야 할 환경 변수**:
```bash
# 필수 환경 변수
TZ=Asia/Seoul                          # 한국 시간대
PORT=8080                              # 서버 포트
WEBHOOK_TOKEN=your_secret_token        # 웹훅 인증
ADMIN_ALERT_PHONE=010-2384-7447       # 관리자 전화번호

# 선택 환경 변수
ENABLE_WEBHOOK_TEST_NOTIFY=true
APP_BASE_URL=https://dnbsir.com
```

**GCP에서 환경 변수 설정**:
```bash
gcloud run deploy dnbsir \
  --image gcr.io/YOUR_PROJECT/dnbsir \
  --region us-central1 \
  --set-env-vars "TZ=Asia/Seoul,PORT=8080,WEBHOOK_TOKEN=secret123"
```

---

### 에러 유형 5: 데이터베이스 연결 오류
**증상**: `OperationalError` 또는 `Connection timeout`

**체크 포인트**:
1. **SQLite (로컬 테스트)**: `database.db` 파일 존재 확인
2. **PostgreSQL (프로덕션)**: Cloud SQL 연결 설정 확인

**Cloud SQL 연결 설정**:
```bash
# Cloud SQL Proxy 설정
gcloud run services update dnbsir \
  --region us-central1 \
  --add-cloudsql-instances YOUR_PROJECT:us-central1:dnbsir-db
```

**환경 변수 추가**:
```bash
DB_HOST=/cloudsql/YOUR_PROJECT:us-central1:dnbsir-db
DB_USER=postgres
DB_PASSWORD=your_secure_password
DB_NAME=dnbsir_db
```

---

### 에러 유형 6: 메모리 부족
**증상**: `MemoryError` 또는 컨테이너 재시작

**해결 방법**:
```bash
# Cloud Run 메모리 증가 (기본 512MB → 1GB)
gcloud run deploy dnbsir \
  --region us-central1 \
  --memory 1Gi \
  --cpu 1
```

---

### 에러 유형 7: 타임아웃
**증상**: `504 Gateway Timeout`

**해결 방법**:
```bash
# Cloud Run 타임아웃 증가 (기본 300초 → 900초)
gcloud run deploy dnbsir \
  --region us-central1 \
  --timeout 900
```

---

## 🤖 배포 자동화 스크립트

### 스크립트 1: 완전 자동 배포 (`deploy.sh`)
```bash
#!/bin/bash
# deploy.sh - 동네비서 자동 배포 스크립트

set -e  # 에러 발생 시 즉시 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 설정
PROJECT_ID="your-gcp-project-id"
SERVICE_NAME="dnbsir"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  동네비서 자동 배포 시작${NC}"
echo -e "${GREEN}========================================${NC}"

# 1단계: 사전 점검
echo -e "${YELLOW}[1/6] 사전 점검 중...${NC}"

# Python 버전 확인
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "Python 버전: $PYTHON_VERSION"

# 필수 파일 확인
if [ ! -f "main.py" ]; then
    echo -e "${RED}❌ main.py 파일을 찾을 수 없습니다!${NC}"
    exit 1
fi

if [ ! -f "Dockerfile" ]; then
    echo -e "${RED}❌ Dockerfile을 찾을 수 없습니다!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 사전 점검 완료${NC}"

# 2단계: 로컬 테스트
echo -e "${YELLOW}[2/6] 로컬 테스트 중...${NC}"

# 문법 오류 확인
python -m py_compile main.py server/webhook_app.py db_manager.py

echo -e "${GREEN}✅ 로컬 테스트 완료${NC}"

# 3단계: Docker 이미지 빌드
echo -e "${YELLOW}[3/6] Docker 이미지 빌드 중...${NC}"

# 기존 이미지 삭제 (선택 사항)
# docker rmi $IMAGE_NAME:latest || true

# 새 이미지 빌드
docker build -t $IMAGE_NAME:latest .

echo -e "${GREEN}✅ Docker 이미지 빌드 완료${NC}"

# 4단계: GCP에 이미지 푸시
echo -e "${YELLOW}[4/6] GCP Container Registry에 푸시 중...${NC}"

# GCP 인증 (처음 한 번만)
gcloud auth configure-docker

# 이미지 푸시
docker push $IMAGE_NAME:latest

echo -e "${GREEN}✅ 이미지 푸시 완료${NC}"

# 5단계: Cloud Run 배포
echo -e "${YELLOW}[5/6] Cloud Run에 배포 중...${NC}"

gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME:latest \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 900 \
  --set-env-vars "TZ=Asia/Seoul,PORT=8080" \
  --max-instances 10 \
  --min-instances 1

echo -e "${GREEN}✅ Cloud Run 배포 완료${NC}"

# 6단계: 배포 확인
echo -e "${YELLOW}[6/6] 배포 확인 중...${NC}"

# 서비스 URL 가져오기
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --region $REGION \
  --format 'value(status.url)')

echo -e "${GREEN}✅ 배포 성공!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  서비스 URL: ${SERVICE_URL}${NC}"
echo -e "${GREEN}  API 문서: ${SERVICE_URL}/docs${NC}"
echo -e "${GREEN}========================================${NC}"

# 헬스 체크
echo -e "${YELLOW}헬스 체크 수행 중...${NC}"
sleep 5
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" ${SERVICE_URL}/health || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ 서버가 정상적으로 작동하고 있습니다!${NC}"
else
    echo -e "${RED}⚠️ 헬스 체크 실패 (HTTP ${HTTP_CODE})${NC}"
    echo -e "${YELLOW}로그를 확인하세요: gcloud run services logs read $SERVICE_NAME --region $REGION${NC}"
fi
```

---

### 스크립트 2: 롤백 스크립트 (`rollback.sh`)
```bash
#!/bin/bash
# rollback.sh - 이전 버전으로 롤백

SERVICE_NAME="dnbsir"
REGION="us-central1"

echo "이전 배포 버전 목록:"
gcloud run revisions list --service $SERVICE_NAME --region $REGION

read -p "롤백할 Revision 이름을 입력하세요: " REVISION_NAME

gcloud run services update-traffic $SERVICE_NAME \
  --region $REGION \
  --to-revisions $REVISION_NAME=100

echo "✅ 롤백 완료: $REVISION_NAME"
```

---

### 스크립트 3: 로그 모니터링 (`logs.sh`)
```bash
#!/bin/bash
# logs.sh - 실시간 로그 모니터링

SERVICE_NAME="dnbsir"
REGION="us-central1"

echo "실시간 로그 스트리밍 중... (Ctrl+C로 종료)"
gcloud run services logs tail $SERVICE_NAME --region $REGION
```

---

## 📖 단계별 배포 가이드

### 방법 1: GitHub Actions 자동 배포 (추천)

**1단계**: `.github/workflows/deploy.yml` 파일 생성
```yaml
name: Deploy to Cloud Run

on:
  push:
    branches:
      - main

env:
  PROJECT_ID: your-gcp-project-id
  SERVICE_NAME: dnbsir
  REGION: us-central1

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Setup Cloud SDK
      uses: google-github-actions/setup-gcloud@v1
      with:
        service_account_key: ${{ secrets.GCP_SA_KEY }}
        project_id: ${{ env.PROJECT_ID }}
    
    - name: Configure Docker
      run: gcloud auth configure-docker
    
    - name: Build Docker image
      run: docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME:$GITHUB_SHA .
    
    - name: Push to GCR
      run: docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:$GITHUB_SHA
    
    - name: Deploy to Cloud Run
      run: |
        gcloud run deploy $SERVICE_NAME \
          --image gcr.io/$PROJECT_ID/$SERVICE_NAME:$GITHUB_SHA \
          --region $REGION \
          --platform managed \
          --allow-unauthenticated \
          --port 8080 \
          --memory 1Gi \
          --set-env-vars "TZ=Asia/Seoul,PORT=8080"
```

**2단계**: GitHub Secrets 설정
- `Settings` → `Secrets and variables` → `Actions`
- `GCP_SA_KEY`: GCP 서비스 계정 JSON 키 추가

**3단계**: 코드 푸시
```bash
git add .
git commit -m "Deploy: Version 1.0.0"
git push origin main
```

**자동 배포 완료!** 🎉

---

### 방법 2: 수동 배포 (한 줄 명령어)
```bash
# 프로젝트 루트에서 실행
chmod +x deploy.sh
./deploy.sh
```

---

## 🔧 문제 해결 가이드

### 문제 1: "Permission denied" 에러
**원인**: GCP 권한 부족

**해결**:
```bash
# 서비스 계정에 필요한 권한 부여
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/run.admin

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/storage.admin
```

---

### 문제 2: "Module not found" 에러
**원인**: `requirements.txt`에 패키지 누락

**해결**:
```bash
# 로컬에서 현재 설치된 모든 패키지 확인
pip freeze > requirements_full.txt

# 기존 requirements.txt와 비교
diff requirements.txt requirements_full.txt

# 누락된 패키지 추가
echo "missing-package==1.0.0" >> requirements.txt
```

---

### 문제 3: "Container failed to start"
**원인**: Dockerfile 오류 또는 코드 에러

**디버깅**:
```bash
# 로컬에서 Docker 컨테이너 로그 확인
docker run -p 8080:8080 dnbsir-local:latest

# Cloud Run 로그 확인
gcloud run services logs read dnbsir --region us-central1 --limit 50
```

---

### 문제 4: "502 Bad Gateway"
**원인**: 서버가 제때 시작하지 못함

**해결**:
```bash
# 시작 시간 증가
gcloud run deploy dnbsir \
  --region us-central1 \
  --timeout 900 \
  --cpu-throttling  # CPU 제한 해제
```

---

## 📊 배포 후 모니터링

### 헬스 체크 엔드포인트 추가
`server/webhook_app.py`에 추가:
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }
```

### 모니터링 대시보드
```bash
# GCP Console에서 확인
# Cloud Run → dnbsir → Metrics

# 주요 지표:
# - Request count (요청 수)
# - Request latency (응답 속도)
# - Error rate (에러 비율)
# - Container instance count (인스턴스 수)
```

---

## 🎓 추가 자료

- **Cloud Run 공식 문서**: https://cloud.google.com/run/docs
- **Dockerfile 최적화**: https://docs.docker.com/develop/dev-best-practices/
- **GitHub Actions**: https://docs.github.com/en/actions

---

**마지막 업데이트**: 2026-02-10  
**작성자**: 동네비서 개발팀  
**문의**: admin@dnbsir.com
