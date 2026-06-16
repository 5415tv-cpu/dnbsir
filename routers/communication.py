from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import db_manager as db
import sms_manager as sms
from typing import List, Optional
import pandas as pd

router = APIRouter()

class SMSRequest(BaseModel):
    to_phone: str
    message: str
    store_id: Optional[str] = "test_store"

@router.get("/api/comm/contacts")
async def get_contacts(store_id: str = "test_store", tag: str = "동네비서"):
    """
    태그된 비즈니스 연락처 리스트를 가져옵니다.
    """
    try:
        df = db.get_crm_customers_by_tag(store_id, tag)
        if hasattr(df, 'empty') and df.empty:
            return {"success": True, "contacts": []}
        
        # DataFrame을 JSON 직렬화 가능한 리스트로 변환
        contacts = df.to_dict(orient="records")
        return {"success": True, "contacts": contacts}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/api/comm/send-sms")
async def send_business_sms(req: SMSRequest):
    """
    서버 사이드에서 비즈니스 문자를 발송합니다.
    """
    success, msg = sms.send_sms(req.to_phone, req.message, store_id=req.store_id)
    return {"success": success, "message": msg}

@router.get("/api/comm/check-contact")
async def check_business_contact(phone: str, store_id: str = "test_store"):
    """
    특정 번호가 비즈니스 연락처인지 확인합니다. (Android 앱에서 사용)
    """
    try:
        df = db.get_crm_customers_by_tag(store_id, "동네비서")
        if hasattr(df, 'empty') and df.empty:
            return {"is_business": False}
        
        # 번호 정규화 비교
        target = phone.replace("-", "").strip()
        phones = [str(p).replace("-", "").strip() for p in df['phone'].tolist()]
        
        is_business = target in phones
        return {"is_business": is_business}
    except Exception:
        return {"is_business": False}
