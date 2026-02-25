#!/bin/bash
# deploy.sh - 동네비서 자동 배포 스크립트

set -e  # 에러 발생 시 즉시 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 설정 (service_account.json에서 추출한 프로젝트 ID)
PROJECT_ID="gen-lang-client-0456120803"
SERVICE_NAME="dnbsir-api"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  동네비서 자동 배포 시작 (서비스: $SERVICE_NAME)${NC}"
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

# 문법 오류 확인 (파일 존재 여부 확인 후 실행)
FILES_TO_CHECK="main.py db_manager.py"
if [ -f "server/webhook_app.py" ]; then
    FILES_TO_CHECK="$FILES_TO_CHECK server/webhook_app.py"
fi

python -m py_compile $FILES_TO_CHECK

echo -e "${GREEN}✅ 로컬 테스트 완료${NC}"

# 3단계: Docker 이미지 빌드
echo -e "${YELLOW}[3/6] Docker 이미지 빌드 중...${NC}"

# 새 이미지 빌드
docker build -t $IMAGE_NAME:latest .

echo -e "${GREEN}✅ Docker 이미지 빌드 완료${NC}"

# 4단계: GCP에 이미지 푸시
echo -e "${YELLOW}[4/6] GCP Container Registry에 푸시 중...${NC}"

# GCP 인증 (처음 한 번만)
# gcloud auth configure-docker

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
  --min-instances 1 \
  --quiet

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
