"""
탄탄제작소 Control Tower — 관리자 전용 API
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
모든 엔드포인트 JWT 인증 필수 (verify_admin_jwt dependency)

모듈 1: 인프라 감시   GET /api/tantan/admin/infra/status
모듈 2: 파이프라인    GET /api/tantan/admin/tasks
                     GET /api/tantan/admin/tasks/{id}/dlq
                     POST /api/tantan/admin/tasks/{id}/retry
모듈 3: 유저/알림    GET /api/tantan/admin/credits
                     POST /api/tantan/admin/grant
                     POST /api/tantan/admin/deduct
                     GET /api/tantan/admin/sms-logs
인증               POST /api/tantan/admin/auth/login
"""
from __future__ import annotations

import json, logging, math, os, time
from datetime import datetime, timedelta, timezone
from typing import Optional

import redis
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

logger = logging.getLogger("tantan.admin")

router = APIRouter(prefix="/api/tantan/admin", tags=["tantan-control-tower"])

# ── 상수 ────────────────────────────────────────────────────────
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin8705")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Aass12!!")
JWT_SECRET     = os.environ.get("TANTAN_JWT_SECRET",
                 os.environ.get("TOSS_SECURITY_KEY", "tantan-jwt-secret-2026"))
JWT_ALGO       = "HS256"
JWT_EXPIRE_H   = 4          # 4시간
TASK_TTL_SEC   = 7 * 86400  # 7일

_redis_client: Optional[redis.Redis] = None

def _rdb() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        url = os.environ.get("CELERY_RESULT_BACKEND",
              os.environ.get("REDIS_URL", "redis://localhost:6379/1"))
        _redis_client = redis.from_url(url, decode_responses=True)
    return _redis_client

# ── JWT ─────────────────────────────────────────────────────────
def _make_jwt(sub: str) -> str:
    try:
        import jwt as pyjwt
    except ImportError:
        import PyJWT as pyjwt  # type: ignore
    payload = {
        "sub": sub,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_H),
        "role": "superuser",
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def _decode_jwt(token: str) -> dict:
    try:
        import jwt as pyjwt
    except ImportError:
        import PyJWT as pyjwt  # type: ignore
    try:
        return pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except Exception as e:
        raise HTTPException(401, f"토큰 오류: {e}")

_bearer = HTTPBearer(auto_error=False)

def verify_admin_jwt(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """모든 관리자 API에 적용되는 이중 인증 Dependency."""
    if not creds or not creds.credentials:
        raise HTTPException(401, "관리자 인증 토큰이 필요합니다.")
    payload = _decode_jwt(creds.credentials)
    if payload.get("role") != "superuser":
        raise HTTPException(403, "Superuser 권한 없음.")
    return payload


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 인증
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class LoginReq(BaseModel):
    username: str
    password: str

@router.post("/auth/login")
async def admin_login(req: LoginReq):
    if req.username != ADMIN_USERNAME or req.password != ADMIN_PASSWORD:
        raise HTTPException(401, "아이디 또는 비밀번호가 틀렸습니다.")
    token = _make_jwt(req.username)
    logger.info(f"[Admin] 로그인: {req.username}")
    return {
        "access_token": token,
        "token_type":   "bearer",
        "expires_in":   JWT_EXPIRE_H * 3600,
    }

@router.get("/auth/me")
async def admin_me(admin: dict = Depends(verify_admin_jwt)):
    return {"username": admin["sub"], "role": admin["role"]}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 모듈 1: 인프라 감시
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@router.get("/infra/status")
async def infra_status(admin: dict = Depends(verify_admin_jwt)):
    rdb = _rdb()

    # Redis 연결 확인
    try:
        rdb.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    # Celery 큐 깊이 (video_tasks 큐)
    queue_depth = 0
    try:
        queue_depth = rdb.llen("video_tasks") or 0
        if queue_depth == 0:
            queue_depth = rdb.llen("celery") or 0
    except Exception:
        pass

    # GPU 워커 상태 (Celery Inspect)
    worker_info = _get_worker_status()

    # 오늘 통계
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_done   = int(rdb.get(f"tantan:stats:done:{today}") or 0)
    today_failed = int(rdb.get(f"tantan:stats:failed:{today}") or 0)
    total_tasks  = int(rdb.zcard("tantan:tasks:index") or 0)

    return {
        "redis_connected":  redis_ok,
        "queue_depth":      queue_depth,
        "worker":           worker_info,
        "stats": {
            "today_completed": today_done,
            "today_failed":    today_failed,
            "total_tasks":     total_tasks,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

def _get_worker_status() -> dict:
    """Celery Inspect로 워커 상태 파악."""
    base = {
        "status":   "Offline",
        "hostname": None,
        "active_tasks": 0,
        "last_heartbeat": None,
    }
    try:
        from media_worker.celery_app import app as celery_app
        inspect = celery_app.control.inspect(timeout=1.5)

        # ping으로 살아있는지 확인
        pong = inspect.ping()
        if not pong:
            return base

        hostname = list(pong.keys())[0]
        base["hostname"] = hostname

        # 활성 태스크
        active = inspect.active() or {}
        active_list = active.get(hostname, [])
        base["active_tasks"] = len(active_list)

        if active_list:
            base["status"] = "Rendering"
        else:
            # 예약된 태스크
            reserved = inspect.reserved() or {}
            reserved_list = reserved.get(hostname, [])
            base["status"] = "Idle" if not reserved_list else "Idle"

        base["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
        return base
    except Exception as e:
        logger.debug(f"Worker inspect 실패: {e}")
        # Redis heartbeat로 fallback
        rdb = _rdb()
        hb = rdb.get("tantan:worker:heartbeat")
        if hb:
            ts = float(hb)
            if time.time() - ts < 30:
                base["status"] = "Idle"
                base["last_heartbeat"] = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        return base


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 모듈 2: 파이프라인 관제
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _paginate_zset(rdb: redis.Redis, key: str,
                   page: int, size: int, status_filter: Optional[str] = None):
    """Redis Sorted Set에서 역순(최신 먼저) 페이지네이션."""
    total_raw = rdb.zcard(key)

    if status_filter and status_filter != "all":
        # 상태 필터: 전체 스캔 후 필터 (수량이 많지 않을 때 안전)
        all_ids = rdb.zrevrange(key, 0, -1)
        filtered = []
        for tid in all_ids:
            raw = rdb.get(f"tantan:task:{tid}")
            if not raw:
                continue
            task = json.loads(raw)
            if task.get("status", "").lower() == status_filter.lower():
                filtered.append(task)
        total = len(filtered)
        start = (page - 1) * size
        items = filtered[start:start + size]
    else:
        total = total_raw
        start = (page - 1) * size
        ids   = rdb.zrevrange(key, start, start + size - 1)
        items = []
        for tid in ids:
            raw = rdb.get(f"tantan:task:{tid}")
            if raw:
                items.append(json.loads(raw))

    return {
        "items":  items,
        "total":  total,
        "page":   page,
        "size":   size,
        "pages":  max(1, math.ceil(total / size)) if total else 1,
    }

@router.get("/tasks")
async def list_tasks(
    page:   int = Query(1, ge=1),
    size:   int = Query(20, ge=1, le=50),
    status: str = Query("all"),
    admin: dict = Depends(verify_admin_jwt),
):
    rdb = _rdb()
    return _paginate_zset(rdb, "tantan:tasks:index", page, size, status)

@router.get("/tasks/{task_id}")
async def get_task(task_id: str, admin: dict = Depends(verify_admin_jwt)):
    rdb = _rdb()
    raw = rdb.get(f"tantan:task:{task_id}")
    if not raw:
        raise HTTPException(404, "작업을 찾을 수 없습니다.")
    return json.loads(raw)

@router.get("/tasks/{task_id}/dlq")
async def get_task_dlq(task_id: str, admin: dict = Depends(verify_admin_jwt)):
    rdb = _rdb()
    raw = rdb.get(f"tantan:task:{task_id}")
    if not raw:
        raise HTTPException(404, "작업을 찾을 수 없습니다.")
    task = json.loads(raw)
    if task.get("status") not in ("failed", "Failed", "FAILURE"):
        raise HTTPException(400, "실패 상태의 작업이 아닙니다.")
    return {
        "task_id":       task_id,
        "error_type":    task.get("error_type", "UnknownError"),
        "traceback":     task.get("error_traceback", "트레이스백 없음"),
        "failed_at":     task.get("completed_at"),
        "retry_count":   task.get("retry_count", 0),
    }

@router.post("/tasks/{task_id}/retry")
async def retry_task(task_id: str, admin: dict = Depends(verify_admin_jwt)):
    rdb = _rdb()
    raw = rdb.get(f"tantan:task:{task_id}")
    if not raw:
        raise HTTPException(404, "작업을 찾을 수 없습니다.")
    task = json.loads(raw)
    try:
        from media_worker.tasks.video_tasks import generate_shortform_video
        new_task = generate_shortform_video.apply_async(
            kwargs=task.get("original_kwargs", {}),
            queue="video_tasks",
        )
        logger.info(f"[Admin] 재시도: {task_id} → {new_task.id}")
        return {"success": True, "new_task_id": new_task.id}
    except Exception as e:
        raise HTTPException(500, f"재시도 실패: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 모듈 3: 유저 & 알림 통제
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@router.get("/credits")
async def list_credits(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    admin: dict = Depends(verify_admin_jwt),
):
    rdb   = _rdb()
    keys  = sorted(rdb.keys("tantan:credit:*"))
    total = len(keys)
    start = (page - 1) * size
    chunk = keys[start:start + size]
    items = []
    for k in chunk:
        phone = k.replace("tantan:credit:", "")
        credits = int(rdb.get(k) or 0)
        items.append({"phone": phone, "phone_masked": _mask(phone), "credits": credits})
    items.sort(key=lambda x: x["credits"], reverse=True)
    return {
        "items": items, "total": total,
        "page": page, "size": size,
        "pages": max(1, math.ceil(total / size)) if total else 1,
    }

class GrantReq(BaseModel):
    phone:   str
    credits: int = Field(..., ge=1, le=100)

@router.post("/grant")
async def grant_credits(req: GrantReq, admin: dict = Depends(verify_admin_jwt)):
    rdb = _rdb()
    new = rdb.incrby(f"tantan:credit:{req.phone}", req.credits)
    logger.info(f"[Admin] {req.phone} +{req.credits} → {new}")
    return {"success": True, "phone": req.phone, "total_credits": new}

class DeductReq(BaseModel):
    phone:   str
    credits: int = Field(..., ge=1, le=100)

@router.post("/deduct")
async def deduct_credits(req: DeductReq, admin: dict = Depends(verify_admin_jwt)):
    rdb  = _rdb()
    cur  = int(rdb.get(f"tantan:credit:{req.phone}") or 0)
    if cur < req.credits:
        raise HTTPException(400, f"잔여 크레딧({cur})보다 차감 요청({req.credits})이 많습니다.")
    new = rdb.decrby(f"tantan:credit:{req.phone}", req.credits)
    logger.info(f"[Admin] {req.phone} -{req.credits} → {new}")
    return {"success": True, "phone": req.phone, "total_credits": new}

@router.get("/sms-logs")
async def list_sms_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    admin: dict = Depends(verify_admin_jwt),
):
    rdb = _rdb()
    return _paginate_zset(rdb, "tantan:sms:logs:index", page, size)


# ── 유틸 ────────────────────────────────────────────────────────
def _mask(phone: str) -> str:
    if len(phone) >= 10:
        return phone[:3] + "-****-" + phone[-4:]
    return phone

import sqlite3
from pathlib import Path
STORES_DB_PATH = Path(__file__).parent.parent / "stores.db"

def _get_stores_db():
    conn = sqlite3.connect(str(STORES_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

@router.get("/stores/tokens")
async def list_store_tokens(admin: dict = Depends(verify_admin_jwt)):
    """동네비서 가맹점 목록 및 토큰 조회"""
    try:
        with _get_stores_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT subdomain, store_name, phone, address, tokens FROM stores ORDER BY id DESC")
            stores = [dict(row) for row in cursor.fetchall()]
        return {"success": True, "stores": stores}
    except Exception as e:
        logger.error(f"[Admin] stores.db 조회 실패: {e}")
        raise HTTPException(500, f"가맹점 조회 실패: {e}")

class StoreRechargeReq(BaseModel):
    subdomain: str
    amount: int  # 결제 금액 (원)

@router.post("/stores/recharge")
async def recharge_store_tokens(req: StoreRechargeReq, admin: dict = Depends(verify_admin_jwt)):
    """동네비서 가맹점 토큰 충전 (보너스 로직 포함)"""
    import math
    try:
        base_tokens = req.amount / 10
        if req.amount >= 200000:
            bonus = 1.15
        elif req.amount >= 100000:
            bonus = 1.10
        else:
            bonus = 1.0

        added_tokens = math.floor(base_tokens * bonus)

        with _get_stores_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT tokens FROM stores WHERE subdomain = ?", (req.subdomain,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(404, "가맹점을 찾을 수 없습니다.")
            
            old_tokens = row["tokens"]
            new_tokens = old_tokens + added_tokens
            
            # 토큰 업데이트
            cursor.execute("UPDATE stores SET tokens = ? WHERE subdomain = ?", (new_tokens, req.subdomain))
            
            # 충전 내역 기록
            cursor.execute(
                """INSERT INTO token_recharges 
                   (subdomain, method, amount, tokens_added) 
                   VALUES (?, '신용카드(관리자수동)', ?, ?)""",
                (req.subdomain, req.amount, added_tokens)
            )
            conn.commit()
            
        logger.info(f"[Admin] 가맹점 토큰 충전: {req.subdomain} / 금액: {req.amount}원 / 지급: {added_tokens}토큰")
        return {"success": True, "subdomain": req.subdomain, "added_tokens": added_tokens, "balance_after": new_tokens}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin] 토큰 충전 실패: {e}")
        raise HTTPException(500, f"토큰 충전 실패: {e}")

# ── 외부에서 호출되는 Task 기록 헬퍼 ───────────────────────────
def record_task(task_id: str, data: dict, ttl: int = TASK_TTL_SEC):
    """video_tasks.py에서 호출 — 태스크 상태 Redis 기록."""
    try:
        rdb = _rdb()
        data["id"] = task_id
        rdb.setex(f"tantan:task:{task_id}", ttl, json.dumps(data, ensure_ascii=False))
        score = data.get("created_ts", time.time())
        rdb.zadd("tantan:tasks:index", {task_id: score})
        rdb.expire("tantan:tasks:index", ttl)

        # 일별 통계
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        status = data.get("status", "")
        if status in ("completed", "Completed", "SUCCESS"):
            rdb.incr(f"tantan:stats:done:{today}")
            rdb.expire(f"tantan:stats:done:{today}", 30 * 86400)
        elif status in ("failed", "Failed", "FAILURE"):
            rdb.incr(f"tantan:stats:failed:{today}")
            rdb.expire(f"tantan:stats:failed:{today}", 30 * 86400)
    except Exception as e:
        logger.error(f"record_task 실패: {e}")

def record_sms_log(phone: str, code: str, status: str,
                   response: str = "", ttl: int = TASK_TTL_SEC):
    """tantan_payment.py에서 호출 — SMS 발송 로그 Redis 기록."""
    try:
        rdb  = _rdb()
        ts   = time.time()
        key  = f"tantan:sms:log:{int(ts * 1000)}"
        data = {
            "phone_masked": _mask(phone),
            "status":       status,
            "solapi_resp":  response[:200],
            "sent_at":      datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
        }
        rdb.setex(key, ttl, json.dumps(data))
        rdb.zadd("tantan:sms:logs:index", {key: ts})
        rdb.expire("tantan:sms:logs:index", ttl)
    except Exception as e:
        logger.error(f"record_sms_log 실패: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 모듈 4: 시스템 헬스체크 & 테스트 렌더링
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 더미 주문서 — 실제 상품처럼 보이지만 is_test=True
DUMMY_MERCHANT_FACTS = {
    "product":  "테스트 상품입니다",
    "price":    "1,000원 (시스템 점검용)",
    "features": "헬스체크,테스트렌더링,시스템점검",
    "origin":   "탄탄제작소 Control Tower",
    "cta":      "시스템 점검 중입니다",
}

DUMMY_ASSETS_BASE = {
    "bgm_preset":   1,
    "gemini_voice": "Kore",
    "is_test":      True,    # ← 핵심 플래그: bypass 트리거
}

class TestRenderReq(BaseModel):
    product:  str = "테스트 상품입니다"
    price:    str = "1,000원 (시스템 점검용)"
    features: str = "헬스체크,테스트렌더링,시스템점검"
    origin:   str = "탄탄제작소 Control Tower"
    cta:      str = "시스템 점검 중입니다"
    bgm:      int = 1
    voice:    str = "Kore"

@router.post("/healthcheck/render")
async def start_test_render(
    req:   TestRenderReq = TestRenderReq(),
    admin: dict = Depends(verify_admin_jwt),
):
    """
    모듈4: 더미 데이터로 테스트 렌더링 시작.
    is_test=True → 크레딧 차감·SMS·Webhook 모두 bypass.
    오직 FFmpeg 렌더링 파이프라인만 실행.
    """
    import uuid as _uuid
    job_id = f"test-{_uuid.uuid4().hex[:10]}"

    merchant_facts = {
        "product":  req.product,
        "price":    req.price,
        "features": req.features,
        "origin":   req.origin,
        "cta":      req.cta,
    }
    assets = {
        "bgm_preset":   req.bgm,
        "gemini_voice": req.voice,
        "bg_images":    [],       # 기본 배경 이미지 사용
        "is_test":      True,     # ← bypass 플래그
    }

    logger.info(f"[HealthCheck] 테스트 렌더링 시작: {job_id}")

    try:
        from media_worker.tasks.video_tasks import generate_premium_shortform
        task = generate_premium_shortform.apply_async(
            args=[job_id, merchant_facts, assets],
            task_id=job_id,
            queue="video_tasks",
        )
        return {
            "task_id":  task.id,
            "job_id":   job_id,
            "status":   "PENDING",
            "is_test":  True,
            "message":  "테스트 렌더링 대기 중... (크레딧 차감 없음)",
        }
    except Exception as e:
        # Celery 없을 때 — 워커 미연결 상태 명시
        logger.warning(f"[HealthCheck] Celery 연결 실패: {e}")
        raise HTTPException(503,
            f"GPU 워커가 연결되어 있지 않습니다. SSH 터널을 확인하세요. ({type(e).__name__})")


@router.get("/healthcheck/render/{task_id}")
async def poll_test_render(
    task_id: str,
    admin:   dict = Depends(verify_admin_jwt),
):
    """
    모듈4: 테스트 렌더링 상태 폴링.
    Celery AsyncResult로 실시간 진행률 반환.
    SUCCESS 시 video_url 포함 (관리자 화면에서 직접 재생).
    """
    try:
        from celery.result import AsyncResult
        from media_worker.celery_app import app as celery_app

        result = AsyncResult(task_id, app=celery_app)
        state  = result.state

        if state == "PENDING":
            return {"state": "PENDING", "percent": 5,  "message": "⏳ 대기 중..."}

        if state == "PROGRESS":
            meta = result.info or {}
            return {
                "state":   "PROGRESS",
                "percent": meta.get("percent", 10),
                "message": meta.get("message", "렌더링 중..."),
                "step":    meta.get("step", 0),
                "total":   meta.get("total", 4),
            }

        if state == "SUCCESS":
            info = result.result or {}
            video_url = info.get("download_url") or f"/static/output/{task_id}.mp4"
            return {
                "state":        "SUCCESS",
                "percent":      100,
                "message":      "✅ 테스트 렌더링 완료!",
                "video_url":    video_url,
                "duration_sec": info.get("duration_sec", 0),
                "file_size_mb": info.get("file_size_mb", 0),
                "render_time":  info.get("render_time_sec", 0),
                "encoder":      info.get("encoder", "libx264"),
                "is_test":      True,
            }

        if state == "FAILURE":
            err = str(result.result) if result.result else "알 수 없는 오류"
            return {
                "state":   "FAILURE",
                "percent": 0,
                "message": f"❌ 렌더링 실패: {err[:200]}",
            }

        return {"state": state, "percent": 0, "message": "처리 중..."}

    except Exception as e:
        raise HTTPException(500, f"상태 조회 실패: {e}")


@router.get("/healthcheck/systems")
async def system_health(admin: dict = Depends(verify_admin_jwt)):
    """전체 시스템 헬스 체크 — Redis, Celery, FFmpeg, 출력 디렉터리."""
    checks: dict[str, dict] = {}

    # 1. Redis
    try:
        rdb = _rdb()
        rdb.ping()
        checks["redis"] = {"ok": True, "msg": "Connected"}
    except Exception as e:
        checks["redis"] = {"ok": False, "msg": str(e)}

    # 2. Celery 워커
    try:
        from media_worker.celery_app import app as celery_app
        pong = celery_app.control.inspect(timeout=1.5).ping() or {}
        if pong:
            checks["celery_worker"] = {"ok": True, "msg": f"Workers: {list(pong.keys())}"}
        else:
            checks["celery_worker"] = {"ok": False, "msg": "No workers online"}
    except Exception as e:
        checks["celery_worker"] = {"ok": False, "msg": str(e)}

    # 3. FFmpeg (서버 로컬)
    try:
        import subprocess
        out = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=3)
        ver = out.stdout.decode()[:50] if out.returncode == 0 else "not found"
        checks["ffmpeg"] = {"ok": out.returncode == 0, "msg": ver.strip()}
    except Exception as e:
        checks["ffmpeg"] = {"ok": False, "msg": str(e)}

    # 4. 출력 디렉터리
    try:
        import os as _os, glob as _glob
        out_dir = _os.environ.get("SHORTFORM_OUTPUT_DIR", "/var/www/dnbsir/static/output")
        exists  = _os.path.isdir(out_dir)
        files   = len(_glob.glob(_os.path.join(out_dir, "*.mp4"))) if exists else -1
        checks["output_dir"] = {"ok": exists,
                                "msg": f"{files}개 MP4, 경로: {out_dir}"}
    except Exception as e:
        checks["output_dir"] = {"ok": False, "msg": str(e)}

    overall = all(v["ok"] for v in checks.values())
    return {
        "overall": "healthy" if overall else "degraded",
        "checks":  checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 모듈 5: 배치 스케줄러 컨트롤러
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import pytz as _pytz
_KST = _pytz.timezone("Asia/Seoul")

def _kst_now():
    from datetime import datetime
    return datetime.now(_KST)

def _elapsed_days(created_iso: str) -> int:
    """ISO 타임스탬프 → 경과 일수 계산."""
    try:
        from datetime import datetime, timezone
        created = datetime.fromisoformat(created_iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - created).days
    except Exception:
        return 0

def _elapsed_badge(days: int) -> str:
    if days == 0:   return "당일 접수"
    if days == 1:   return "1일째 대기 중"
    return f"{days}일째 대기 중"

def _urgency(days: int) -> str:
    if days >= 4:   return "urgent"   # 🔴
    if days >= 2:   return "warning"  # 🟠
    return "normal"                   # 🟢


@router.get("/batch/status")
async def batch_status(_: str = Depends(verify_admin_jwt)):
    """배치 스케줄러 현재 상태 조회."""
    rdb = _rdb()
    now_kst = _kst_now()

    maintenance   = rdb.get("tantan:maintenance:active") == "1"
    batch_running = rdb.get("tantan:batch:running") == "1"
    soft_shutdown = rdb.get("tantan:batch:soft_shutdown") == "1"
    count_today   = int(rdb.get("tantan:batch:count_today") or 0)
    pending_count = rdb.zcard("tantan:orders:pending_index")

    # 다음 배치 시작까지 남은 시간 계산 (KST 00:10 기준)
    from datetime import datetime as _dt
    next_batch = now_kst.replace(hour=0, minute=10, second=0, microsecond=0)
    if now_kst >= next_batch:
        import datetime as _datetime_mod
        next_batch += _datetime_mod.timedelta(days=1)
    eta_seconds = int((next_batch - now_kst).total_seconds())
    eta_str = f"{eta_seconds // 3600}시간 {(eta_seconds % 3600) // 60}분"

    return {
        "maintenance":    maintenance,
        "batch_running":  batch_running,
        "soft_shutdown":  soft_shutdown,
        "count_today":    count_today,
        "pending_count":  pending_count,
        "batch_limit":    35,
        "server_time_kst": now_kst.strftime("%H:%M:%S"),
        "next_batch_eta": eta_str,
        "schedule": {
            "maintenance_on":  "00:00 KST",
            "batch_start":     "00:10 KST",
            "soft_shutdown":   "06:30 KST",
            "maintenance_off": "07:00 KST",
        }
    }


class MaintenanceBody(BaseModel):
    active: bool = Field(..., description="True=점검 ON, False=점검 OFF")

@router.post("/maintenance")
async def toggle_maintenance(
    body: MaintenanceBody,
    _: str = Depends(verify_admin_jwt),
):
    """점검 모드 수동 토글 (관리자 긴급 제어용)."""
    rdb = _rdb()
    if body.active:
        rdb.set("tantan:maintenance:active", "1")
        msg = "점검 모드 ON — kiosk.html 접속 차단됨"
    else:
        rdb.delete("tantan:maintenance:active")
        msg = "점검 모드 OFF — 정상 운영 복귀"
    logger.info(f"[Admin] 수동 {msg}")
    return {"ok": True, "maintenance": body.active, "message": msg}


@router.post("/batch/start")
async def manual_batch_start(_: str = Depends(verify_admin_jwt)):
    """수동으로 배치 렌더링 즉시 시작 (테스트/긴급 처리용)."""
    try:
        from routers.batch_scheduler import start_batch_render
        import asyncio
        asyncio.create_task(start_batch_render())
        return {"ok": True, "message": "배치 렌더링 시작 요청됨"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/stop")
async def manual_soft_shutdown(_: str = Depends(verify_admin_jwt)):
    """수동 Soft Shutdown — 신규 enqueue 즉시 차단."""
    rdb = _rdb()
    rdb.set("tantan:batch:soft_shutdown", "1")
    count = int(rdb.get("tantan:batch:count_today") or 0)
    return {
        "ok": True,
        "message": f"Soft Shutdown 활성화 — 오늘 처리 {count}건, 신규 enqueue 차단됨"
    }


@router.get("/queue/pending")
async def pending_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: str = Depends(verify_admin_jwt),
):
    """PENDING_BATCH 대기 주문 목록 (경과일 표시, 페이지네이션)."""
    rdb = _rdb()

    total = rdb.zcard("tantan:orders:pending_index")
    offset = (page - 1) * page_size

    # ZSortedSet: score=접수시각(오름차순) → 오래된 건 먼저
    job_ids = rdb.zrange("tantan:orders:pending_index", offset, offset + page_size - 1,
                          withscores=True)

    items = []
    for job_id, score in job_ids:
        raw = rdb.get(f"tantan:order:{job_id}")
        if not raw:
            continue
        order = json.loads(raw)
        days  = _elapsed_days(order.get("created_at", ""))
        phone = order.get("phone", "")
        # 전화번호 마스킹 (앞 3자리 + **** + 뒤 4자리)
        masked = phone[:3] + "****" + phone[-4:] if len(phone) >= 7 else "****"
        facts  = order.get("merchant_facts", {})

        items.append({
            "job_id":       job_id,
            "phone_masked": masked,
            "product":      facts.get("product", "알 수 없음")[:20],
            "batch_status": order.get("batch_status", "UNKNOWN"),
            "created_at":   order.get("created_at", ""),
            "elapsed_days": days,
            "elapsed_label": _elapsed_badge(days),
            "urgency":      _urgency(days),
        })

    return {
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "pages":     math.ceil(total / page_size) if total else 1,
        "items":     items,
    }
