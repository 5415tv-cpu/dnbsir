from fastapi import APIRouter, Request, Form, Response, Depends, HTTPException, BackgroundTasks, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Union
from pathlib import Path
from datetime import datetime
import os

import db_manager as db
try:
    import server.google_sheet_sync as gsheet
except ImportError:
    gsheet = None

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
API_URL = os.environ.get("API_URL", "https://dnbsir-api-ap33e42daq-uc.a.run.app")

class User(BaseModel):
    store_id: str
    role: str = "owner"
    is_signed: bool = False

async def get_current_user(request: Request):
    store_id = request.cookies.get("admin_session")
    if not store_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    
    from fastapi.concurrency import run_in_threadpool
    store = await run_in_threadpool(db.get_store, store_id)
    if not store:
        raise HTTPException(status_code=401, detail="존재하지 않는 사용자입니다.")
        
    role = store.get("role", "owner")
    if store_id == "master":
        role = "delivery"
    
    is_signed = store.get("is_signed", False)
        
    return User(store_id=store_id, role=role, is_signed=is_signed)

def check_user_role(current_user: User, required_role: str):
    if current_user.role != required_role:
        raise HTTPException(status_code=403, detail="접근 권한이 없는 페이지입니다.")
    return True

@router.get("/admin", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.cookies.get("admin_session"):
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "api_url": API_URL,
        "hide_bottom_nav": True
    })

@router.post("/login")
async def login(
    response: Response, 
    background_tasks: BackgroundTasks, 
    store_id: str = Form(...), 
    password: str = Form(...),
    mode: str = Form("login")
):
    print(f"DEBUG: Login flow. store_id={store_id}, mode={mode}")
    store = db.get_store(store_id)
    
    if not store:
        clean_id = store_id.replace("-", "").strip()
        if clean_id != store_id:
             print(f"DEBUG: Retrying with normalized ID: {clean_id}")
             store = db.get_store(clean_id)
             if store:
                 store_id = clean_id

    print(f"DEBUG: db.get_store frame: {'Found' if store else 'Not Found'}")
    
    if mode == "signup":
        if store:
            print("DEBUG: Signup failed - User exists")
            raise HTTPException(status_code=409, detail="User already exists")
            
        print("DEBUG: New user, attempting auto-signup")
        new_store_data = {
            "store_id": store_id,
            "password": password,
            "name": "사장님",
            "owner_name": "미입력",
            "phone": store_id,
            "points": 0,
            "membership": "free"
        }
        res = db.save_store(store_id, new_store_data)
        
        if not res:
            print("DEBUG: Auto-signup failed (DB Error)")
            raise HTTPException(status_code=500, detail="Signup failed")
            
        join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if gsheet:
            from fastapi.concurrency import run_in_threadpool
            background_tasks.add_task(run_in_threadpool, gsheet.sync_to_google_sheet, [store_id, "사장님", "무료회원", join_date])
            
        store = new_store_data

    elif mode == "login":
        if not store:
            print("DEBUG: Login failed - User not found")
            raise HTTPException(status_code=404, detail="User not found")

    db_password = str(store.get('password'))
    
    if db_password == password:
        print("DEBUG: Password match")
        
        ADMIN_ACCOUNTS = ["master", "010-2384-7447", "01023847447"]
        
        if store_id in ADMIN_ACCOUNTS:
             response = RedirectResponse(url="/admin/master", status_code=303)
        else:
             user_role = store.get("user_role")
             if not user_role:
                 print(f"DEBUG: No role found for {store_id}, redirecting to selection")
                 response = RedirectResponse(url="/select-role", status_code=303)
             else:
                 response = RedirectResponse(url="/admin/dashboard", status_code=303)
        
        response.set_cookie(
            key="admin_session", 
            value=store_id,
            httponly=True,
            max_age=3600 * 24,
            samesite="lax",
            secure=False 
        )
        return response
    else:
        print("DEBUG: Password mismatch")
        raise HTTPException(status_code=401, detail="Invalid password")

@router.get("/select-role", response_class=HTMLResponse)
async def select_role_page(request: Request):
    store_id = request.cookies.get("admin_session")
    if not store_id:
        return RedirectResponse(url="/admin", status_code=303)
        
    return templates.TemplateResponse("role_select.html", {"request": request, "store_id": store_id})

@router.post("/api/select-role")
async def select_role_api(
    store_id: str = Form(...),
    role: str = Form(...)
):
    print(f"[RBAC] User {store_id} selected role: {role}")
    valid_roles = ["citizen", "farmer", "merchant", "logistics"]
    
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid Role")
        
    if db.update_store_role(store_id, role):
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    else:
        raise HTTPException(status_code=500, detail="Failed to update role")

@router.get("/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/admin", status_code=303)
    response.delete_cookie("admin_session")
    return response

