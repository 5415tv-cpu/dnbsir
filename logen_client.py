"""
로젠 마이크로서비스 클라이언트
Django 앱에서 import해서 사용

사용법:
    from logen_client import create_waybill
    result = await create_waybill(order_data)
    if result["success"]:
        slip_no = result["slip_no"]
"""
import httpx
import logging

logger = logging.getLogger(__name__)

LOGEN_SERVICE_URL = "http://localhost:8001"


async def create_waybill(order: dict) -> dict:
    """
    로젠 마이크로서비스에 운송장 등록 요청

    order = {
        "receiver_name": "김철수",
        "receiver_phone": "01012345678",
        "receiver_addr1": "서울특별시 강남구 테헤란로 152",
        "receiver_addr2": "강남파이낸스센터",
        "receiver_zipcode": "06236",
        "item_name": "농산물",
        "item_qty": 1,
        "item_weight": 3,
        "item_price": 30000,
        "message": "부재시 경비실",
    }

    Returns:
        {"success": True, "slip_no": "44662755605", "seq": "16", ...}
    """
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{LOGEN_SERVICE_URL}/waybill/create",
                json=order
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.TimeoutException:
        logger.error("[로젠] 타임아웃 (120초 초과)")
        return {"success": False, "error": "타임아웃"}
    except Exception as e:
        logger.error(f"[로젠] 오류: {e}")
        return {"success": False, "error": str(e)}


def create_waybill_sync(order: dict) -> dict:
    """동기 버전 (일반 view에서 사용)"""
    import asyncio
    return asyncio.run(create_waybill(order))
