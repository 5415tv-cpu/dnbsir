from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
import os
import db_manager as db

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
API_URL = os.environ.get("API_URL", "")

@router.get("/api/admin/crm/revisit-list")
async def get_revisit_list_endpoint():
    return db.get_today_revisit_list("test_store")

@router.post("/api/admin/crm/send-msg")
async def send_marketing_msg(request: Request):
    data = await request.json()
    phone = data.get("phone")
    return {"success": True, "message": f"{phone}님께 발송되었습니다."}

class CardRegisterRequest(BaseModel):
    card_number: str
    expiry: str
    pwd_2digit: str

@router.post("/api/admin/cards/auth")
async def register_card_auth(request: Request):
    data = await request.json()
    action = data.get("action")
    if action == "request_sms":
        return {"success": True, "message": "인증번호가 발송되었습니다."}
    elif action == "verify":
        code = data.get("code")
        if code == "123456":
            return {"success": True, "message": "인증되었습니다. (유효기간: 1년)"}
        else:
            return {"success": False, "message": "인증번호가 틀렸습니다."}
    return {"success": False, "error": "Invalid Action"}

@router.get("/admin/cards/register", response_class=HTMLResponse)
async def card_register_page(request: Request):
    return templates.TemplateResponse("card_register.html", {"request": request, "api_url": API_URL})

@router.post("/api/admin/cards/register")
async def register_card_api(card: CardRegisterRequest):
    store_id = "test_store"
    db.save_expense(store_id, "새로등록한카드", "식대", 15000, "2026-02-08")
    return {"success": True}
