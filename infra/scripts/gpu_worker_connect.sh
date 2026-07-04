#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# 동네비서 — GPU 워크스테이션 미디어 워커 연결 스크립트 (보안 강화판)
#
# [보안 원칙] Redis 6379 포트를 외부에 절대 노출하지 않습니다.
#             SSH 터널을 통해 암호화된 로컬 포트 포워딩만 사용합니다.
#
#   워크스테이션                   메인 서버 (api.dnbsir.com)
#   ─────────────────────────────────────────────────────────
#   media_worker                    Redis:6379 (내부 전용)
#        │                               │
#        └──→ localhost:6399 ←─[SSH 터널]─┘
#
#   Redis URL: redis://localhost:6399/1 (포트 6399는 로컬 전용)
#   외부 방화벽: 6379 포트 완전 폐쇄 유지
#
# [사전 요구사항]
#   - SSH 키가 api.dnbsir.com 에 등록되어 있어야 합니다
#   - 로컬에 Docker + redis-cli 설치
#
# [실행 방법]
#   WSL2 또는 Git Bash 에서:
#   chmod +x gpu_worker_connect.sh
#
#   ./gpu_worker_connect.sh --tunnel-start    # 1단계: SSH 터널 개통
#   ./gpu_worker_connect.sh --check           # 2단계: 연결 상태 점검
#   ./gpu_worker_connect.sh --start-worker    # 3단계: Celery 워커 시작
#   ./gpu_worker_connect.sh --test-queue      # 4단계: 큐 통신 최종 확인
#   ./gpu_worker_connect.sh --stop            # 종료: 터널 + 워커 중지
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()      { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*"; }
log_security(){ echo -e "${CYAN}[보안]${NC}  $*"; }
log_step()    { echo -e "\n${BOLD}$*${NC}"; }

# ── 설정 ──────────────────────────────────────────────────────────────
SSH_USER="${SSH_USER:-root}"                       # 서버 SSH 유저
SSH_HOST="${SSH_HOST:-api.dnbsir.com}"            # 메인 서버 주소
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_rsa}"            # SSH 키 경로

LOCAL_TUNNEL_PORT="6399"                           # 로컬 포워딩 포트 (6379 ≠)
REMOTE_REDIS_PORT="6379"                           # 서버 내부 Redis 포트 (비노출)
REDIS_DB="1"                                       # DB1: 워커 전용 큐

TUNNEL_PID_FILE="/tmp/dnbsir_redis_tunnel.pid"
TUNNEL_REDIS_URL="redis://localhost:${LOCAL_TUNNEL_PORT}/${REDIS_DB}"

COMFYUI_HOST="${COMFYUI_HOST:-localhost}"
COMFYUI_PORT="${COMFYUI_PORT:-8188}"

WORKER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/media_worker"
WORKER_CONTAINER="dnbsir-media-worker-local"

MODE="${1:---help}"

# ── 보안 배너 ─────────────────────────────────────────────────────────
print_banner() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  동네비서 GPU 워커 — SSH 터널 보안 연결        ║${NC}"
    echo -e "${CYAN}║  Redis 포트 비노출 원칙 (외부 6379 완전 폐쇄)  ║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║  서버: ${SSH_USER}@${SSH_HOST}${NC}"
    printf "${CYAN}║  터널: localhost:%-5s → 서버 내부:%-5s (DB%s)  ║${NC}\n" \
        "$LOCAL_TUNNEL_PORT" "$REMOTE_REDIS_PORT" "$REDIS_DB"
    echo -e "${CYAN}╚════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ══════════════════════════════════════════════════════════════════════
# STEP 1: SSH 터널 개통
# ══════════════════════════════════════════════════════════════════════
start_tunnel() {
    log_step "STEP 1 — SSH 터널 개통"
    log_security "Redis 포트(${REMOTE_REDIS_PORT}) 외부 노출 없이 암호화 터널만 사용합니다."

    # 기존 터널 확인
    if [[ -f "$TUNNEL_PID_FILE" ]]; then
        OLD_PID=$(cat "$TUNNEL_PID_FILE")
        if kill -0 "$OLD_PID" 2>/dev/null; then
            log_ok "기존 터널 이미 활성: PID=$OLD_PID (로컬 포트 $LOCAL_TUNNEL_PORT)"
            verify_tunnel
            return 0
        else
            rm -f "$TUNNEL_PID_FILE"
        fi
    fi

    # SSH 키 파일 확인
    if [[ ! -f "$SSH_KEY" ]]; then
        log_error "SSH 키 파일 없음: $SSH_KEY"
        log_error "SSH_KEY 환경변수로 경로를 지정하세요: SSH_KEY=/path/to/key ./gpu_worker_connect.sh"
        exit 1
    fi

    # 서버 SSH 연결 테스트
    log_info "서버 SSH 연결 테스트..."
    if ! ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o BatchMode=yes \
             "${SSH_USER}@${SSH_HOST}" "echo tunnel_test_ok" 2>/dev/null | grep -q "tunnel_test_ok"; then
        log_error "SSH 연결 실패: ${SSH_USER}@${SSH_HOST}"
        log_error "확인 사항:"
        log_error "  1. SSH 키 등록: ssh-copy-id -i $SSH_KEY ${SSH_USER}@${SSH_HOST}"
        log_error "  2. 서버 SSH 포트 확인 (기본 22)"
        log_error "  3. 방화벽에서 22 포트 허용 여부"
        exit 1
    fi
    log_ok "서버 SSH 연결 성공"

    # 로컬 포트 사용 중 확인
    if lsof -i ":${LOCAL_TUNNEL_PORT}" &>/dev/null 2>&1; then
        log_warn "로컬 포트 ${LOCAL_TUNNEL_PORT}이 이미 사용 중입니다."
        log_warn "기존 프로세스를 종료하거나 LOCAL_TUNNEL_PORT를 변경하세요."
        exit 1
    fi

    # SSH 터널 백그라운드 실행
    # -N: 명령어 없이 포트 포워딩만
    # -f: 백그라운드 실행
    # -L: 로컬 포트 → 서버 내부 포트 포워딩
    # ServerAliveInterval: 연결 유지 (idle 차단 방지)
    ssh -i "$SSH_KEY" \
        -N -f \
        -L "${LOCAL_TUNNEL_PORT}:localhost:${REMOTE_REDIS_PORT}" \
        -o ServerAliveInterval=30 \
        -o ServerAliveCountMax=3 \
        -o ExitOnForwardFailure=yes \
        -o StrictHostKeyChecking=accept-new \
        "${SSH_USER}@${SSH_HOST}"

    # PID 저장
    SSH_TUNNEL_PID=$(pgrep -f "ssh.*${LOCAL_TUNNEL_PORT}:localhost:${REMOTE_REDIS_PORT}" | tail -1)
    echo "$SSH_TUNNEL_PID" > "$TUNNEL_PID_FILE"

    sleep 2
    log_ok "SSH 터널 개통 완료 (PID: $SSH_TUNNEL_PID)"
    log_security "외부 방화벽에서 Redis ${REMOTE_REDIS_PORT} 포트는 계속 폐쇄 상태입니다."

    verify_tunnel
}

# ── 터널 동작 검증 ────────────────────────────────────────────────────
verify_tunnel() {
    log_info "터널 경유 Redis PING 테스트..."
    PONG=$(redis-cli -h localhost -p "$LOCAL_TUNNEL_PORT" -n "$REDIS_DB" PING 2>/dev/null || echo "FAIL")
    if [[ "$PONG" == "PONG" ]]; then
        log_ok "Redis PING → PONG (터널 경유, DB${REDIS_DB})"
        QUEUE_LEN=$(redis-cli -h localhost -p "$LOCAL_TUNNEL_PORT" -n "$REDIS_DB" LLEN "media_tasks" 2>/dev/null || echo "?")
        log_ok "media_tasks 큐 대기 태스크: ${QUEUE_LEN}개"
    else
        log_error "Redis 응답 없음 — 터널 상태를 확인하세요."
        exit 1
    fi
}

# ══════════════════════════════════════════════════════════════════════
# STEP 2: 전체 연결 상태 점검
# ══════════════════════════════════════════════════════════════════════
check_all() {
    log_step "STEP 2 — 연결 상태 전체 점검"

    # 터널 상태
    if [[ -f "$TUNNEL_PID_FILE" ]] && kill -0 "$(cat "$TUNNEL_PID_FILE")" 2>/dev/null; then
        log_ok "SSH 터널: 활성 (PID=$(cat "$TUNNEL_PID_FILE"))"
        verify_tunnel
    else
        log_warn "SSH 터널: 비활성 — 먼저 --tunnel-start 를 실행하세요"
    fi

    # ComfyUI 상태
    log_info "ComfyUI 연결 테스트: ${COMFYUI_HOST}:${COMFYUI_PORT}"
    COMFY=$(curl -sf --max-time 5 "http://${COMFYUI_HOST}:${COMFYUI_PORT}/system_stats" 2>/dev/null || echo "FAIL")
    if [[ "$COMFY" != "FAIL" ]]; then
        GPU=$(echo "$COMFY" | python3 -c \
            "import sys,json; d=json.load(sys.stdin); print(d.get('system',{}).get('gpu_name','알 수 없음'))" 2>/dev/null || echo "파싱 실패")
        log_ok "ComfyUI 연결 성공 — GPU: $GPU"
    else
        log_warn "ComfyUI 응답 없음 — 별도 터미널에서 ComfyUI를 먼저 실행하세요:"
        log_warn "  cd /path/to/ComfyUI && python main.py --listen"
    fi

    # 워커 컨테이너 상태
    if docker ps --filter "name=$WORKER_CONTAINER" --filter "status=running" | grep -q "$WORKER_CONTAINER"; then
        log_ok "media-worker 컨테이너: 실행 중"
    else
        log_warn "media-worker 컨테이너: 미실행 (--start-worker 로 시작)"
    fi
}

# ══════════════════════════════════════════════════════════════════════
# STEP 3: Celery 워커 컨테이너 시작
# ══════════════════════════════════════════════════════════════════════
start_worker() {
    log_step "STEP 3 — media_worker 컨테이너 시작"

    # 터널 활성 확인 (워커 시작 전 필수)
    if [[ ! -f "$TUNNEL_PID_FILE" ]] || ! kill -0 "$(cat "$TUNNEL_PID_FILE")" 2>/dev/null; then
        log_error "SSH 터널이 활성 상태가 아닙니다."
        log_error "먼저 실행: ./gpu_worker_connect.sh --tunnel-start"
        exit 1
    fi
    log_ok "SSH 터널 활성 확인"

    cd "$WORKER_DIR"

    # .env 설정 (터널 경유 localhost URL 주입)
    if [[ ! -f ".env" ]]; then
        cp .env.example .env
        log_warn ".env.example → .env 복사. 필요한 값을 추가로 설정하세요."
    fi

    # Redis URL을 터널 경유 localhost로 강제 설정
    if grep -q "MEDIA_WORKER_REDIS_URL" .env; then
        sed -i "s|MEDIA_WORKER_REDIS_URL=.*|MEDIA_WORKER_REDIS_URL=${TUNNEL_REDIS_URL}|" .env
    else
        echo "MEDIA_WORKER_REDIS_URL=${TUNNEL_REDIS_URL}" >> .env
    fi
    log_security "Redis URL = ${TUNNEL_REDIS_URL} (터널 경유, 외부 노출 없음)"

    # 이미지 빌드
    log_info "워커 이미지 빌드..."
    docker build -f Dockerfile.worker -t dnbsir-media-worker:local . 2>&1 | grep -E "Step|Successfully|ERROR" || true

    # 기존 컨테이너 제거 후 재시작
    docker rm -f "$WORKER_CONTAINER" 2>/dev/null || true

    # ── 핵심: --network=host 로 SSH 터널(localhost:6399) 접근 가능하게 ──
    docker run -d \
        --name "$WORKER_CONTAINER" \
        --restart unless-stopped \
        --network host \
        --env-file .env \
        -e "MEDIA_WORKER_REDIS_URL=${TUNNEL_REDIS_URL}" \
        -e "MEDIA_WORKER_COMFYUI_HOST=${COMFYUI_HOST}" \
        -e "MEDIA_WORKER_COMFYUI_PORT=${COMFYUI_PORT}" \
        --memory=8g \
        --memory-swap=8g \
        --shm-size=2g \
        dnbsir-media-worker:local

    log_ok "워커 컨테이너 시작: $WORKER_CONTAINER"
    sleep 5

    log_info "워커 시작 로그 (최근 20줄):"
    docker logs "$WORKER_CONTAINER" --tail=20
}

# ══════════════════════════════════════════════════════════════════════
# STEP 4: Celery 큐 통신 최종 확인
# ══════════════════════════════════════════════════════════════════════
test_queue() {
    log_step "STEP 4 — Celery 큐 통신 최종 확인"

    # 터널 경유 헬스체크 태스크 투입
    python3 - <<PYEOF
import sys, os, time
os.environ["REDIS_URL"] = "${TUNNEL_REDIS_URL}"

try:
    from celery import Celery

    app = Celery(
        broker="${TUNNEL_REDIS_URL}",
        backend="${TUNNEL_REDIS_URL}"
    )
    print(f"[INFO] 태스크 투입 중... (브로커: localhost:{LOCAL_TUNNEL_PORT}/DB{REDIS_DB})")

    result = app.send_task("worker.health_check")
    print(f"[INFO] 태스크 ID: {result.id}")
    print(f"[INFO] 워커 응답 대기 (최대 15초)...")

    try:
        resp = result.get(timeout=15)
        print(f"\n[OK] ✅ 큐 통신 성공!")
        print(f"[OK] 워커 응답: {resp}")
        print(f"\n[보안] Redis 포트는 SSH 터널로만 통신했습니다. 외부 노출 없음.")
    except Exception as e:
        print(f"\n[WARN] ⏱️  워커 응답 타임아웃: {e}")
        print(f"[INFO] 워커가 아직 초기화 중일 수 있습니다.")
        print(f"[INFO] 30초 후 재시도: ./gpu_worker_connect.sh --test-queue")

except ImportError:
    print("[WARN] celery 미설치: pip install celery redis")
    sys.exit(0)
PYEOF
}

# ══════════════════════════════════════════════════════════════════════
# 종료: 터널 + 워커 안전 중지
# ══════════════════════════════════════════════════════════════════════
stop_all() {
    log_step "종료 — SSH 터널 + 워커 중지"

    # 워커 중지
    if docker ps --filter "name=$WORKER_CONTAINER" | grep -q "$WORKER_CONTAINER"; then
        docker stop "$WORKER_CONTAINER" && docker rm "$WORKER_CONTAINER"
        log_ok "워커 컨테이너 중지"
    else
        log_info "워커 컨테이너가 실행 중이지 않습니다."
    fi

    # SSH 터널 종료
    if [[ -f "$TUNNEL_PID_FILE" ]]; then
        TUNNEL_PID=$(cat "$TUNNEL_PID_FILE")
        if kill -0 "$TUNNEL_PID" 2>/dev/null; then
            kill "$TUNNEL_PID"
            log_ok "SSH 터널 종료 (PID: $TUNNEL_PID)"
        fi
        rm -f "$TUNNEL_PID_FILE"
    else
        log_info "활성 SSH 터널이 없습니다."
    fi

    # 혹시 남은 터널 프로세스 정리
    pkill -f "ssh.*${LOCAL_TUNNEL_PORT}:localhost:${REMOTE_REDIS_PORT}" 2>/dev/null || true
    log_ok "정리 완료"
}

# ══════════════════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════════════════
print_banner

# 필수 로컬 도구 확인
for tool in ssh redis-cli docker python3; do
    if ! command -v "$tool" &>/dev/null; then
        log_warn "$tool 미설치 — 일부 기능이 제한될 수 있습니다."
    fi
done

case "$MODE" in
    --tunnel-start)
        start_tunnel
        log_ok "다음 단계: ./gpu_worker_connect.sh --check"
        ;;
    --check)
        check_all
        ;;
    --start-worker)
        start_worker
        log_ok "다음 단계: ./gpu_worker_connect.sh --test-queue"
        ;;
    --test-queue)
        test_queue
        ;;
    --stop)
        stop_all
        ;;
    --status)
        log_info "SSH 터널:"
        if [[ -f "$TUNNEL_PID_FILE" ]] && kill -0 "$(cat "$TUNNEL_PID_FILE")" 2>/dev/null; then
            echo "  활성 — PID=$(cat "$TUNNEL_PID_FILE"), 로컬:$LOCAL_TUNNEL_PORT → 서버:$REMOTE_REDIS_PORT"
        else
            echo "  비활성"
        fi
        echo ""
        log_info "워커 컨테이너:"
        docker ps --filter "name=$WORKER_CONTAINER" \
            --format "  {{.Names}}\t{{.Status}}\t{{.Image}}" 2>/dev/null || echo "  없음"
        ;;
    *)
        echo -e "${BOLD}사용법:${NC}"
        echo "  ./gpu_worker_connect.sh --tunnel-start   # 1단계: SSH 터널 개통"
        echo "  ./gpu_worker_connect.sh --check          # 2단계: 연결 상태 점검"
        echo "  ./gpu_worker_connect.sh --start-worker   # 3단계: Celery 워커 시작"
        echo "  ./gpu_worker_connect.sh --test-queue     # 4단계: 큐 통신 확인"
        echo "  ./gpu_worker_connect.sh --stop           # 종료: 터널 + 워커 중지"
        echo "  ./gpu_worker_connect.sh --status         # 현재 상태 확인"
        echo ""
        echo -e "${BOLD}환경변수:${NC}"
        echo "  SSH_USER=root         SSH 접속 유저 (기본: root)"
        echo "  SSH_HOST=api.dnbsir.com  서버 주소 (기본값)"
        echo "  SSH_KEY=~/.ssh/id_rsa SSH 키 경로"
        echo "  COMFYUI_HOST=localhost ComfyUI 주소 (기본: localhost)"
        echo "  COMFYUI_PORT=8188     ComfyUI 포트"
        echo ""
        echo -e "${CYAN}[보안] Redis 포트는 외부에 절대 노출하지 않습니다.${NC}"
        ;;
esac
