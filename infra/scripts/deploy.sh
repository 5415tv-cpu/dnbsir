#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# 동네비서 v1.4.0 — 무중단 배포 스크립트 (Zero-downtime Deploy)
# 실행 위치: 라이브 서버 (api.dnbsir.com) 직접 실행
#
# [사전 요구사항]
#   1. 서버에 Docker + Docker Compose v2 설치
#   2. /opt/dnbsir/ 에 Git 저장소 클론
#   3. /opt/dnbsir/.env 파일 존재 (운영 환경변수)
#   4. Nginx 실행 중
#
# [실행 방법]
#   chmod +x deploy.sh
#   ./deploy.sh
#   ./deploy.sh --rollback   # 이전 버전으로 롤백
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── 색상 출력 ─────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ── 설정 ──────────────────────────────────────────────────────
DEPLOY_DIR="/opt/dnbsir"
COMPOSE_FILE="$DEPLOY_DIR/infra/docker/docker-compose.yml"
APP_SERVICE="dongnebiseo-app"
BACKUP_TAG="backup-$(date +%Y%m%d-%H%M%S)"
HEALTH_URL="http://localhost:8080/health"
HEALTH_TIMEOUT=60    # 헬스체크 최대 대기 시간(초)
ROLLBACK_FLAG="${1:-}"

# ── 롤백 모드 ─────────────────────────────────────────────────
if [[ "$ROLLBACK_FLAG" == "--rollback" ]]; then
    log_warn "롤백 모드 시작..."
    LAST_BACKUP=$(docker images --format "{{.Tag}}" dnbsir-app | grep "backup-" | sort -r | head -1)
    if [[ -z "$LAST_BACKUP" ]]; then
        log_error "롤백 가능한 백업 이미지가 없습니다."
        exit 1
    fi
    log_info "롤백 대상: dnbsir-app:$LAST_BACKUP"
    docker tag "dnbsir-app:$LAST_BACKUP" "dnbsir-app:latest"
    cd "$DEPLOY_DIR"
    docker compose -f "$COMPOSE_FILE" up -d --no-deps "$APP_SERVICE"
    log_ok "롤백 완료: $LAST_BACKUP"
    exit 0
fi

# ═══════════════════════════════════════════════════════════════
# STEP 1: 사전 점검
# ═══════════════════════════════════════════════════════════════
log_info "══════════════════════════════════════════"
log_info " 동네비서 v1.4.0 무중단 배포 시작"
log_info " $(date '+%Y-%m-%d %H:%M:%S KST')"
log_info "══════════════════════════════════════════"

echo ""
log_info "[1/7] 사전 환경 점검..."

# .env 파일 존재 확인
if [[ ! -f "$DEPLOY_DIR/.env" ]]; then
    log_error ".env 파일이 없습니다: $DEPLOY_DIR/.env"
    log_error "cp $DEPLOY_DIR/.env.example $DEPLOY_DIR/.env 후 값을 채워주세요."
    exit 1
fi
log_ok ".env 파일 확인"

# 필수 환경변수 검증
source "$DEPLOY_DIR/.env"

# ── 1단계: 절대 필수 변수 (누락 시 즉시 중단) ────────────────
HARD_REQUIRED_VARS=("GOOGLE_API_KEY" "TANTAN_DB_PASSWORD")
for var in "${HARD_REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        log_error "필수 환경변수 미설정: $var"
        exit 1
    fi
done
log_ok "기본 환경변수 확인 (${#HARD_REQUIRED_VARS[@]}개)"

# ── 2단계: 콜백 보안 토큰 전용 검증 (치명적 에러 방지) ───────
# WEBHOOK_SECRET_TOKEN이 없으면 배포 후 전화망/카카오 채널 콜백이
# 전면 차단됩니다. 서비스 운영에 치명적이므로 별도 강제 검증합니다.
if [[ -z "${WEBHOOK_SECRET_TOKEN:-}" ]]; then
    echo ""
    log_error "══════════════════════════════════════════════════"
    log_error " [치명적 차단] WEBHOOK_SECRET_TOKEN 미설정!"
    log_error "══════════════════════════════════════════════════"
    log_error " 이 토큰이 없으면 배포 완료 후 즉시:"
    log_error "  - 전화망(NHN) 부재중 콜백 → 전면 차단"
    log_error "  - 카카오 채널 트리거     → 전면 차단"
    log_error "  서버가 모든 외부 신호를 해킹 시도로 간주합니다."
    log_error ""
    log_error " 해결 방법:"
    log_error "  1. 기존 운영 서버의 환경변수 확인:"
    log_error "     docker exec dnbsir-app env | grep WEBHOOK"
    log_error "  2. .env 파일에 추가:"
    log_error "     echo 'WEBHOOK_SECRET_TOKEN=your_token' >> $DEPLOY_DIR/.env"
    log_error "  3. 배포 재시도."
    log_error "══════════════════════════════════════════════════"
    exit 1
fi
log_ok "[보안] WEBHOOK_SECRET_TOKEN 확인 — 콜백 시스템 무결성 보장"

# Docker 상태 확인
if ! docker info &>/dev/null; then
    log_error "Docker가 실행 중이지 않습니다."
    exit 1
fi
log_ok "Docker 상태 정상"

# Nginx 상태 확인
if ! systemctl is-active --quiet nginx; then
    log_warn "Nginx가 실행 중이 아닙니다. 계속 진행합니다."
else
    log_ok "Nginx 실행 중"
fi

# ═══════════════════════════════════════════════════════════════
# STEP 2: 코드 동기화
# ═══════════════════════════════════════════════════════════════
echo ""
log_info "[2/7] Git 코드 동기화..."

cd "$DEPLOY_DIR"
CURRENT_BRANCH=$(git branch --show-current)
CURRENT_COMMIT=$(git rev-parse --short HEAD)

log_info "현재 브랜치: $CURRENT_BRANCH ($CURRENT_COMMIT)"
git fetch origin
git pull origin "$CURRENT_BRANCH"

NEW_COMMIT=$(git rev-parse --short HEAD)
log_ok "코드 동기화 완료: $CURRENT_COMMIT → $NEW_COMMIT"

# ═══════════════════════════════════════════════════════════════
# STEP 3: 현재 이미지 백업
# ═══════════════════════════════════════════════════════════════
echo ""
log_info "[3/7] 현재 이미지 백업..."

if docker image inspect "dnbsir-app:latest" &>/dev/null; then
    docker tag "dnbsir-app:latest" "dnbsir-app:$BACKUP_TAG"
    log_ok "백업 태그 생성: dnbsir-app:$BACKUP_TAG"
else
    log_warn "기존 이미지 없음 — 초기 배포로 진행"
fi

# ═══════════════════════════════════════════════════════════════
# STEP 4: 새 이미지 빌드
# ═══════════════════════════════════════════════════════════════
echo ""
log_info "[4/7] 새 이미지 빌드 중... (캐시 활용)"

docker compose -f "$COMPOSE_FILE" build "$APP_SERVICE" 2>&1 | tail -5
log_ok "이미지 빌드 완료"

# ═══════════════════════════════════════════════════════════════
# STEP 5: 블루-그린 무중단 교체
# ═══════════════════════════════════════════════════════════════
echo ""
log_info "[5/7] 블루-그린 무중단 교체..."

# 현재 컨테이너 수 확인
CURRENT_COUNT=$(docker compose -f "$COMPOSE_FILE" ps --status running "$APP_SERVICE" 2>/dev/null | grep -c "$APP_SERVICE" || echo "0")
log_info "현재 실행 중인 앱 컨테이너: ${CURRENT_COUNT}개"

# 새 컨테이너 2개로 스케일 업 (트래픽 유지)
log_info "컨테이너 2개로 스케일 업..."
docker compose -f "$COMPOSE_FILE" up -d --no-deps --scale "$APP_SERVICE=2" "$APP_SERVICE"

# 새 컨테이너 헬스체크 대기
log_info "새 컨테이너 헬스체크 대기 (최대 ${HEALTH_TIMEOUT}초)..."
ELAPSED=0
while [[ $ELAPSED -lt $HEALTH_TIMEOUT ]]; do
    HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" "$HEALTH_URL" 2>/dev/null || echo "000")
    if [[ "$HTTP_CODE" == "200" ]]; then
        log_ok "헬스체크 통과 (${ELAPSED}초 소요): HTTP $HTTP_CODE"
        break
    fi
    sleep 3
    ELAPSED=$((ELAPSED + 3))
    echo -n "."
done
echo ""

if [[ "$HTTP_CODE" != "200" ]]; then
    log_error "헬스체크 실패 (${HEALTH_TIMEOUT}초 초과) — 자동 롤백 실행"
    docker tag "dnbsir-app:$BACKUP_TAG" "dnbsir-app:latest" 2>/dev/null || true
    docker compose -f "$COMPOSE_FILE" up -d --no-deps --scale "$APP_SERVICE=1" "$APP_SERVICE"
    log_error "롤백 완료. 배포 실패 원인을 확인해 주세요."
    exit 1
fi

# 구 컨테이너 제거 (1개로 스케일 다운)
log_info "구 컨테이너 제거 (스케일 다운)..."
docker compose -f "$COMPOSE_FILE" up -d --no-deps --scale "$APP_SERVICE=1" "$APP_SERVICE"
log_ok "무중단 교체 완료"

# ═══════════════════════════════════════════════════════════════
# STEP 6: 의존 서비스 상태 확인
# ═══════════════════════════════════════════════════════════════
echo ""
log_info "[6/7] 의존 서비스 상태 확인..."

# Redis 핑 테스트
REDIS_PING=$(docker compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping 2>/dev/null || echo "FAIL")
if [[ "$REDIS_PING" == "PONG" ]]; then
    log_ok "Redis: 정상 (PONG)"
else
    log_warn "Redis: 응답 없음 — 확인 필요"
fi

# DB 연결 테스트
DB_OK=$(docker compose -f "$COMPOSE_FILE" exec -T db pg_isready -U "${TANTAN_DB_USER:-dnbsir}" 2>/dev/null || echo "FAIL")
if echo "$DB_OK" | grep -q "accepting"; then
    log_ok "PostgreSQL: 정상"
else
    log_warn "PostgreSQL: 확인 필요"
fi

# ═══════════════════════════════════════════════════════════════
# STEP 7: 배포 완료 요약
# ═══════════════════════════════════════════════════════════════
echo ""
log_info "[7/7] 스모크 테스트..."

ENDPOINTS=(
    "http://localhost:8080/health"
    "http://localhost:8080/admin/login"
    "http://localhost:8080/citizen"
)
for ep in "${ENDPOINTS[@]}"; do
    CODE=$(curl -sf -o /dev/null -w "%{http_code}" "$ep" 2>/dev/null || echo "ERR")
    if [[ "$CODE" =~ ^(200|301|302|307)$ ]]; then
        log_ok "$ep → $CODE"
    else
        log_warn "$ep → $CODE (확인 필요)"
    fi
done

# 오래된 백업 이미지 정리 (5개 초과분 삭제)
log_info "오래된 백업 이미지 정리..."
docker images "dnbsir-app" --format "{{.Tag}}" | grep "backup-" | sort -r | tail -n +6 | \
    xargs -r -I{} docker rmi "dnbsir-app:{}" 2>/dev/null || true

echo ""
log_info "══════════════════════════════════════════"
log_ok " 배포 완료! v1.4.0 (커밋: $NEW_COMMIT)"
log_info " 백업 태그: dnbsir-app:$BACKUP_TAG"
log_info " 롤백 명령: ./deploy.sh --rollback"
log_info " 로그 확인: docker compose -f $COMPOSE_FILE logs -f $APP_SERVICE"
log_info "══════════════════════════════════════════"
