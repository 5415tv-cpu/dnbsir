#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# 동네비서 서버 초기 셋업 스크립트 (최초 1회 실행)
# 실행 위치: api.dnbsir.com 서버에서 직접
#
# [실행 방법]
#   # 서버에 SSH 접속 후:
#   curl -fsSL https://raw.githubusercontent.com/[repo]/main/infra/scripts/server_setup.sh | bash
#   # 또는 로컬에서 업로드 후:
#   scp infra/scripts/server_setup.sh user@api.dnbsir.com:/tmp/
#   ssh user@api.dnbsir.com "chmod +x /tmp/server_setup.sh && /tmp/server_setup.sh"
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

DEPLOY_DIR="/opt/dnbsir"
GIT_REPO="${GIT_REPO:-git@github.com:your-org/AI_Store.git}"  # ← 실제 저장소 URL로 변경
GIT_BRANCH="${GIT_BRANCH:-main}"

log_info "══════════════════════════════════════"
log_info " 동네비서 서버 초기 셋업"
log_info "══════════════════════════════════════"

# ── Docker 설치 확인 ──────────────────────────────────────────
log_info "Docker 설치 확인..."
if ! command -v docker &>/dev/null; then
    log_info "Docker 설치 중..."
    curl -fsSL https://get.docker.com | bash
    usermod -aG docker "$USER"
    log_ok "Docker 설치 완료"
else
    log_ok "Docker 이미 설치됨: $(docker --version)"
fi

# ── 배포 디렉토리 설정 ────────────────────────────────────────
log_info "배포 디렉토리 설정: $DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"

if [[ -d "$DEPLOY_DIR/.git" ]]; then
    log_info "기존 저장소 업데이트..."
    cd "$DEPLOY_DIR"
    git fetch origin
    git checkout "$GIT_BRANCH"
    git pull origin "$GIT_BRANCH"
else
    log_info "저장소 클론: $GIT_REPO"
    git clone -b "$GIT_BRANCH" "$GIT_REPO" "$DEPLOY_DIR"
fi
log_ok "코드 동기화 완료"

# ── .env 설정 ────────────────────────────────────────────────
if [[ ! -f "$DEPLOY_DIR/.env" ]]; then
    cp "$DEPLOY_DIR/.env.example" "$DEPLOY_DIR/.env"
    log_warn "⚠️  $DEPLOY_DIR/.env 파일을 반드시 수정해 주세요!"
    log_warn "필수 항목:"
    log_warn "  GOOGLE_API_KEY=..."
    log_warn "  TANTAN_DB_PASSWORD=..."
    log_warn "  WEBHOOK_SECRET_TOKEN=..."
    log_warn "  SOLAPI_API_KEY=..."
    echo ""
    log_warn "수정 후 다음 명령어로 배포를 계속하세요:"
    log_warn "  cd $DEPLOY_DIR && ./infra/scripts/deploy.sh"
    exit 0
fi

# ── Redis 외부 접속 허용 설정 (워크스테이션 워커용) ────────────
log_info "Redis 외부 접속 설정 (워크스테이션 → 서버 Celery 큐)..."
log_warn "보안 권장: Redis를 공개하지 말고 VPN 또는 SSH 터널 사용"
log_warn "방화벽 규칙 예시 (워크스테이션 IP만 허용):"
log_warn "  sudo ufw allow from [워크스테이션_IP] to any port 6379"
log_warn "  또는 docker-compose.yml의 redis ports 섹션에서 127.0.0.1:6379:6379 로 변경 후 SSH 터널 사용"

# ── 스크립트 권한 설정 ─────────────────────────────────────────
chmod +x "$DEPLOY_DIR/infra/scripts/deploy.sh"
chmod +x "$DEPLOY_DIR/infra/scripts/gpu_worker_connect.sh"
log_ok "스크립트 권한 설정 완료"

# ── 심볼릭 링크로 편의 명령어 등록 ────────────────────────────
ln -sf "$DEPLOY_DIR/infra/scripts/deploy.sh" /usr/local/bin/dnbsir-deploy 2>/dev/null || true
log_ok "편의 명령어 등록: dnbsir-deploy"

# ── 배포 실행 ────────────────────────────────────────────────
log_info "초기 배포 실행..."
cd "$DEPLOY_DIR"
"$DEPLOY_DIR/infra/scripts/deploy.sh"

log_info "══════════════════════════════════════"
log_ok " 서버 초기 셋업 완료!"
log_info " 이후 배포: dnbsir-deploy"
log_info " 롤백:     dnbsir-deploy --rollback"
log_info "══════════════════════════════════════"
