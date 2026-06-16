import logging
import asyncio
from typing import Dict, Any, List

try:
    from config import get_secret
    from schemas.courier_schema import DongnaeBiseoStandardSchema, DongnaeBiseoTrackingSchema
    from couriers.logen_adapter import LogenAdapter
    from couriers.mock_adapters import CoupangAdapter, LotteAdapter, CjAdapter
    from couriers.hanjin_adapter import HanjinAdapter
except ModuleNotFoundError:
    from server.config import get_secret
    from server.schemas.courier_schema import DongnaeBiseoStandardSchema, DongnaeBiseoTrackingSchema
    from server.couriers.logen_adapter import LogenAdapter
    from server.couriers.mock_adapters import CoupangAdapter, LotteAdapter, CjAdapter
    from server.couriers.hanjin_adapter import HanjinAdapter

class CourierManager:
    """
    모든 택배사 어댑터를 통합 관리하며, 특정 API 장애 시 우선순위에 따라 대체 택배사(Fallback)를 자동으로 지정합니다.
    """
    def __init__(self):
        self.adapters = {
            "LOGEN": LogenAdapter(),
            "COUPANG": CoupangAdapter(),
            "LOTTE": LotteAdapter(),
            "CJ": CjAdapter(),
            "HANJIN": HanjinAdapter()
        }
        
        # 환경변수에서 쉼표로 구분된 우선순위 로드 (예: "LOGEN,COUPANG,CJ")
        priority_str = get_secret("COURIER_PRIORITY", "LOGEN,COUPANG,LOTTE,CJ")
        self.priority = [p.strip().upper() for p in priority_str.split(",") if p.strip()]

    async def reserve_delivery(self, data: DongnaeBiseoStandardSchema) -> Dict[str, Any]:
        """
        우선순위 순으로 택배 접수를 시도하며, 성공 시 즉각 반환합니다.
        전부 실패 시 에러를 반환합니다.
        """
        for courier_name in self.priority:
            adapter = self.adapters.get(courier_name)
            if not adapter:
                continue
                
            logging.info(f"[CourierManager] Trying {courier_name} for order {data.order_id}...")
            
            # 1. 간단 인증 모의 테스트 (옵션)
            is_valid = await adapter.authenticate()
            if not is_valid:
                logging.warning(f"[CourierManager] {courier_name} Auth failed. Skipping.")
                continue
                
            # 2. 접수 시도
            result = await adapter.create_reservation(data)
            if result.get("success"):
                invoice_no = result.get('invoice_no')
                logging.info(f"[CourierManager] SUCCESS using {courier_name}. Invoice: {invoice_no}")
                
                # 3. 마스터 DB (자체 장부) 동기화
                try:
                    import db_manager as db
                    # RDBMS에 택배 예약 정보 백업 저장
                    db.save_delivery({
                        "store_id": "api_user",
                        "sender_name": "API_Reservation",
                        "receiver_name": data.receiver_name,
                        "receiver_phone": data.receiver_tel,
                        "item_name": "Delivery Booking",
                        "status": "PENDING",
                        "tracking_code": str(invoice_no),
                        "fee": result.get("net_price", 0)
                    })
                except Exception as e:
                    logging.error(f"[CourierManager] DB Sync Error: {e}")
                
                return {
                    "success": True,
                    "courier": courier_name,
                    "invoice_no": invoice_no,
                    "net_price": result.get("net_price")
                }
            else:
                logging.error(f"[CourierManager] FAILED using {courier_name}. Error: {result.get('error')}")
                # 다음 우선순위 어댑터로 진행 (모듈 독립 작동 / Fallback)

        return {"success": False, "error": "All automated courier APIs failed."}

    async def process_refund(self, assigned_courier: str, data: DongnaeBiseoStandardSchema) -> Dict[str, Any]:
        """기존 할당된 택배사에 대해 취소 처리를 수행합니다."""
        adapter = self.adapters.get(assigned_courier.upper())
        if adapter:
            return await adapter.process_refund(data)
        return {"success": False, "error": f"Unknown courier {assigned_courier}"}

    async def fetch_all_tracking_statuses(self, tracking_requests: List[Dict[str, str]]) -> List[Any]:
        """
        병렬 비동기 추적 (Asynchronous Parallel Processing)
        tracking_requests = [{"carrier": "LOGEN", "tracking_no": "123"}, {"carrier": "COUPANG", "tracking_no": "456"}]
        응답이 느린 API가 있어도 gather를 통해 영향을 분산시킵니다.
        """
        async def fetch_single(req):
            courier = req.get("carrier", "").upper()
            t_no = req.get("tracking_no")
            adapter = self.adapters.get(courier)
            if not adapter:
                return Exception(f"Unknown courier {courier}")
            return await adapter.get_tracking_status(t_no)

        tasks = [fetch_single(req) for req in tracking_requests]
        # return_exceptions=True 로 한 API 오류가 전체 응답 취소를 일으키는 상황 방지
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

