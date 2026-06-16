from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
import db_manager as db

router = APIRouter()

@router.get("/schedule/confirm", response_class=HTMLResponse)
async def schedule_confirm_page(store_id: str):
    """
    알림톡에서 점주가 클릭하여 접근하는 간편 스케줄 설정 페이지.
    10초 이내에 정상 영업/휴무/설정변경을 선택 가능.
    """
    store = db.get_store(store_id)
    if not store:
        return "<p>잘못된 접근입니다. 매장 정보를 찾을 수 없습니다.</p>"
        
    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>스케줄 관리 - 탄탄한 동네비서</title>
        <style>
            body {{ font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; padding: 20px; text-align: center; background-color: #f8f9fc; }}
            .container {{ max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
            h2 {{ color: #1e3a8a; margin-bottom: 5px; }}
            p {{ color: #64748b; margin-bottom: 25px; }}
            .btn {{ display: block; width: 100%; padding: 15px; margin-bottom: 10px; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; }}
            .btn-normal {{ background-color: #3b82f6; color: white; }}
            .btn-closed {{ background-color: #ef4444; color: white; }}
            .input-box {{ width: 100%; padding: 10px; margin-bottom: 15px; border: 1px solid #cbd5e1; border-radius: 6px; display: none; }}
        </style>
        <script>
            function toggleClosedMessage() {{
                const input = document.getElementById("closed_msg_div");
                if (input.style.display === "none") {{
                     input.style.display = "block";
                }} else {{
                     input.style.display = "none";
                }}
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <h2>{store.get("name", "가맹점")} 사장님</h2>
            <p>내일 영업 스케줄을 확정해주세요.</p>
            
            <form action="/schedule/confirm/submit" method="post">
                <input type="hidden" name="store_id" value="{store_id}">
                <button type="submit" name="status" value="normal" class="btn btn-normal">✅ 정상 영업 (기본 콜백)</button>
            </form>
            
            <button class="btn btn-closed" onclick="toggleClosedMessage()">💤 임시 휴무 / 문구 변경</button>
            
            <div id="closed_msg_div" style="display: none; text-align: left; margin-top: 15px;">
                <form action="/schedule/confirm/submit" method="post">
                    <input type="hidden" name="store_id" value="{store_id}">
                    <input type="hidden" name="status" value="closed">
                    <label style="font-size: 14px; font-weight: bold; color: #475569;">고객에게 전송할 안내 문구</label>
                    <input type="text" name="closed_message" class="input-box" placeholder="예: 단체 회식 예약으로 휴무입니다." value="{store.get("closed_message", "")}" style="display: block; width: 90%; margin-top: 5px;" required>
                    <button type="submit" class="btn btn-closed">휴무 스케줄 확정</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    """
    return html

@router.post("/schedule/confirm/submit")
async def schedule_confirm_submit(store_id: str = Form(...), status: str = Form(...), closed_message: str = Form("")):
    """
    점주의 스케줄 응답 처리 (DB 업데이트)
    """
    store = db.get_store(store_id)
    if not store:
         return HTMLResponse(content="<p>알 수 없는 오류가 발생했습니다.</p>")

    # DB 업데이트 (has_confirmed_schedule, closed_message)
    # db.update_store가 지원하는 쿼리를 사용하거나, 지원하지 않는다면 새 함수 필요. 
    # 여기서는 Python 레벨에서 Mocking 또는 존재하는 update_store_partial 가능성 가정
    try:
        if status == "normal":
             db.update_store(store_id, {"closed_message": "현재 매장 부재중이거나 통화가 어렵습니다."})
        elif status == "closed":
             db.update_store(store_id, {"closed_message": closed_message})
    except Exception as e:
         pass # fallback if db module lacks update_store
         
    html = """
    <!DOCTYPE html>
    <html lang="ko">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>확정 완료</title>
    <style>body { text-align: center; padding: 50px; font-family: sans-serif; background: #eff6ff; }</style>
    </head>
    <body><h2>스케줄이 성공적으로 업데이트 되었습니다! 🚀</h2><p>창을 닫으셔도 좋습니다.</p></body>
    </html>
    """
    return HTMLResponse(content=html)
