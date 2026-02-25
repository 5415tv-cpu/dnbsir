from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
import db_manager as db
from .auth import get_current_user, User

router = APIRouter()

class CourierReservationRequest(BaseModel):
    sender_name: str
    sender_phone: str
    sender_addr1: str
    sender_addr2: str
    receiver_name: str
    receiver_phone: str
    receiver_addr1: str
    receiver_addr2: str
    quantity: int
    item_type: str
    item_value: int
    pickup_date: str
    payment_type: str

@router.post("/api/courier/reserve")
async def reserve_courier(data: CourierReservationRequest, request: Request, user: User = Depends(get_current_user)):
    store_id = user.store_id
    print(f"📦 [Courier] Reservation Request from {store_id}: {data}")

    delivery_data = {
        "store_id": store_id,
        "date_time": datetime.now().isoformat(),
        "sender_name": data.sender_name,
        "receiver_name": data.receiver_name,
        "receiver_addr": f"{data.receiver_addr1} {data.receiver_addr2}",
        "item_type": data.item_type,
        "tracking_code": f"LOGEN-{int(datetime.now().timestamp())}", 
        "fee": 3000 * data.quantity, 
        "status": "접수완료"
    }
    
    try:
        from fastapi.concurrency import run_in_threadpool
        if hasattr(db, 'save_store_delivery'):
             await run_in_threadpool(db.save_store_delivery, delivery_data)
        else:
             await run_in_threadpool(db.save_delivery, delivery_data)
        
        print(f"✅ Logen API Call: Reserve {delivery_data['tracking_code']}")
        
        return {"success": True, "tracking_code": delivery_data["tracking_code"]}
    except Exception as e:
        print(f"❌ Courier Reservation Failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="예약 저장 실패")
