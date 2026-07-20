"""
로젠 FastAPI 마이크로서비스 - 프로덕션 강화 버전
✅ asyncio.Queue로 순차 처리 (동시성 제어)
✅ 동시 실행 중 새 요청은 큐에서 대기
✅ 브라우저 좀비 프로세스 차단
✅ 각 요청에 고유 ID 부여 (추적 가능)
"""
import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/var/playwright"

# ── 큐 기반 순차 처리 ─────────────────────────────────────
# 동시에 여러 주문이 들어와도 브라우저는 1개씩만 실행
# → 로젠 서버 IP 차단 방지 + 메모리 안전
MAX_QUEUE_SIZE = 50       # 최대 대기 주문 수
QUEUE_TIMEOUT = 300       # 큐 대기 최대 5분

_queue: asyncio.Queue = None
_worker_task: asyncio.Task = None


async def _worker():
    """큐에서 주문을 꺼내 순차적으로 처리하는 워커"""
    logger.info("[큐워커] 시작")
    while True:
        req_id, order, future = await _queue.get()
        logger.info(f"[큐워커] 처리 시작: {req_id} (대기 잔여: {_queue.qsize()})")
        try:
            from logen_web_automation import create_logen_waybill
            result = await create_logen_waybill(order)
            future.set_result(result)
        except Exception as e:
            logger.error(f"[큐워커] 오류 {req_id}: {e}")
            future.set_exception(e)
        finally:
            _queue.task_done()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _queue, _worker_task
    _queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
    _worker_task = asyncio.create_task(_worker())
    logger.info("[서비스] 로젠 웨이빌 서비스 시작")
    yield
    _worker_task.cancel()
    try: await _worker_task
    except asyncio.CancelledError: pass
    logger.info("[서비스] 종료")


app = FastAPI(
    title="로젠 택배 자동화 서비스",
    version="2.0",
    lifespan=lifespan
)


class OrderRequest(BaseModel):
    receiver_name: str
    receiver_phone: str
    receiver_addr1: str
    receiver_addr2: Optional[str] = ""
    receiver_zipcode: str
    item_name: Optional[str] = "일반상품"
    item_qty: Optional[int] = 1
    item_weight: Optional[int] = 3
    item_price: Optional[int] = 30000
    message: Optional[str] = ""


class WaybillResponse(BaseModel):
    success: bool
    slip_no: Optional[str] = None
    seq: Optional[str] = None
    pickup_dt: Optional[str] = None
    delivery_dt: Optional[str] = None
    error: Optional[str] = None
    request_id: Optional[str] = None
    queue_position: Optional[int] = None


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "logen-waybill",
        "queue_size": _queue.qsize() if _queue else 0,
        "worker_alive": _worker_task and not _worker_task.done() if _worker_task else False
    }


@app.post("/waybill/create", response_model=WaybillResponse)
async def create_waybill(order: OrderRequest):
    """
    로젠 TMS에 운송장 등록

    - 큐에 담아 순차 처리 (동시성 제어)
    - 큐가 꽉 찬 경우 429 반환
    - 최대 대기 시간: 5분
    """
    req_id = str(uuid.uuid4())[:8]
    q_pos = _queue.qsize() + 1

    logger.info(f"[요청 {req_id}] 수하인: {order.receiver_name}, 큐위치: {q_pos}")

    if _queue.full():
        logger.warning(f"[요청 {req_id}] 큐 포화 (현재 {_queue.qsize()}건)")
        raise HTTPException(
            status_code=429,
            detail=f"서버 처리 큐가 포화 상태입니다 ({MAX_QUEUE_SIZE}건). 잠시 후 재시도하세요."
        )

    loop = asyncio.get_event_loop()
    future = loop.create_future()

    await _queue.put((req_id, order.model_dump(), future))
    logger.info(f"[요청 {req_id}] 큐 등록 완료 (위치: {q_pos})")

    try:
        result = await asyncio.wait_for(future, timeout=QUEUE_TIMEOUT)
        result["request_id"] = req_id
        result["queue_position"] = q_pos
        return WaybillResponse(**result)
    except asyncio.TimeoutError:
        logger.error(f"[요청 {req_id}] 큐 대기 타임아웃 ({QUEUE_TIMEOUT}초)")
        raise HTTPException(
            status_code=504,
            detail=f"처리 타임아웃 ({QUEUE_TIMEOUT}초). 주문은 접수되었을 수 있으니 로젠 TMS를 확인하세요."
        )


@app.get("/queue/status")
async def queue_status():
    """현재 큐 상태 조회"""
    return {
        "queue_size": _queue.qsize() if _queue else 0,
        "max_queue_size": MAX_QUEUE_SIZE,
        "worker_alive": _worker_task and not _worker_task.done() if _worker_task else False
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"[서비스] 처리되지 않은 예외: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("logen_service:app", host="0.0.0.0", port=8001, reload=False, workers=1)
