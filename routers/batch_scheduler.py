"""
심야 배치 스케줄러 (Nightly Batch Processor)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KST 기준 4단계 Staggered Scheduling:
  00:00 → 점검 모드 진입 (kiosk 차단)
  00:10 → 배치 렌더링 시작 (최대 35건)
  06:30 → Soft Shutdown (신규 enqueue 차단)
  07:00 → 정상 운영 복귀

★ 이중 저장 아키텍처 (v2 — PostgreSQL ORM 연동)
  Redis  : 대기열 순서 + 락 + 실시간 플래그 (빠른 읽기/쓰기)
  PostgreSQL : 주문 상태 영속 보존 (서버 재시작 후에도 안전)

Redis 키 구조:
  tantan:maintenance:active    = "1"           (점검 중 플래그)
  tantan:batch:running         = "1"           (배치 가동 중)
  tantan:batch:soft_shutdown   = "1"           (신규 차단 중)
  tantan:batch:count_today     = N             (오늘 처리 건수)
  tantan:orders:pending_index  = SortedSet     (score=접수시각, member=job_id)
"""

from __future__ import annotations
import json, logging, os, time
from datetime import datetime, timezone, timedelta, date

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("tantan.batch")

KST = pytz.timezone("Asia/Seoul")

# ── 배치 상수 ────────────────────────────────────────────────────
BATCH_LIMIT           = 35          # 하룻밤 최대 처리 건수 (RTX 4070 안전 상한)
JOB_TIMEOUT_SEC       = 600         # 1건 최대 10분 (Veo + FFmpeg)
ORDER_TTL_DAYS        = 10          # 완료 주문 보존 기간 (제작 7일 + 여유 3일)
VIDEO_EXPIRE_DAYS     = 10          # 영상 파일 만료 기간
ADMIN_ALERT_PHONE_ENV = "ADMIN_ALERT_PHONE"

scheduler = AsyncIOScheduler(timezone=KST)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 헬퍼: Redis / DB 세션
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _rdb():
    import redis as _redis
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/1")
    return _redis.from_url(url, decode_responses=True)


def _db_session():
    """PostgreSQL ORM 세션 반환. 호출자가 직접 close() 해야 함."""
    from tantan_database import SessionLocal
    return SessionLocal()


def _now_kst() -> datetime:
    return datetime.now(KST)


def _ts() -> float:
    return time.time()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 유틸: 관리자 SMS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _send_admin_sms(msg: str):
    """관리자 전화번호로 Solapi SMS 발송."""
    try:
        admin_phone = os.environ.get(ADMIN_ALERT_PHONE_ENV, "")
        if not admin_phone:
            return
        from routers.tantan_payment import _send_sms
        _send_sms(admin_phone, msg)
    except Exception as e:
        logger.warning(f"관리자 SMS 발송 실패: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 스케줄 함수 4개 (KST 기준)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def enter_maintenance():
    """
    KST 00:00 — 점검 모드 진입
    - Redis 플래그 ON → kiosk.html 차단
    - 관리자 SMS 발송
    """
    rdb = _rdb()
    now = _now_kst()
    logger.info(f"[Batch] 점검 모드 진입 KST {now.strftime('%H:%M:%S')}")

    rdb.set("tantan:maintenance:active",  "1")
    rdb.set("tantan:batch:running",       "0")
    rdb.set("tantan:batch:soft_shutdown", "0")
    rdb.set("tantan:batch:count_today",   "0")

    # PostgreSQL에서 실제 PENDING_BATCH 건수 조회 (Redis보다 신뢰도 높음)
    pending = 0
    try:
        from tantan_models import TantanOrder
        db = _db_session()
        pending = db.query(TantanOrder).filter_by(batch_status="PENDING_BATCH").count()
        db.close()
    except Exception as e:
        logger.warning(f"[Batch] DB 조회 실패, Redis fallback: {e}")
        pending = rdb.zcard("tantan:orders:pending_index")

    _send_admin_sms(
        f"[탄탄제작소] 야간 배치 점검 모드 진입\n"
        f"대기 주문: {pending}건 | 배치 시작: 00:10 KST"
    )


async def start_batch_render():
    """
    KST 00:10 — 배치 렌더링 시작 (10분 Stagger)
    - PostgreSQL에서 PENDING_BATCH 주문을 오래된 순으로 최대 35건 조회
    - 각 주문을 PROCESSING으로 업데이트 후 Celery enqueue
    - Redis 큐와 DB 상태를 동시에 업데이트 (이중 저장)
    """
    rdb = _rdb()
    now = _now_kst()

    if rdb.get("tantan:batch:soft_shutdown") == "1":
        logger.warning("[Batch] Soft Shutdown 상태 — 배치 시작 스킵")
        return

    rdb.set("tantan:batch:running", "1")
    logger.info(f"[Batch] 렌더링 배치 시작 KST {now.strftime('%H:%M:%S')}")

    today = now.date()
    dispatched = 0

    try:
        from tantan_models import TantanOrder
        from sqlalchemy import func as sa_func
        db = _db_session()

        # ── 오래된 순 + 테스트 제외 우선, BATCH_LIMIT 건 ──────
        pending_orders = (
            db.query(TantanOrder)
            .filter(TantanOrder.batch_status == "PENDING_BATCH")
            .order_by(TantanOrder.is_test.asc(), TantanOrder.created_at.asc())
            .limit(BATCH_LIMIT)
            .all()
        )

        for order in pending_orders:
            # Soft Shutdown 루프 중 재확인
            if rdb.get("tantan:batch:soft_shutdown") == "1":
                logger.info(f"[Batch] Soft Shutdown 감지 — {dispatched}건 투입 후 중단")
                break

            job_id = order.job_id

            # ── DB 상태 → PROCESSING ───────────────────────────
            order.batch_status      = "PROCESSING"
            order.render_started_at = datetime.now(timezone.utc)
            order.batch_date        = today
            db.commit()

            # ── Redis 상태도 동기화 ────────────────────────────
            raw = rdb.get(f"tantan:order:{job_id}")
            if raw:
                redis_order = json.loads(raw)
                redis_order["batch_status"]      = "PROCESSING"
                redis_order["render_started_at"] = order.render_started_at.isoformat()
                rdb.setex(
                    f"tantan:order:{job_id}",
                    ORDER_TTL_DAYS * 86400,
                    json.dumps(redis_order)
                )

            # ── Celery enqueue ─────────────────────────────────
            try:
                from media_worker.tasks.video_tasks import generate_premium_shortform
                generate_premium_shortform.apply_async(
                    args=[job_id,
                          order.merchant_facts,
                          order.assets],
                    task_id=job_id,
                    queue="video_tasks",
                    time_limit=JOB_TIMEOUT_SEC,
                    soft_time_limit=JOB_TIMEOUT_SEC - 60,
                )
                dispatched += 1
                rdb.incr("tantan:batch:count_today")
                logger.info(f"[Batch] enqueue: {job_id} ({dispatched}/{len(pending_orders)})")

            except Exception as e:
                # enqueue 실패 → DB 롤백 (PENDING_BATCH 복원)
                logger.error(f"[Batch] enqueue 실패 {job_id}: {e}")
                order.batch_status      = "PENDING_BATCH"
                order.render_started_at = None
                order.batch_date        = None
                db.commit()

        db.close()

    except Exception as e:
        logger.error(f"[Batch] DB 처리 오류: {e}", exc_info=True)

    logger.info(f"[Batch] 배치 완료: {dispatched}건 투입")


async def soft_shutdown():
    """
    KST 06:30 — Soft Shutdown
    - 신규 enqueue 차단 플래그 ON
    - 진행 중인 작업은 완료 허용
    """
    rdb = _rdb()
    now = _now_kst()
    logger.info(f"[Batch] Soft Shutdown KST {now.strftime('%H:%M:%S')}")

    rdb.set("tantan:batch:soft_shutdown", "1")

    count = int(rdb.get("tantan:batch:count_today") or 0)

    # DB에서 정확한 미완료 건수 조회
    remaining = 0
    try:
        from tantan_models import TantanOrder
        db = _db_session()
        remaining = db.query(TantanOrder).filter(
            TantanOrder.batch_status.in_(["PENDING_BATCH", "PROCESSING"])
        ).count()
        db.close()
    except Exception as e:
        logger.warning(f"[Batch] DB 조회 실패: {e}")
        remaining = rdb.zcard("tantan:orders:pending_index")

    _send_admin_sms(
        f"[탄탄제작소] 야간 배치 Soft Shutdown\n"
        f"처리 완료: {count}건 | 미완료 대기: {remaining}건\n"
        f"07:00 정상 운영 복귀"
    )


async def exit_maintenance():
    """
    KST 07:00 — 정상 운영 복귀
    - 모든 배치 플래그 초기화
    - kiosk.html 차단 해제
    - 미완료 PROCESSING 건 → PENDING_BATCH 복원 (DB + Redis 동시)
    """
    rdb = _rdb()
    now = _now_kst()
    logger.info(f"[Batch] 정상 운영 복귀 KST {now.strftime('%H:%M:%S')}")

    # 점검/배치 플래그 해제
    rdb.delete("tantan:maintenance:active")
    rdb.set("tantan:batch:running",       "0")
    rdb.set("tantan:batch:soft_shutdown", "0")

    # ── DB: 미완료 PROCESSING → PENDING_BATCH 복원 ────────────
    recovered = 0
    try:
        from tantan_models import TantanOrder
        db = _db_session()

        stale = db.query(TantanOrder).filter_by(batch_status="PROCESSING").all()
        for order in stale:
            order.batch_status      = "PENDING_BATCH"
            order.render_started_at = None
            order.retry_count       = (order.retry_count or 0) + 1
            recovered += 1

            # Redis도 동기화
            raw = rdb.get(f"tantan:order:{order.job_id}")
            if raw:
                ro = json.loads(raw)
                ro["batch_status"]      = "PENDING_BATCH"
                ro["render_started_at"] = None
                rdb.setex(
                    f"tantan:order:{order.job_id}",
                    ORDER_TTL_DAYS * 86400,
                    json.dumps(ro)
                )

        db.commit()
        db.close()
        logger.info(f"[Batch] 미완료 복원: {recovered}건 → PENDING_BATCH (retry_count+1)")

    except Exception as e:
        logger.error(f"[Batch] 복원 중 DB 오류: {e}", exc_info=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 스케줄 등록
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def register_jobs():
    """app.py startup에서 호출 — KST 기준 4개 스케줄 등록."""

    scheduler.add_job(
        enter_maintenance,
        CronTrigger(hour=0, minute=0, timezone=KST),
        id="batch_maintenance_on",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        start_batch_render,
        CronTrigger(hour=0, minute=10, timezone=KST),
        id="batch_render_start",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        soft_shutdown,
        CronTrigger(hour=6, minute=30, timezone=KST),
        id="batch_soft_shutdown",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        exit_maintenance,
        CronTrigger(hour=7, minute=0, timezone=KST),
        id="batch_maintenance_off",
        replace_existing=True,
        misfire_grace_time=300,
    )

    logger.info(
        "[Batch] 스케줄 등록 완료 (KST): "
        "00:00 점검ON → 00:10 배치시작 → 06:30 SoftShutdown → 07:00 점검OFF"
    )


def start():
    register_jobs()
    scheduler.start()
    logger.info("[Batch] APScheduler 시작 (Asia/Seoul)")


def stop():
    scheduler.shutdown(wait=False)
    logger.info("[Batch] APScheduler 종료")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 주문 등록 헬퍼 (video_shortform.py에서 호출)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def register_pending_order(
    job_id: str,
    phone: str,
    merchant_facts: dict,
    assets: dict,
    is_test: bool = False,
):
    """
    결제 완료 주문을 PENDING_BATCH로 등록.
    ★ PostgreSQL(영속) + Redis(큐) 이중 저장.
    """
    rdb = _rdb()
    ts  = _ts()
    now_utc = datetime.fromtimestamp(ts, tz=timezone.utc)

    # ── 1. PostgreSQL에 영속 저장 ──────────────────────────────
    try:
        from tantan_models import TantanOrder
        from tantan_database import SessionLocal
        db = SessionLocal()
        new_order = TantanOrder(
            job_id         = job_id,
            phone          = phone,
            batch_status   = "PENDING_BATCH",
            merchant_facts = merchant_facts,
            assets         = assets,
            is_test        = is_test,
        )
        db.merge(new_order)   # upsert — 재시도 시 중복 방지
        db.commit()
        db.close()
        logger.info(f"[Batch] DB 주문 등록: {job_id}")
    except Exception as e:
        logger.error(f"[Batch] DB 등록 실패 {job_id}: {e}", exc_info=True)
        # DB 실패해도 Redis에는 등록 시도 (서비스 연속성 우선)

    # ── 2. Redis에 큐 등록 (순서 관리용) ──────────────────────
    order_data = {
        "job_id":              job_id,
        "phone":               phone,
        "merchant_facts":      merchant_facts,
        "assets":              assets,
        "batch_status":        "PENDING_BATCH",
        "is_test":             is_test,
        "created_at":          now_utc.isoformat(),
        "render_started_at":   None,
        "render_completed_at": None,
        "video_url":           None,
    }
    rdb.setex(f"tantan:order:{job_id}", ORDER_TTL_DAYS * 86400, json.dumps(order_data))
    rdb.zadd("tantan:orders:pending_index", {job_id: ts})

    queue_pos = rdb.zrank("tantan:orders:pending_index", job_id) or 0
    logger.info(f"[Batch] 주문 등록: {job_id} | 대기 {queue_pos + 1}번째")
    return order_data


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 완료 처리 헬퍼 (video_tasks.py에서 호출)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def complete_order(job_id: str, video_url: str):
    """
    렌더링 완료 후 DONE 상태로 업데이트.
    ★ PostgreSQL(영속) + Redis(큐 제거) 동시 처리.
    """
    rdb     = _rdb()
    now_utc = datetime.now(timezone.utc)
    expires = now_utc + timedelta(days=VIDEO_EXPIRE_DAYS)

    # ── 1. PostgreSQL DONE 업데이트 ────────────────────────────
    try:
        from tantan_models import TantanOrder
        db = _db_session()
        order = db.query(TantanOrder).filter_by(job_id=job_id).first()
        if order:
            order.batch_status          = "DONE"
            order.video_url             = video_url
            order.render_completed_at   = now_utc
            order.video_expires_at      = expires
            db.commit()
        db.close()
        logger.info(f"[Batch] DB DONE: {job_id}")
    except Exception as e:
        logger.error(f"[Batch] DB 완료 처리 실패 {job_id}: {e}", exc_info=True)

    # ── 2. Redis 업데이트 + 대기열 제거 ───────────────────────
    raw = rdb.get(f"tantan:order:{job_id}")
    if raw:
        ro = json.loads(raw)
        ro["batch_status"]          = "DONE"
        ro["video_url"]             = video_url
        ro["render_completed_at"]   = now_utc.isoformat()
        rdb.setex(f"tantan:order:{job_id}", ORDER_TTL_DAYS * 86400, json.dumps(ro))

    rdb.zrem("tantan:orders:pending_index", job_id)
    logger.info(f"[Batch] 완료: {job_id} → {video_url}")


def fail_order(job_id: str, error_msg: str):
    """
    렌더링 실패 처리 — FAILED 상태 + 오류 메시지 기록.
    retry_count < 3이면 PENDING_BATCH로 복원 (자동 재시도).
    """
    rdb = _rdb()

    try:
        from tantan_models import TantanOrder
        db = _db_session()
        order = db.query(TantanOrder).filter_by(job_id=job_id).first()
        if order:
            order.retry_count   = (order.retry_count or 0) + 1
            order.error_message = error_msg[:500]   # 500자 제한

            if order.retry_count < 3:
                # 3회 미만 → 다음 배치에서 재시도
                order.batch_status      = "PENDING_BATCH"
                order.render_started_at = None
                logger.warning(f"[Batch] 재시도 예약: {job_id} (retry={order.retry_count})")
            else:
                # 3회 이상 → FAILED 확정
                order.batch_status = "FAILED"
                logger.error(f"[Batch] 최종 실패: {job_id} (retry={order.retry_count})")

            db.commit()
        db.close()
    except Exception as e:
        logger.error(f"[Batch] fail_order DB 오류 {job_id}: {e}", exc_info=True)
