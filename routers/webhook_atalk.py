from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from comm_middleware import CommMiddleware

router = APIRouter()

class AtalkWebhookPayload(BaseModel):
    caller_phone: str
    virtual_number: str
    status: str # 'busy', 'no_answer', etc.
    store_id: Optional[str] = None

@router.post("/webhook/atalk")
async def receive_atalk_webhook(payload: AtalkWebhookPayload, background_tasks: BackgroundTasks):
    """
    아톡비즈 Webhook 수신 엔드포인트.
    US-KR 지연시간 최소화를 위해 1초 이내에 HTTP 200 OK를 리턴하고,
    실제 콜백 발송 처리는 백그라운드 태스크로 넘겨버립니다.
    """
    if payload.status not in ["busy", "no_answer"]:
        return {"status": "ignored", "reason": "콜백 발송 조건이 아님"}

    # 미들웨어의 콜백 처리 메서드를 Background로 던짐
    background_tasks.add_task(
        CommMiddleware.dispatch_callback_message,
        payload.store_id,
        payload.virtual_number,
        payload.caller_phone,
        payload.status
    )

    return {"status": "accepted", "message": "1초 내 콜백 발송 파이프라인 진입 완료"}
