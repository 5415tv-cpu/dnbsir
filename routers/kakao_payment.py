from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import httpx
import os
import uuid
import db_sqlite

router = APIRouter(prefix="/api/payment/kakao", tags=["kakao-payment"])

# Configuration (fallback to env or use provided)
KAKAO_SECRET_KEY = os.environ.get("KAKAO_SECRET_KEY", "DEVEEA43226CD9AA8EE849370B18B44F50518FAF")
KAKAO_CID = os.environ.get("KAKAO_CID", "58F5919512E3F488A4F9")
BASE_URL = os.environ.get("TANTAN_BASE_URL", "http://localhost:5000") # Replace with actual logic to get base url

@router.post("/ready")
async def kakao_payment_ready(request: Request):
    """
    Step 1: Ready Payment
    """
    try:
        payload = await request.json()
    except:
        payload = {}

    order_id = payload.get("orderId", f"ORDER-{uuid.uuid4().hex[:8].upper()}")
    item_name = payload.get("itemName", "탄탄제작소 상품")
    amount = payload.get("amount", 1000)
    user_id = payload.get("userId", "USER_ID")

    return_url = payload.get("returnUrl", "")
    
    headers = {
        "Authorization": f"SECRET_KEY {KAKAO_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    host_url = str(request.base_url).rstrip('/')
    if "localhost" not in host_url and "127.0.0.1" not in host_url:
        actual_base = host_url
    else:
        actual_base = BASE_URL
        
    import urllib.parse
    encoded_return_url = urllib.parse.quote_plus(return_url) if return_url else ""
    approval_url = f"{actual_base}/api/payment/kakao/approve?order_id={order_id}&return_url={encoded_return_url}"

    data = {
        "cid": KAKAO_CID,
        "partner_order_id": order_id,
        "partner_user_id": user_id,
        "item_name": item_name,
        "quantity": 1,
        "total_amount": int(amount),
        "tax_free_amount": 0,
        "approval_url": approval_url,
        "cancel_url": f"{actual_base}/api/payment/kakao/cancel?order_id={order_id}",
        "fail_url": f"{actual_base}/api/payment/kakao/fail?order_id={order_id}"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post("https://open-api.kakaopay.com/online/v1/payment/ready", json=data, headers=headers)
        res_data = response.json()

        if response.status_code == 200:
            tid = res_data.get("tid")
            next_redirect_pc_url = res_data.get("next_redirect_pc_url")
            
            # Securely save tid mapped to order_id in DB
            db_sqlite.save_payment_tid(order_id, tid, method="KAKAOPAY")
            
            return {
                "orderId": order_id,
                "tid": tid,
                "next_redirect_pc_url": next_redirect_pc_url,
                "next_redirect_mobile_url": res_data.get("next_redirect_mobile_url")
            }
        else:
            print(f"[KakaoPay Ready Error] {res_data}")
            raise HTTPException(status_code=400, detail=res_data.get("msg", "Failed to prepare KakaoPay"))

@router.get("/approve", response_class=HTMLResponse, include_in_schema=False)
async def kakao_payment_approve(request: Request, pg_token: str, order_id: str, return_url: str = ""):
    """
    Step 2: Approve Payment
    """
    # 1. Look up tid securely from DB
    tid = db_sqlite.get_payment_tid(order_id)
    if not tid:
        return RedirectResponse(url="/payment-fail?reason=tid_not_found")
    
    headers = {
        "Authorization": f"SECRET_KEY {KAKAO_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "cid": KAKAO_CID,
        "tid": tid,
        "partner_order_id": order_id,
        "partner_user_id": "USER_ID", # In production, verify user matches ready step
        "pg_token": pg_token
    }

    async with httpx.AsyncClient() as client:
        response = await client.post("https://open-api.kakaopay.com/online/v1/payment/approve", json=data, headers=headers)
        res_data = response.json()
        
        if response.status_code == 200:
            # Payment success -> finalize order in DB
            db_sqlite.update_payment_status(order_id, "APPROVED")
            
            amount = res_data.get('amount', {}).get('total', 0)
            if return_url:
                import urllib.parse
                decoded_return_url = urllib.parse.unquote_plus(return_url)
                separator = "&" if "?" in decoded_return_url else "?"
                return RedirectResponse(url=f"{decoded_return_url}{separator}paymentKey=KAKAOPAY_{tid}&orderId={order_id}&amount={amount}")
            
            # Default fallback
            return RedirectResponse(url=f"/payment-success?orderId={order_id}&amount={amount}")
        else:
            print(f"[KakaoPay Approve Error] {res_data}")
            db_sqlite.update_payment_status(order_id, "FAILED")
            return RedirectResponse(url="/payment-fail?reason=approval_failed")

@router.get("/cancel", response_class=HTMLResponse, include_in_schema=False)
async def kakao_payment_cancel(order_id: str):
    db_sqlite.update_payment_status(order_id, "CANCELLED")
    return RedirectResponse(url="/payment-fail?reason=cancelled")

@router.get("/fail", response_class=HTMLResponse, include_in_schema=False)
async def kakao_payment_fail(order_id: str):
    db_sqlite.update_payment_status(order_id, "FAILED")
    return RedirectResponse(url="/payment-fail?reason=failed")
