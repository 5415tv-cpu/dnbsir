from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
import db_manager as db
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sms_manager import send_alimtalk, send_sms

class KakaoRequest(BaseModel):
    phone: str

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent
from templates_config import templates
BASE_DIR = Path(__file__).resolve().parent.parent

@router.post("/api/debug_log")
async def debug_log(request: Request):
    data = await request.json()
    print(f"[Frontend Log] {data}")
    return {"status": "ok"}

@router.get("/support", response_class=HTMLResponse)
async def public_support_page(request: Request):
    return HTMLResponse("<script>alert('소상공인 지원사업 알림 기능은 준비 중입니다. (COMING SOON)'); history.back();</script>")

@router.get("/subsidy", response_class=HTMLResponse)
async def public_subsidy_page(request: Request):
    # Pass api_url to keep frontend routing clean
    from app import API_URL
    return templates.TemplateResponse(request, "subsidy.html", {
        "request": request,
        "api_url": API_URL
    })

@router.post("/api/subsidy/kakao")
async def send_subsidy_kakao(req: KakaoRequest):
    phone = req.phone.strip().replace("-", "")
    if not phone or len(phone) < 10:
        return JSONResponse(status_code=400, content={"success": False, "message": "유효한 휴대폰 번호를 입력해주세요."})
    
    # Message content
    msg = (
        "[동네비서]\n"
        "사장님, 요청하신 지자체 농업인 수당 상세 안내서류가 준비되었습니다.\n\n"
        "아래 링크에서 확인하시고 혜택을 빠짐없이 챙기세요!\n\n"
        "▶ 상세 확인하기: https://dongnebiseo.com/subsidy\n\n"
        "※ 본 메시지는 수신자가 요청한 정보를 바탕으로 발송되었습니다.\n"
        "※ 수신자가 신청한 알림톡 서비스 정기 발송 고지 안내입니다."
    )
    
    template_vars = {
        "#{store_name}": "사장님",
        "#{link}": "https://dongnebiseo.com/subsidy"
    }

    success, err_msg = send_alimtalk(phone, message=msg, variables=template_vars)
    if not success:
        print(f"[Subsidy Kakao] Alimtalk Failed: {err_msg}. Falling back to SMS.")
        success, err_msg = send_sms(phone, msg)
        
    if success:
        return {"success": True, "message": "성공적으로 발송되었습니다."}
    else:
        return JSONResponse(status_code=500, content={"success": False, "message": f"발송 실패: {err_msg}"})



@router.get("/api/ping")
async def ping():
    return {"status": "ok", "message": "pong"}

@router.get("/api/health_full")
def health_full():
    pass 
    # To avoid API_URL issues if not imported here
    status = {"status": "ok", "db": "unknown", "base_dir": str(BASE_DIR), "env": {}}
    try:
        store = db.get_store("test_store")
        status["db"] = "connected" if store else "empty"
    except Exception as e:
        status["db"] = f"error: {e}"
    
    return status

@router.get("/api/version")
def debug_version():
    from db_backend import _use_cloudsql
    backend = "Cloud SQL" if _use_cloudsql() else "SQLite"
    return {"source": "modularized", "status": "patched_v4", "db_backend": backend}

@router.get("/api/app_version")
def app_version():
    return {
        "latest_version": "1.9.3",
        "min_version": "1.0.0",
        "update_url": "https://dongnebiseo.com/static/apps/dongnebiseo_latest.apk"
    }

@router.get("/api/admin/security/backup")
async def backup_db_endpoint():
    success, path = db.create_db_backup()
    if success:
        return {"success": True, "path": path}
    return {"success": False, "error": path}

@router.get("/api/admin/security/integrity")
async def check_integrity_endpoint():
    ok = db.get_db_integrity()
    return {"status": "OK" if ok else "CORRUPTED"}

@router.get("/health")
def health_check():
    return {"ok": True}

@router.get("/status", response_class=HTMLResponse)
async def visual_health_check():
    return """
    <html>
        <head>
            <title>동네비서 시스템 상태</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { font-family: 'Noto Sans KR', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f8fafc; margin: 0; }
                .card { background: white; padding: 40px; border-radius: 24px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); text-align: center; border: 1px solid #e2e8f0; width: 80%; max-width: 400px; }
                .status-light { width: 40px; height: 40px; background: #22c55e; border-radius: 50%; display: inline-block; box-shadow: 0 0 20px #22c55e; animation: pulse 2s infinite; margin-bottom: 24px; }
                @keyframes pulse { 0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7); } 70% { transform: scale(1); box-shadow: 0 0 0 20px rgba(34, 197, 94, 0); } 100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); } }
                h1 { color: #0f172a; margin: 0 0 12px 0; font-size: 1.5rem; }
                p { color: #64748b; margin: 0; font-size: 1rem; line-height: 1.5; }
                .refresh-btn { margin-top: 32px; padding: 14px 28px; border: none; background: #f1f5f9; color: #334155; border-radius: 12px; cursor: pointer; font-weight: bold; font-size: 1rem; width: 100%; transition: all 0.2s; }
                .refresh-btn:hover { background: #e2e8f0; }
            </style>
        </head>
        <body>
            <div class="card">
                <div class="status-light"></div>
                <h1>시스템 정상 가동 중</h1>
                <p>AI 동네비서 마이크로서비스가 완벽하게 돌아가고 있습니다.</p>
                <button class="refresh-btn" onclick="location.reload()">새로고침</button>
            </div>
        </body>
    </html>
    """


# --- Rollback System Endpoints ---
from fastapi.responses import RedirectResponse
from fastapi import Cookie
from typing import Union
import subprocess

@router.get("/admin/rollback", response_class=HTMLResponse)
async def admin_rollback_page(
    request: Request,
    cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")
):
    ADMIN_ACCOUNTS = ["master", "010-2384-7447", "01023847447"]
    if not cookie_store_id or cookie_store_id not in ADMIN_ACCOUNTS:
        return RedirectResponse(url="/admin?mode=login", status_code=303)
        
    return """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>동네비서 - 긴급 시스템 롤백</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&family=Noto+Sans+KR:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: 'Outfit', 'Noto Sans KR', sans-serif;
            background: linear-gradient(135deg, #0b0f19 0%, #111827 100%);
            color: #f3f4f6;
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            overflow: hidden;
        }
        .container {
            background: rgba(255, 255, 255, 0.02);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 40px;
            border-radius: 32px;
            width: 90%;
            max-width: 480px;
            text-align: center;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            position: relative;
        }
        .warning-icon {
            width: 80px;
            height: 80px;
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.2);
            border-radius: 50%;
            display: inline-flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 24px;
            color: #ef4444;
            font-size: 2.5rem;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
            70% { box-shadow: 0 0 0 20px rgba(239, 68, 68, 0); }
            100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
        }
        h1 {
            font-size: 1.8rem;
            font-weight: 800;
            margin: 0 0 12px 0;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        p {
            font-size: 0.95rem;
            color: #9ca3af;
            line-height: 1.6;
            margin: 0 0 32px 0;
        }
        .btn-rollback {
            background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
            color: white;
            border: none;
            padding: 16px 32px;
            border-radius: 16px;
            font-weight: 700;
            font-size: 1.1rem;
            width: 100%;
            cursor: pointer;
            box-shadow: 0 10px 20px rgba(220, 38, 38, 0.2);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .btn-rollback:hover {
            transform: translateY(-2px);
            box-shadow: 0 15px 25px rgba(220, 38, 38, 0.35);
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        }
        .btn-rollback:active {
            transform: translateY(1px);
        }
        .btn-cancel {
            background: transparent;
            color: #9ca3af;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 14px 32px;
            border-radius: 16px;
            font-weight: 600;
            font-size: 1rem;
            width: 100%;
            cursor: pointer;
            margin-top: 12px;
            transition: all 0.2s;
        }
        .btn-cancel:hover {
            background: rgba(255, 255, 255, 0.05);
            color: white;
        }
        .overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: #0f172a;
            border-radius: 32px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 40px;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.4s ease;
            z-index: 10;
        }
        .overlay.active {
            opacity: 1;
            pointer-events: auto;
        }
        .loader {
            width: 48px;
            height: 48px;
            border: 3px solid rgba(255, 255, 255, 0.05);
            border-top-color: #ef4444;
            border-radius: 50%;
            animation: spin 1s infinite linear;
            margin-bottom: 24px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .progress-container {
            width: 100%;
            background: rgba(255, 255, 255, 0.05);
            height: 6px;
            border-radius: 3px;
            overflow: hidden;
            margin-bottom: 16px;
        }
        .progress-bar {
            width: 0%;
            height: 100%;
            background: linear-gradient(90deg, #ef4444, #f97316);
            transition: width 10s linear;
        }
        .status-text {
            font-size: 0.95rem;
            font-weight: 600;
            color: #cbd5e1;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="warning-icon">⚠️</div>
        <h1>긴급 시스템 롤백</h1>
        <p>
            현재 활성화된 버전에서 치명적 결함이 발견된 경우, 즉각 이전의 안정화 버전으로 시스템을 되돌립니다.<br><br>
            이 작업은 서비스 중단을 최소화하기 위해 약 10초 내에 강제 복구 및 서버 재부팅을 진행합니다.
        </p>
        <button class="btn-rollback" onclick="triggerRollback()">원클릭 롤백 실행</button>
        <button class="btn-cancel" onclick="history.back()">취소 및 돌아가기</button>

        <div class="overlay" id="overlay">
            <div class="loader"></div>
            <h2 style="font-size: 1.4rem; font-weight: 800; margin: 0 0 8px 0;">이전 안정 버전 복구 중</h2>
            <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 24px;">원클릭 자동 복구 시스템 가동 중...</div>
            <div class="progress-container">
                <div class="progress-bar" id="progressBar"></div>
            </div>
            <div class="status-text" id="statusText">이전 코드 데이터 복원하는 중 (1/3)...</div>
        </div>
    </div>

    <script>
        async function triggerRollback() {
            if (!confirm("정말 이 버전으로 롤백하시겠습니까?\\n이 작업은 즉시 서버를 재시작합니다.")) {
                return;
            }

            const overlay = document.getElementById('overlay');
            const progressBar = document.getElementById('progressBar');
            const statusText = document.getElementById('statusText');

            overlay.classList.add('active');
            
            setTimeout(() => {
                progressBar.style.width = '100%';
            }, 50);

            setTimeout(() => {
                statusText.innerText = "서버 백업 데이터 교체 및 재설정 중 (2/3)...";
            }, 3000);

            setTimeout(() => {
                statusText.innerText = "FastAPI 서버 인스턴스 재시작 중 (3/3)...";
            }, 6500);

            setTimeout(() => {
                statusText.innerText = "롤백 완료! 시스템이 정상화되었습니다. 페이지를 새로고침합니다.";
                location.href = '/status';
            }, 10000);

            try {
                const res = await fetch('/api/admin/rollback', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                const data = await res.json();
                if (!data.success) {
                    alert('롤백 요청 실패: ' + data.message);
                    location.reload();
                }
            } catch(e) {
                console.log('Server connection interrupted as expected during restart.');
            }
        }
    </script>
</body>
</html>"""

@router.post("/api/admin/rollback")
async def api_admin_rollback(
    request: Request,
    cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")
):
    ADMIN_ACCOUNTS = ["master", "010-2384-7447", "01023847447"]
    if not cookie_store_id or cookie_store_id not in ADMIN_ACCOUNTS:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized admin access"})
        
    cmd = 'nohup bash -c "sleep 1 && /var/www/dnbsir_rollback.sh" > /var/www/rollback.log 2>&1 &'
    try:
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"success": True, "message": "Rollback initiated successfully."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": f"Failed to initiate rollback command: {str(e)}"})


# ──────────────────────────────────────────────────────────
# 🌐 미가입자용 공개 API (Public API — 인증 불필요)
# 미들웨어의 통제를 받지 않는 안전 지대 (/api/public/)
# 토큰 소모 없음, IP 기반 Rate Limiting 적용
# ──────────────────────────────────────────────────────────
import time
from collections import defaultdict

# 간단한 인메모리 Rate Limiter (IP당 하루 60회 제한)
_public_api_calls: dict = defaultdict(list)
PUBLIC_API_LIMIT = 60      # 최대 호출 횟수
PUBLIC_API_WINDOW = 86400  # 시간 창 (초) = 24시간

def _check_rate_limit(client_ip: str) -> bool:
    """True = 허용, False = 차단"""
    now = time.time()
    calls = _public_api_calls[client_ip]
    # 시간 창 밖의 기록 제거
    _public_api_calls[client_ip] = [t for t in calls if now - t < PUBLIC_API_WINDOW]
    if len(_public_api_calls[client_ip]) >= PUBLIC_API_LIMIT:
        return False
    _public_api_calls[client_ip].append(now)
    return True


@router.get("/api/public/status")
async def public_service_status(request: Request):
    """동네비서 서비스 상태 및 소개 — 미가입자에게 무료 제공"""
    client_ip = request.client.host
    if not _check_rate_limit(client_ip):
        return JSONResponse(
            status_code=429,
            content={"error": "요청 한도 초과", "detail": "하루 최대 60회까지 조회 가능합니다."}
        )
    return {
        "service": "동네비서",
        "status": "운영 중",
        "features": {
            "free": ["날씨 조회", "서비스 안내"],
            "premium": ["AI 비서 질문", "주문 관리", "단골 알림톡", "매출 분석", "수수료 정산"]
        },
        "cta": {
            "message": "프리미엄 기능을 무료로 30일 체험해 보세요!",
            "url": "/store/landing"
        }
    }


@router.get("/api/public/weather")
async def get_today_weather(request: Request, region: str = "태백시"):
    """오늘 날씨 정보 — 미가입자에게 무료 제공 (IP 기반 Rate Limiting)"""
    client_ip = request.client.host
    if not _check_rate_limit(client_ip):
        return JSONResponse(
            status_code=429,
            content={"error": "요청 한도 초과", "detail": "하루 최대 60회까지 조회 가능합니다."}
        )
    # TODO: 실제 기상청 API 연동 (현재는 샘플 응답)
    return {
        "region": region,
        "date": time.strftime("%Y-%m-%d"),
        "weather": "맑음",
        "temperature": "25°C",
        "humidity": "55%",
        "wind": "북동풍 2m/s",
        "message": f"오늘 {region} 날씨는 맑으며, 기온은 25도입니다. 야외 활동하기 좋은 날씨입니다.",
        "tip": "동네비서에 가입하면 날씨 기반 스마트 알림톡도 자동 발송돼요! 👉 /store/landing"
    }


@router.get("/api/public/intro")
async def get_service_intro(request: Request):
    """동네비서 서비스 소개 — 미가입자용 랜딩 데이터"""
    return {
        "name": "동네비서",
        "tagline": "사장님의 하루를 가볍게. AI 동네비서가 대신 합니다.",
        "benefits": [
            {"icon": "📞", "title": "미수신 전화 자동 응대", "desc": "전화 못 받아도 AI가 대신 고객에게 콜백 문자 발송"},
            {"icon": "📊", "title": "매출·수수료 자동 정산", "desc": "월말 정산을 AI가 자동으로 계산해 드립니다"},
            {"icon": "💬", "title": "단골 알림톡 자동 발송", "desc": "단골 고객에게 특가 행사 알림톡 자동 전송"},
            {"icon": "📦", "title": "택배 자동 접수", "desc": "로젠·한진·CJ 택배 자동 연동 접수"},
        ],
        "cta_url": "/store/landing",
        "login_url": "/admin?mode=login"
    }
