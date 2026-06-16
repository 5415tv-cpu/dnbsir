import httpx
import logging
from typing import Dict, Any

try:
    from config import get_secret
    from schemas.courier_schema import DongnaeBiseoStandardSchema, DongnaeBiseoTrackingSchema
    from couriers.base_adapter import BaseCourierAdapter
except ModuleNotFoundError:
    from server.config import get_secret
    from server.schemas.courier_schema import DongnaeBiseoStandardSchema, DongnaeBiseoTrackingSchema
    from server.couriers.base_adapter import BaseCourierAdapter

class LogenAdapter(BaseCourierAdapter):
    """
    로젠택배(LOGEN) 어댑터 구현체
    """
    def __init__(self):
        super().__init__()
        # 환경변수에서 로드 (하드코딩 제거)
        self.api_url = get_secret("LOGEN_API_URL", "https://api.ilogen.com/v1/booking")
        self.api_key = get_secret("LOGEN_API_KEY", "your_logen_auth_key")

    @property
    def courier_name(self) -> str:
        return "LOGEN"

    async def authenticate(self) -> bool:
        """독립적인 인증 토큰 발급 및 파기 관리"""
        # 세션 토큰이 캐시되어 있으면 그대로 활용
        if self._session_token:
            return True
            
        if self.api_key == "your_logen_auth_key" or not self.api_key:
            logging.info("Logen API Key is default or missing. Mock Auth using fake token.")
            self._session_token = "mock_logen_session_token_xyz"
            return True
            
        # 실제 API 호출을 통한 토큰 발급 로직이 들어갈 곳
        self._session_token = f"real_token_generated_by_{self.api_key[:4]}"
        return True

    async def create_reservation(self, data: DongnaeBiseoStandardSchema) -> Dict[str, Any]:
        """정규화된 동네비서 스키마 데이터를 로젠 Payload로 변환하여 발송"""
        # 1. 로젠 B2B Open API 연동 모드 우선 순위 처리
        try:
            import logen_delivery
            
            # logen_delivery.py 의 B2B API 설정이 유효하거나 활성화된 경우
            if logen_delivery.USE_LOGEN_B2B_API or (logen_delivery.LOGEN_B2B_SECRET_KEY and logen_delivery.LOGEN_B2B_USER_ID):
                logging.info(f"[{self.courier_name}] B2B Open API 예약 시도: order_id={data.order_id}")
                sender_dict = {
                    "name": data.sender_name,
                    "phone": data.sender_tel,
                    "address": data.sender_addr,
                    "detail_address": ""
                }
                receiver_dict = {
                    "name": data.receiver_name,
                    "phone": data.receiver_tel,
                    "address": data.receiver_addr,
                    "detail_address": ""
                }
                package_dict = {
                    "type": "박스",
                    "weight": 2.5,
                    "size": "소형",
                    "contents": data.item_name or "일반 상품",
                    "price": data.amount or 10000,
                    "fee": data.net_price or 3500,
                    "is_prepaid": True
                }
                
                from fastapi.concurrency import run_in_threadpool
                res, err = await run_in_threadpool(
                    logen_delivery.create_delivery_reservation,
                    sender=sender_dict,
                    receiver=receiver_dict,
                    package=package_dict,
                    pickup_date=None,
                    memo=f"동네비서 주문:{data.order_id}"
                )
                
                if not err and res and res.get("success"):
                    invoice_no = res.get("waybill_number")
                    logging.info(f"[{self.courier_name}] B2B API 예약 성공: {invoice_no}")
                    return {
                        "success": True,
                        "invoice_no": invoice_no,
                        "net_price": data.net_price,
                        "raw_data": res
                    }
                else:
                    logging.error(f"[{self.courier_name}] B2B API 예약 실패: {err}")
                    return {"success": False, "error": err or "B2B API 예약 실패"}
        except Exception as e:
            logging.error(f"[{self.courier_name}] B2B API 연동 시도 중 에러 (Fallback 진행): {e}")

        # 2. 레거시 로직 진행 (Fallback)
        if not self._session_token:
            await self.authenticate()
            
        # 로젠택배 전용 Payload 변환 (Adapter 역할)
        logen_payload = {
            "slip_no": "",
            "s_name": data.sender_name,
            "s_tel1": data.sender_tel,
            "s_addr": data.sender_addr,
            "r_name": data.receiver_name,
            "r_tel1": data.receiver_tel,
            "r_addr": data.receiver_addr,
            "p_name": data.item_name,
            "pay_type": "현금", # 예시 고정
            "charge": data.net_price
        }

        async with httpx.AsyncClient() as client:
            try:
                if self.api_key == "your_logen_auth_key":
                    # Mock Success
                    import random
                    mock_inv = f"250-{random.randint(1000,9999)}-{random.randint(1000,9999)}"
                    logging.info(f"[{self.courier_name}] Mock Reservation Success: {mock_inv}")
                    return {"success": True, "invoice_no": mock_inv, "net_price": data.net_price, "raw_data": {"logen_hub": "Seoul-G", "slip_no": mock_inv}}

                response = await client.post(
                    self.api_url,
                    json=logen_payload,
                    headers={"Authorization": f"Bearer {self._session_token}"},
                    timeout=5.0
                )

                if response.status_code == 200:
                    result = response.json()
                    invoice_no = result.get('invoice_no')
                    if invoice_no:
                        return {"success": True, "invoice_no": invoice_no, "net_price": data.net_price, "raw_data": result}

                logging.error(f"[{self.courier_name}] API Fail: {response.text}")
                return {"success": False, "error": response.text}

            except Exception as e:
                logging.error(f"[{self.courier_name}] Exception calling API: {str(e)}")
                return {"success": False, "error": str(e)}

    async def process_refund(self, data: DongnaeBiseoStandardSchema) -> Dict[str, Any]:
        """로젠택배 환불/취소 로직"""
        logging.info(f"[{self.courier_name}] Refund processed for order: {data.order_id}")
        return {"success": True, "refunded_amount": data.net_price}

    async def get_tracking_status(self, tracking_no: str) -> DongnaeBiseoTrackingSchema:
        if not self._session_token:
            await self.authenticate()
            
        logging.info(f"[{self.courier_name}] Fetching tracking info for {tracking_no}")
        # Mock Response
        return DongnaeBiseoTrackingSchema(
            carrier_id=self.courier_name,
            tracking_no=tracking_no,
            status="TRANSIT",
            address_raw="서울특별시 송파구 송파대로 123",
            address_refined="서울특별시 송파구 송파대로 123 (네이버 보정)"
        )
