from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, List
import os
import db_manager as db

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent
from templates_config import templates
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
    return templates.TemplateResponse(request, "card_register.html", {"request": request, "api_url": API_URL})

@router.post("/api/admin/cards/register")
async def register_card_api(card: CardRegisterRequest):
    store_id = "test_store"
    db.save_expense(store_id, "새로등록한카드", "식대", 15000, "2026-02-08")
    return {"success": True}


# ════════════════════════════════════════════════════════
# 택배 광고문자 발송 (동네비서 쿠리어 유입 캠페인)
# ════════════════════════════════════════════════════════

_AD_TEMPLATE = """(광고) [{store_name}] 방금 통화하신 매장 택배 접수 안내

바쁜 시간, 송장 주소 일일이 타이핑하기 힘드셨죠?
아래 링크에 주소와 이름만 '말하거나 붙여넣으면' AI가 알아서 접수증을 만들어 드립니다.

➡️ 3초 만에 택배 접수하기:
https://dongnebisor.com/citizen/courier

--------------------------------
[발송처 정보]
- 상호명: {store_name}
- 사업자등록번호: {biz_no}
- 고객센터: {store_phone}
- 본 문자 신청/해지 문의는 위 고객센터로 연락 바랍니다.

무료 수신거부: {opt_out_number}"""


class CourierAdRequest(BaseModel):
    to_phone: str
    store_name: str = "탄탄제작소"
    store_phone: str = ""
    biz_no: str = ""
    opt_out_number: str = "080-000-0000"
    store_id: Optional[str] = "SYSTEM"


class CourierAdBulkRequest(BaseModel):
    phones: List[str]
    store_name: str = "탄탄제작소"
    store_phone: str = ""
    biz_no: str = ""
    opt_out_number: str = "080-000-0000"
    store_id: Optional[str] = "SYSTEM"


def _build_body(store_name, store_phone, biz_no, opt_out_number):
    return _AD_TEMPLATE.format(
        store_name=store_name or "동네비서",
        store_phone=store_phone or "고객센터 문의",
        biz_no=biz_no or "미등록",
        opt_out_number=opt_out_number or "080-000-0000",
    )


@router.post("/api/crm/courier-ad/send")
async def send_courier_ad_single(req: CourierAdRequest):
    """단건 택배 광고문자 발송"""
    import re
    to = req.to_phone.strip()
    if not to or not re.match(r"^0\d{1,2}-?\d{3,4}-?\d{4}$", to):
        raise HTTPException(status_code=422, detail=f"올바르지 않은 전화번호: {to}")

    body = _build_body(req.store_name, req.store_phone, req.biz_no, req.opt_out_number)
    try:
        import sms_manager
        cfg = sms_manager.get_solapi_config()
        ok, info = sms_manager.send_sms(to, body, config=cfg, store_id=req.store_id or "SYSTEM")
        if ok:
            return {"success": True, "phone": to, "detail": info}
        raise HTTPException(status_code=502, detail=f"발송 실패: {info}")
    except HTTPException:
        raise
    except ImportError:
        return {"success": False, "detail": "sms_manager 모듈 없음 (Mock)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/crm/courier-ad/send-bulk")
async def send_courier_ad_bulk(req: CourierAdBulkRequest):
    """최대 50건 일괄 택배 광고문자 발송"""
    if len(req.phones) > 50:
        raise HTTPException(status_code=422, detail="최대 50건까지 가능합니다.")

    import re
    try:
        import sms_manager
        cfg = sms_manager.get_solapi_config()
    except ImportError:
        cfg = {}

    body    = _build_body(req.store_name, req.store_phone, req.biz_no, req.opt_out_number)
    results = []

    for phone in req.phones:
        phone = phone.strip()
        if not re.match(r"^0\d{1,2}-?\d{3,4}-?\d{4}$", phone):
            results.append({"phone": phone, "success": False, "detail": "번호 형식 오류"})
            continue
        try:
            import sms_manager
            ok, info = sms_manager.send_sms(phone, body, config=cfg, store_id=req.store_id or "SYSTEM")
            results.append({"phone": phone, "success": ok, "detail": info})
        except Exception as e:
            results.append({"phone": phone, "success": False, "detail": str(e)})

    success_count = sum(1 for r in results if r["success"])
    return {
        "total": len(req.phones),
        "success": success_count,
        "failed": len(req.phones) - success_count,
        "results": results,
    }


@router.get("/admin/crm/courier-ad", response_class=HTMLResponse)
async def courier_ad_page(request: Request):
    return HTMLResponse(content=_COURIER_AD_PAGE)


_COURIER_AD_PAGE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>택배 광고문자 발송 — 동네비서</title>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap" rel="stylesheet">
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    :root{
      --bg:#0f172a;--surface:#1a2236;--card:#1e2d45;
      --border:#2d3f5c;--text:#e2e8f0;--muted:#64748b;
      --gold:#f5c842;--green:#22c55e;--red:#ef4444;--radius:14px;
    }
    body{font-family:'Noto Sans KR',sans-serif;background:var(--bg);color:var(--text);
         min-height:100vh;padding:32px 16px 80px;display:flex;flex-direction:column;align-items:center;}
    h1{font-size:1.5rem;font-weight:900;margin-bottom:4px;}
    .sub{color:var(--muted);font-size:.9rem;margin-bottom:28px;}
    .card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
          padding:24px;width:100%;max-width:640px;margin-bottom:16px;}
    .card-title{font-size:.78rem;font-weight:700;color:var(--muted);letter-spacing:1px;
                text-transform:uppercase;margin-bottom:16px;}
    label{display:block;font-size:.82rem;color:var(--muted);margin-bottom:6px;}
    input{width:100%;background:var(--card);border:1px solid var(--border);border-radius:10px;
          color:var(--text);font-family:'Noto Sans KR',sans-serif;font-size:.95rem;
          padding:11px 14px;outline:none;transition:border-color .2s,box-shadow .2s;}
    input:focus{border-color:var(--gold);box-shadow:0 0 0 3px rgba(245,200,66,.12);}
    .fg{margin-bottom:14px;}
    .preview-box{background:var(--card);border:1px solid var(--border);border-radius:10px;
                 padding:16px;font-size:.82rem;line-height:1.7;white-space:pre-wrap;
                 color:#c7d2e0;font-family:monospace;max-height:280px;overflow-y:auto;}
    .phone-list{display:flex;flex-direction:column;gap:8px;}
    .phone-row{display:flex;gap:8px;align-items:center;}
    .phone-row input{flex:1;}
    .btn-rm{background:transparent;border:1px solid var(--border);border-radius:8px;
            color:var(--muted);cursor:pointer;padding:8px 12px;font-size:.85rem;
            transition:border-color .15s,color .15s;}
    .btn-rm:hover{border-color:var(--red);color:var(--red);}
    .btn-add{background:transparent;border:1px dashed var(--border);border-radius:10px;
             color:var(--muted);cursor:pointer;padding:10px;width:100%;font-size:.88rem;
             margin-top:8px;transition:border-color .15s,color .15s;}
    .btn-add:hover{border-color:var(--gold);color:var(--gold);}
    .actions{display:flex;gap:10px;margin-top:20px;}
    .btn{flex:1;border:none;border-radius:10px;cursor:pointer;
         font-family:'Noto Sans KR',sans-serif;font-size:.95rem;font-weight:700;
         padding:14px;transition:opacity .15s,transform .1s;}
    .btn:hover{opacity:.88;transform:translateY(-1px);}
    .btn-send{background:var(--gold);color:#111;}
    .btn-preview{background:var(--border);color:var(--text);}
    #result-area{width:100%;max-width:640px;margin-top:12px;display:none;}
    .result-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;}
    .result-header{background:var(--card);border-bottom:1px solid var(--border);
                   padding:14px 20px;display:flex;align-items:center;justify-content:space-between;}
    .stat-row{display:flex;gap:24px;padding:16px 20px;border-bottom:1px solid var(--border);}
    .stat{display:flex;flex-direction:column;align-items:center;gap:4px;}
    .stat .n{font-size:1.6rem;font-weight:900;}
    .stat .l{font-size:.75rem;color:var(--muted);}
    .n-ok{color:var(--green);}.n-fail{color:var(--red);}
    .log-list{max-height:200px;overflow-y:auto;}
    .log-row{display:flex;align-items:center;gap:10px;padding:10px 20px;
             border-bottom:1px solid var(--border);font-size:.83rem;}
    .log-row:last-child{border-bottom:none;}
    .badge{font-size:.7rem;font-weight:700;padding:2px 8px;border-radius:6px;}
    .badge-ok{background:rgba(34,197,94,.15);color:var(--green);}
    .badge-fail{background:rgba(239,68,68,.15);color:var(--red);}
    .spinner{display:inline-block;width:15px;height:15px;border:2px solid rgba(0,0,0,.2);
             border-top-color:#111;border-radius:50%;animation:spin .6s linear infinite;}
    @keyframes spin{to{transform:rotate(360deg)}}

    /* 법적 고지 배너 */
    .law-banner{background:rgba(245,200,66,.08);border:1px solid rgba(245,200,66,.25);
                border-radius:10px;padding:12px 16px;font-size:.78rem;color:var(--gold);
                margin-bottom:16px;line-height:1.6;width:100%;max-width:640px;}
  </style>
</head>
<body>

  <h1>📣 택배 광고문자 발송</h1>
  <p class="sub">통화 후 고객에게 동네비서 택배 접수 링크를 안내합니다.</p>

  <div class="law-banner">
    ⚠️ <strong>방통위 광고 문자 규정</strong><br>
    ① 문자 맨 앞에 <strong>(광고)</strong> 표기 必 &nbsp;|&nbsp;
    ② 발송자 상호·연락처 포함 必 &nbsp;|&nbsp;
    ③ <strong>무료 수신거부 080 번호</strong> 포함 必<br>
    위 양식은 규정을 반영하여 자동 생성됩니다.
  </div>

  <!-- 발송처 정보 -->
  <div class="card">
    <div class="card-title">🏢 발송처 정보</div>
    <div class="fg"><label>상호명</label><input id="store-name" value="탄탄제작소"></div>
    <div class="fg"><label>사업자등록번호</label><input id="biz-no" placeholder="000-00-00000"></div>
    <div class="fg"><label>고객센터 번호</label><input id="store-phone" placeholder="010-0000-0000" oninput="hyphen(this)"></div>
    <div class="fg"><label>수신거부 번호 (080 무료)</label><input id="opt-out" value="080-000-0000"></div>
  </div>

  <!-- 미리보기 -->
  <div class="card">
    <div class="card-title">👁️ 문자 미리보기 <span style="font-size:.75rem;font-weight:400;color:var(--muted);">(발송 전 반드시 확인)</span></div>
    <div class="preview-box" id="preview-box">아래 '미리보기' 버튼을 눌러 내용을 확인하세요.</div>
  </div>

  <!-- 수신 번호 -->
  <div class="card">
    <div class="card-title">📞 수신 번호 (최대 50건)</div>
    <div class="phone-list" id="phone-list">
      <div class="phone-row">
        <input type="tel" placeholder="010-0000-0000" class="phone-input" maxlength="13" oninput="hyphen(this)">
        <button class="btn-rm" onclick="removeRow(this)">✕</button>
      </div>
    </div>
    <button class="btn-add" onclick="addRow()">+ 번호 추가</button>

    <div class="actions">
      <button class="btn btn-preview" onclick="doPreview()">👁️ 미리보기</button>
      <button class="btn btn-send" id="send-btn" onclick="doSend()">✈️ 발송하기</button>
    </div>
  </div>

  <div id="result-area">
    <div class="result-card">
      <div class="result-header">
        <span style="font-weight:700;">📋 발송 결과</span>
        <span id="result-time" style="font-size:.8rem;color:var(--muted);"></span>
      </div>
      <div class="stat-row">
        <div class="stat"><span class="n" id="r-total">—</span><span class="l">총 발송</span></div>
        <div class="stat"><span class="n n-ok" id="r-ok">—</span><span class="l">성공</span></div>
        <div class="stat"><span class="n n-fail" id="r-fail">—</span><span class="l">실패</span></div>
      </div>
      <div class="log-list" id="log-list"></div>
    </div>
  </div>

<script>
function hyphen(el){
  el.value=el.value.replace(/[^0-9]/g,'')
    .replace(/^(\d{0,3})(\d{0,4})(\d{0,4})$/,(_,a,b,c)=>a+(b?'-'+b:'')+(c?'-'+c:''));
}
function addRow(){
  const list=document.getElementById('phone-list');
  if(list.children.length>=50)return alert('최대 50건까지 입력할 수 있습니다.');
  const row=document.createElement('div');
  row.className='phone-row';
  row.innerHTML='<input type="tel" placeholder="010-0000-0000" class="phone-input" maxlength="13" oninput="hyphen(this)"><button class="btn-rm" onclick="removeRow(this)">✕</button>';
  list.appendChild(row);
  list.lastElementChild.querySelector('input').focus();
}
function removeRow(btn){
  const list=document.getElementById('phone-list');
  if(list.children.length<=1)return;
  btn.closest('.phone-row').remove();
}
function getPhones(){return[...document.querySelectorAll('.phone-input')].map(e=>e.value.trim()).filter(Boolean);}
function getInfo(){return{
  store_name:document.getElementById('store-name').value.trim()||'탄탄제작소',
  biz_no:document.getElementById('biz-no').value.trim()||'미등록',
  store_phone:document.getElementById('store-phone').value.trim()||'고객센터 문의',
  opt_out_number:document.getElementById('opt-out').value.trim()||'080-000-0000',
};}
function buildPreview(i){
  return `(광고) [${i.store_name}] 방금 통화하신 매장 택배 접수 안내\n\n바쁜 시간, 송장 주소 일일이 타이핑하기 힘드셨죠?\n아래 링크에 주소와 이름만 '말하거나 붙여넣으면' AI가 알아서 접수증을 만들어 드립니다.\n\n➡️ 3초 만에 택배 접수하기:\nhttps://dongnebisor.com/citizen/courier\n\n--------------------------------\n[발송처 정보]\n- 상호명: ${i.store_name}\n- 사업자등록번호: ${i.biz_no}\n- 고객센터: ${i.store_phone}\n- 본 문자 신청/해지 문의는 위 고객센터로 연락 바랍니다.\n\n무료 수신거부: ${i.opt_out_number}`;
}
function doPreview(){
  document.getElementById('preview-box').textContent=buildPreview(getInfo());
}
async function doSend(){
  const phones=getPhones();
  if(!phones.length)return alert('수신 번호를 한 개 이상 입력해주세요.');
  if(!confirm(`총 ${phones.length}건 광고문자를 발송합니다.\n계속하시겠습니까?`))return;
  const btn=document.getElementById('send-btn');
  btn.disabled=true;btn.innerHTML='<div class="spinner"></div> 발송 중...';
  try{
    const resp=await fetch('/api/crm/courier-ad/send-bulk',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({phones,...getInfo(),store_id:'ADMIN'}),
      signal:AbortSignal.timeout(30000)
    });
    if(!resp.ok)throw new Error('HTTP '+resp.status);
    renderResult(await resp.json());
  }catch(e){alert('발송 오류: '+e.message);}
  finally{btn.disabled=false;btn.innerHTML='✈️ 발송하기';}
}
function renderResult(json){
  document.getElementById('result-area').style.display='block';
  document.getElementById('r-total').textContent=json.total;
  document.getElementById('r-ok').textContent=json.success;
  document.getElementById('r-fail').textContent=json.failed;
  document.getElementById('result-time').textContent=new Date().toLocaleTimeString('ko-KR');
  const list=document.getElementById('log-list');
  list.innerHTML='';
  (json.results||[]).forEach(r=>{
    list.innerHTML+=`<div class="log-row"><span class="badge ${r.success?'badge-ok':'badge-fail'}">${r.success?'성공':'실패'}</span><span style="flex:1">${r.phone}</span><span style="color:var(--muted);font-size:.78rem">${r.detail||''}</span></div>`;
  });
  document.getElementById('result-area').scrollIntoView({behavior:'smooth'});
}
</script>
</body>
</html>"""
