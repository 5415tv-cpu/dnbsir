import os
import time
import requests
import base64
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from fastapi.concurrency import run_in_threadpool
import db_manager as db

router = APIRouter(prefix="/payment", tags=["payment"])

class PaymentRequest(BaseModel):
    store_id: str
    reservation_id: int
    amount: int
    order_name: str = "객실 예약"

@router.post("/request")
async def payment_request(req: PaymentRequest):
    """
    Generate a payment order ID and return client-side configuration for PG integration.
    """
    try:
        # Check if reservation exists and is pending
        res = await run_in_threadpool(db.get_room_reservation, req.reservation_id, req.store_id)
        if not res:
            raise HTTPException(status_code=404, detail="Reservation not found for this store.")
            
        if res.get("status") != "pending":
            raise HTTPException(status_code=400, detail=f"Reservation is not in pending state (current status: {res.get('status')})")
            
        # Generate a unique order_id matching the Toss schema
        order_id = f"RES-{req.reservation_id}-{int(time.time())}"
        
        toss_client_key = os.getenv("TOSS_CLIENT_KEY", "test_ck_PBal2vxj81ND2OPW6a7135RQgOAN")
        
        return {
            "success": True,
            "order_id": order_id,
            "amount": req.amount,
            "order_name": req.order_name,
            "client_key": toss_client_key,
            "store_id": req.store_id,
            "reservation_id": req.reservation_id
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API payment_request] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/webhook")
async def payment_webhook(req: dict, request: Request):
    """
    Receive webhook notifications from Toss Payments.
    """
    try:
        event_type = req.get("eventType")
        data = req.get("data", {})
        
        if not event_type or not data:
            print(f"[Payment Webhook] Unknown webhook format: {req}")
            raise HTTPException(status_code=400, detail="Invalid payload format.")
            
        order_id = data.get("orderId", "")
        status = data.get("status", "")
        payment_key = data.get("paymentKey", "")
        amount = data.get("amount", 0)
        
        # Filter for our reservation payments
        if not order_id.startswith("RES-"):
            return {"status": "ignored", "reason": "Not a RES order"}
            
        if status != "DONE":
            return {"status": "ignored", "reason": f"Status is {status}, not DONE"}
            
        # Parse reservation ID from order_id: RES-{reservation_id}-{timestamp}
        parts = order_id.split("-")
        if len(parts) < 3:
            raise HTTPException(status_code=400, detail=f"Invalid orderId format: {order_id}")
            
        try:
            reservation_id = int(parts[1])
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid reservation ID in orderId: {order_id}")
            
        # Find store_id and verify reservation
        conn = db.db.get_connection()
        c = conn.cursor()
        try:
            c.execute("SELECT store_id, status FROM reservations WHERE id = ?", (reservation_id,))
            row = c.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"Reservation {reservation_id} not found.")
            store_id = row["store_id"]
            db_status = row["status"]
        finally:
            conn.close()
            
        # Verify and confirm payment with Toss API
        confirm_success = await run_in_threadpool(confirm_toss_payment_direct, payment_key, order_id, amount)
        if not confirm_success:
            raise HTTPException(status_code=400, detail="Toss payments confirmation failed.")
            
        # Update reservation status to confirmed
        success = await run_in_threadpool(db.confirm_room_reservation, reservation_id, store_id)
        if not success:
            if db_status == "confirmed":
                return {"status": "success", "message": "Already confirmed"}
            raise HTTPException(status_code=500, detail="Failed to update reservation to confirmed state.")
            
        return {"status": "success", "message": "Reservation confirmed successfully via Webhook"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Payment Webhook Exception] {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status-check")
async def payment_status_check(reservation_id: int, store_id: str, payment_key: str = "", order_id: str = "", amount: int = 0):
    """
    Polling/direct check fallback if webhook is delayed or missed.
    """
    try:
        res = await run_in_threadpool(db.get_room_reservation, reservation_id, store_id)
        if not res:
            raise HTTPException(status_code=404, detail="Reservation not found.")
            
        if res.get("status") == "confirmed":
            return {"status": "confirmed", "message": "Reservation is already confirmed."}
            
        if not payment_key or not order_id or amount <= 0:
            raise HTTPException(status_code=400, detail="Missing payment verification credentials for polling check.")
            
        confirm_success = await run_in_threadpool(confirm_toss_payment_direct, payment_key, order_id, amount)
        if confirm_success:
            await run_in_threadpool(db.confirm_room_reservation, reservation_id, store_id)
            return {"status": "confirmed", "message": "Reservation confirmed via status check."}
            
        return {"status": "pending", "message": "Payment not confirmed yet."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def confirm_toss_payment_direct(payment_key: str, order_id: str, amount: int) -> bool:
    toss_secret_key = os.getenv("TOSS_SECRET_KEY", "test_sk_26DlbXAaV0Kbn1ljMQa43qY50Q9R")
    url = "https://api.tosspayments.com/v1/payments/confirm"
    
    secret_key_with_colon = f"{toss_secret_key}:"
    encoded_secret_key = base64.b64encode(secret_key_with_colon.encode("utf-8")).decode("utf-8")
    
    headers = {
        "Authorization": f"Basic {encoded_secret_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "paymentKey": payment_key,
        "orderId": order_id,
        "amount": amount
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"[confirm_toss_payment_direct] Approved Toss payment for order {order_id} successfully!")
            return True
        else:
            err_text = response.text
            if "ALREADY_PROCESSED" in err_text:
                print(f"[confirm_toss_payment_direct] Order {order_id} already confirmed.")
                return True
            print(f"[confirm_toss_payment_direct] Failed status: {response.status_code}, error: {err_text}")
            return False
    except Exception as e:
        print(f"[confirm_toss_payment_direct] System error connecting to Toss: {e}")
        return False
