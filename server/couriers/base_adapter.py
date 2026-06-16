from abc import ABC, abstractmethod
from typing import Dict, Any

# 임포트 경로가 sys.path에 의해 server/ 폴더 기준일 경우 대비
try:
    from schemas.courier_schema import DongnaeBiseoStandardSchema, DongnaeBiseoTrackingSchema
except ModuleNotFoundError:
    from server.schemas.courier_schema import DongnaeBiseoStandardSchema, DongnaeBiseoTrackingSchema

class BaseCourierAdapter(ABC):
    """
    모든 택배사 어댑터가 반드시 구현해야 하는 기본 인터페이스
    """
    def __init__(self):
        # 택배사별 완전 격리된 상태 공간 (Independent Auth Layer)
        self._session_token = None
        
    @property
    @abstractmethod
    def courier_name(self) -> str:
        """어댑터의 이름을 반환 (예: 'LOGEN', 'CJ', 'COUPANG')"""
        pass

    @abstractmethod
    async def authenticate(self) -> bool:
        """
        API 인증 처리 로직을 구현합니다.
        자체 _session_token 발급 및 갱신을 통해 타 모듈의 간섭 없이 독립성을 유지해야 합니다.
        """
        pass

    @abstractmethod
    async def create_reservation(self, data: DongnaeBiseoStandardSchema) -> Dict[str, Any]:
        """
        표준 스키마 데이터를 바탕으로 실제로 택배사에 화물을 접수합니다.
        
        성공 시 {"success": True, "invoice_no": "12345"} 형식,
        실패 시 {"success": False, "error": "에러 내용"} 형식을 반환해야 합니다.
        """
        pass

    @abstractmethod
    async def process_refund(self, data: DongnaeBiseoStandardSchema) -> Dict[str, Any]:
        """
        접수 취소 요청 및 환불 처리를 수행합니다.
        """
        pass

    @abstractmethod
    async def get_tracking_status(self, tracking_no: str) -> DongnaeBiseoTrackingSchema:
        """
        송장번호를 기반으로 배송 추적 현황 마스터 폼을 반환합니다.
        """
        pass

