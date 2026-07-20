from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
import db_manager as db

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

@router.get("/check")
async def check_inventory(
    store_id: str = Query(..., description="매장 고유 ID"),
    resource_id: str = Query(..., description="예약 대상 ID (객실번호, 테이블번호 등)"),
    check_in: str = Query(..., description="시작 일시 (또는 날짜)"),
    check_out: str = Query(..., description="종료 일시 (또는 날짜)")
):
    # 1. 입력 검증 (store_id 존재 여부)
    store = await run_in_threadpool(db.get_store, store_id)
    if not store:
        return {
            "status": "success",
            "data": {
                "is_available": False,
                "resource_id": resource_id,
                "reason": "Store not found"
            }
        }

    # 2. resource_id 검증 (비어있는지 확인)
    if not resource_id or not resource_id.strip():
        return {
            "status": "success",
            "data": {
                "is_available": False,
                "resource_id": resource_id,
                "reason": "Invalid resource_id"
            }
        }

    # 3. 실시간 예약 중복 조회
    try:
        is_available = await run_in_threadpool(
            db.check_room_availability,
            store_id,
            resource_id,
            check_in,
            check_out
        )
        
        reason = "Available" if is_available else "Already reserved"
        
        return {
            "status": "success",
            "data": {
                "is_available": is_available,
                "resource_id": resource_id,
                "reason": reason
            }
        }
    except Exception as e:
        print(f"[API check_inventory] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
