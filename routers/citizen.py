from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
import os
import db_manager as db

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
API_URL = os.environ.get("API_URL", "https://dnbsir-api-ap33e42daq-uc.a.run.app")

class CourierReservationRequest(BaseModel):
    sender_name: str
    sender_phone: str
    sender_addr: str
    receiver_name: str
    receiver_phone: str
    receiver_addr: str
    item_type: str
    weight: str = "small"
    quantity: int = 1
    payment_method: str

@router.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "api_url": API_URL})

@router.get("/citizen/courier", response_class=HTMLResponse)
async def public_courier_page(request: Request):
    toss_client_key = os.getenv("TOSS_CLIENT_KEY", "")
    return templates.TemplateResponse("citizen_courier.html", {
        "request": request, 
        "api_url": API_URL,
        "toss_client_key": toss_client_key,
        "store": {} 
    })
    
@router.post("/api/citizen/courier/reserve")
async def public_reserve_courier(data: CourierReservationRequest, request: Request):
    store_id = "CITIZEN" 
    
    base_fee = 6000
    if data.weight == "medium":
        base_fee = 7000
    elif data.weight == "large":
        base_fee = 9000
    
    total_fee = base_fee * data.quantity

    delivery_data = {
        "store_id": store_id,
        "date_time": datetime.now().isoformat(),
        "sender_name": data.sender_name,
        "receiver_name": data.receiver_name,
        "receiver_addr": data.receiver_addr,
        "item_type": data.item_type,
        "weight": data.weight,
        "quantity": data.quantity,
        "tracking_code": f"LOGEN-{int(datetime.now().timestamp())}", 
        "fee": total_fee, 
        "status": "접수완료"
    }
    
    try:
        from fastapi.concurrency import run_in_threadpool
        if hasattr(db, 'save_store_delivery'):
             await run_in_threadpool(db.save_store_delivery, delivery_data)
        else:
             await run_in_threadpool(db.save_delivery, delivery_data)
        
        return {
            "success": True, 
            "tracking_code": delivery_data["tracking_code"],
            "amount": total_fee,
            "orderName": f"택배 {data.quantity}건 ({data.item_type})"
        }
    except Exception as e:
        print(f"[X] Public Courier Reservation Failed: {e}")
        raise HTTPException(status_code=500, detail="예약 저장 실패")

@router.get("/citizen/market", response_class=HTMLResponse)
async def public_market_page(request: Request):
    products = db.get_all_products()
    return templates.TemplateResponse("market.html", {"request": request, "products": products, "api_url": API_URL})
