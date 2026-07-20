from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from fastapi.concurrency import run_in_threadpool
import db_manager as db

router = APIRouter(prefix="/reservation", tags=["reservation"])

class CheckRequest(BaseModel):
    store_id: str
    room_id: str
    check_in: str  # YYYY-MM-DD format
    check_out: str # YYYY-MM-DD format

class HoldRequest(BaseModel):
    store_id: str
    room_id: str
    check_in: str
    check_out: str
    guest_info: dict | str
    hold_duration_seconds: int = 600

class ConfirmRequest(BaseModel):
    reservation_id: int
    store_id: str

@router.post("/check")
async def check_reservation(req: CheckRequest):
    """
    Check if a specific room is available for the given dates.
    """
    if not req.store_id or not req.room_id or not req.check_in or not req.check_out:
        raise HTTPException(status_code=400, detail="Missing required parameters.")
        
    try:
        available = await run_in_threadpool(
            db.check_room_availability,
            req.store_id,
            req.room_id,
            req.check_in,
            req.check_out
        )
        return {"store_id": req.store_id, "room_id": req.room_id, "available": available}
    except Exception as e:
        print(f"[API check_reservation] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal database error: {str(e)}")

@router.post("/hold")
async def hold_reservation(req: HoldRequest):
    """
    Hold a room reservation before payment processing (status='pending').
    """
    if not req.store_id or not req.room_id or not req.check_in or not req.check_out:
        raise HTTPException(status_code=400, detail="Missing required parameters.")
        
    try:
        reservation_id = await run_in_threadpool(
            db.hold_room_reservation,
            req.store_id,
            req.room_id,
            req.check_in,
            req.check_out,
            req.guest_info,
            req.hold_duration_seconds
        )
        if reservation_id is None:
            raise HTTPException(status_code=409, detail="The room is already booked or held for these dates.")
            
        return {
            "success": True,
            "reservation_id": reservation_id,
            "message": f"Room reservation hold placed successfully for {req.hold_duration_seconds} seconds."
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API hold_reservation] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/confirm")
async def confirm_reservation(req: ConfirmRequest):
    """
    Confirm the reservation after successful payment (status='confirmed').
    """
    try:
        success = await run_in_threadpool(
            db.confirm_room_reservation,
            req.reservation_id,
            req.store_id
        )
        if not success:
            raise HTTPException(status_code=404, detail="Reservation not found or not in pending state.")
            
        return {
            "success": True,
            "reservation_id": req.reservation_id,
            "message": "Reservation successfully confirmed."
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API confirm_reservation] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
