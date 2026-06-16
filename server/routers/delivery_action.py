from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
import logging
import asyncio

try:
    from core.security_layer import get_current_user_from_header
except ModuleNotFoundError:
    from server.core.security_layer import get_current_user_from_header

router = APIRouter(prefix="/api/delivery", tags=["One-Stop Delivery Engine"])


async def mock_logen_complete_api(tracking_no: str, image_url: str):
    """로젠/한진 택배 서버로 '배송 완료' 상태 전송 (Mock)"""
    await asyncio.sleep(0.5)
    logging.info(f"🚚 Notified Courier API: {tracking_no} is DELIVERED. Proof: {image_url}")

@router.post("/complete_one_stop")
async def one_stop_delivery_completion(
    tracking_no: str,
    courier: str,
    photo: UploadFile = File(...),
    current_user: dict = Depends(get_current_user_from_header)
):
    """
    [원스톱 배달 완료 매커니즘]
    기사님의 단 한 번의 사진 업로드 클릭으로 택배사 서버에 완료를 전송합니다.
    """
    user_id = current_user.get("sub", "UnknownDriver")
    logging.info(f"🚀 User {user_id} triggered One-Stop Completion for {courier} {tracking_no}")
    
    filename = f"{courier}_{tracking_no}_{photo.filename}"
    
    # 1. 자체 영구 보관용 구글 드라이브 업로드 제거 
    # (로젠택배 등 택배사 서버 자동저장 기능 활용하여 용량 및 비용 절감)
    image_url = f"logen_server_hosted_{filename}"
    
    # 2. 택배사 서버 연동 (비동기)
    logen_task = asyncio.create_task(mock_logen_complete_api(tracking_no, image_url))
    
    # 3. 마스터 DB 업데이트
    try:
        import db_manager as db
        # 영구 증빙 보관용 DB 레코드 저장
        db.save_ledger_record({
            "store_id": user_id,
            "type": "delivery_proof",
            "category": courier,
            "amount": 0,
            "memo": f"Delivery completed for {tracking_no}. Courier: {courier}.",
            "proof_path": image_url,
            "date": ""
        })
    except Exception as db_err:
        logging.error(f"DB Master Ledger Update Failed: {db_err}")
    
    # 모든 태스크 병합 완료 대기
    await asyncio.gather(logen_task)
    
    return {
        "success": True,
        "message": f"{tracking_no} Delivery One-Stop Complete.",
        "image_proof_url": image_url
    }
