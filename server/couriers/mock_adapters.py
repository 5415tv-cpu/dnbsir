import logging
import random
import asyncio
from typing import Dict, Any

try:
    from schemas.courier_schema import DongnaeBiseoStandardSchema, DongnaeBiseoTrackingSchema
    from couriers.base_adapter import BaseCourierAdapter
except ModuleNotFoundError:
    from server.schemas.courier_schema import DongnaeBiseoStandardSchema, DongnaeBiseoTrackingSchema
    from server.couriers.base_adapter import BaseCourierAdapter

class CoupangAdapter(BaseCourierAdapter):
    @property
    def courier_name(self) -> str:
        return "COUPANG"

    async def authenticate(self) -> bool:
        if not self._session_token:
            self._session_token = "mock_token_coupang"
        return True

    async def create_reservation(self, data: DongnaeBiseoStandardSchema) -> Dict[str, Any]:
        logging.warning(f"[{self.courier_name}] Mock Reservation: {data.order_id}")
        return {
            "success": True, 
            "invoice_no": f"C-100-{random.randint(1000,9999)}",
            "raw_data": {"coupang_meta": "fast_delivery", "assigned_hub": "C-11"}
        }

    async def process_refund(self, data: DongnaeBiseoStandardSchema) -> Dict[str, Any]:
        return {"success": True}

    async def get_tracking_status(self, tracking_no: str) -> DongnaeBiseoTrackingSchema:
        await self.authenticate()
        logging.info(f"[{self.courier_name}] Fetching {tracking_no} (Expect 3s latency)")
        #의도적인 레이턴시 추가하여 Async 테스트 목적 달성
        await asyncio.sleep(3.0)
        return DongnaeBiseoTrackingSchema(
            carrier_id=self.courier_name,
            tracking_no=tracking_no,
            status="DELIVERED",
            address_raw="제주특별자치도 제주시",
            address_refined="제주특별자치도 제주시 (보정됨)"
        )

class LotteAdapter(BaseCourierAdapter):
    @property
    def courier_name(self) -> str:
        return "LOTTE"

    async def authenticate(self) -> bool:
        if not self._session_token:
            self._session_token = "mock_token_lotte"
        return True

    async def create_reservation(self, data: DongnaeBiseoStandardSchema) -> Dict[str, Any]:
        logging.warning(f"[{self.courier_name}] Mock Reservation: {data.order_id}")
        return {
            "success": True, 
            "invoice_no": f"L-101-{random.randint(1000,9999)}",
            "raw_data": {"lotte_route": "Terminal_B", "special_care": False}
        }

    async def process_refund(self, data: DongnaeBiseoStandardSchema) -> Dict[str, Any]:
        return {"success": True}
        
    async def get_tracking_status(self, tracking_no: str) -> DongnaeBiseoTrackingSchema:
        await self.authenticate()
        return DongnaeBiseoTrackingSchema(
            carrier_id=self.courier_name,
            tracking_no=tracking_no,
            status="PENDING",
            address_raw="경기도 성남시 분당구",
            address_refined="경기도 성남시 분당구"
        )

class CjAdapter(BaseCourierAdapter):
    @property
    def courier_name(self) -> str:
        return "CJ"

    async def authenticate(self) -> bool:
        if not self._session_token:
            self._session_token = "mock_token_cj"
        return True

    async def create_reservation(self, data: DongnaeBiseoStandardSchema) -> Dict[str, Any]:
        logging.warning(f"[{self.courier_name}] Mock Reservation: {data.order_id}")
        return {
            "success": True, 
            "invoice_no": f"CJ-102-{random.randint(1000,9999)}",
            "raw_data": {"cj_zone": "K-22", "scan_code": "0000-xxxx-12"}
        }

    async def process_refund(self, data: DongnaeBiseoStandardSchema) -> Dict[str, Any]:
        return {"success": True}

    async def get_tracking_status(self, tracking_no: str) -> DongnaeBiseoTrackingSchema:
        await self.authenticate()
        return DongnaeBiseoTrackingSchema(
            carrier_id=self.courier_name,
            tracking_no=tracking_no,
            status="TRANSIT",
            address_raw="대전광역시 유성구",
            address_refined="대전광역시 유성구"
        )

