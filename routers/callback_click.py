"""
콜백 클릭 추적 라우터 — /c
SMS에 담긴 링크를 클릭하면 이 라우트가:
1. 클릭 시각을 callback_funnel에 기록
2. 고객 전화번호(ref=)를 수거 후 파라미터 제거
3. 가게 유형에 따라 적절한 페이지로 리다이렉트
"""
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
import db_sqlite as db
import re

router = APIRouter()

_PHONE_RE = re.compile(r'0\d{9,10}')

def _clean_phone(raw: str) -> str:
    """숫자만 추출"""
    return re.sub(r'[^0-9]', '', raw or '')


@router.get("/c")
async def callback_click_tracker(
    request: Request,
    id: str = "",       # url_slug 또는 store_id
    ref: str = "",      # 고객 전화번호 (마스킹 후 저장)
):
    """
    콜백 SMS 딥링크 진입점.
    클릭 기록 후 즉시 깔끔한 URL로 리다이렉트.
    고객 브라우저에는 파라미터 없는 주소가 보임.
    """
    source_ip = request.client.host if request.client else ""

    # 1) 가게 조회
    store = None
    if id:
        store = db.get_store_by_slug(id)

    store_id = (store.get("store_id") if store else None) or id or "UNKNOWN"

    # 2) 클릭 기록 (고객번호 마스킹 저장)
    customer_phone = _clean_phone(ref)
    if customer_phone:
        try:
            db.log_callback_click(
                customer_phone=customer_phone,
                store_id=store_id,
                source_ip=source_ip,
            )
        except Exception as e:
            print(f"[/c] 클릭 기록 실패: {e}")

    # 3) 리다이렉트 목적지 — DB 템플릿 우선, 없으면 기본값
    if store:
        slug     = store.get("url_slug") or store_id
        category = store.get("category", "기타")

        try:
            tmpl = db.get_callback_template(category)
            dest = tmpl.get("redirect_path", "/market")
            # {slug} 플레이스홀더 치환
            dest = dest.replace("{slug}", slug)
        except Exception as _e:
            print(f"[/c] 템플릿 조회 실패: {_e}")
            # 하드코딩 폴백
            role = store.get("role", "")
            if role in ("logistics", "courier") or category == "택배":
                dest = "/delivery/request"
            else:
                dest = f"/market?focus={slug}"
    else:
        dest = "/market"

    return RedirectResponse(url=dest, status_code=302)
