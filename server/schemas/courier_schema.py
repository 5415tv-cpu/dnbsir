from pydantic import BaseModel, Field
from typing import Optional

class DongnaeBiseoStandardSchema(BaseModel):
    """
    동네비서 표준 스키마 (Courier Standard)
    모든 택배사 어댑터로 전달되기 전, 각 입력값들을 이 스키마로 변환하여 정규화합니다.
    """
    order_id: str = Field(description="내부 주문 ID")
    
    # 발송인 정보
    sender_name: str = Field(..., description="발송인 이름")
    sender_tel: str = Field(..., description="발송인 연락처")
    sender_addr: str = Field(..., description="발송지 전체 주소")
    
    # 수진인 정보
    receiver_name: str = Field(..., description="수령인 이름")
    receiver_tel: str = Field(..., description="수령인 연락처")
    receiver_addr: str = Field(..., description="수령지 전체 주소")
    
    # 물품 정보
    item_name: str = Field(default="일반 물품", description="배송 물품 명칭")
    amount: int = Field(default=0, description="최종 결제 금액 (배송비 포함)")
    payment_method: str = Field(default="CARD", description="결제 수단 (CASH, CARD, PAY, TRANSFER 등)")
    
    # 정산 관련 (옵션)
    margin: Optional[int] = Field(default=0, description="동네비서 수수료/마진")
    payment_fee: Optional[int] = Field(default=0, description="PG사 수수료")
    net_price: Optional[int] = Field(default=0, description="순수 택배비 (마운트 - 마진 - PG수수료)")

    class Config:
        schema_extra = {
            "example": {
                "order_id": "ORD-123",
                "sender_name": "홍길동",
                "sender_tel": "010-1234-5678",
                "sender_addr": "서울 강남구 송파대로 123",
                "receiver_name": "김철수",
                "receiver_tel": "010-9876-5432",
                "receiver_addr": "부산광역시 해운대구 센터길 45",
                "item_name": "유기농 사과",
                "amount": 5500,
                "payment_method": "CARD"
            }
        }

class DongnaeBiseoTrackingSchema(BaseModel):
    """
    동네비서 추적 마스터 스키마 (Master Tracking Schema)
    택배 배송 상태 조회의 공통 분모 및 데이터 규격을 정의합니다.
    """
    carrier_id: str = Field(..., description="택배사 구분 (LOGEN, CJ, COUPANG 등)")
    tracking_no: str = Field(..., description="송장 번호 (공통 식별자)")
    status: str = Field(..., description="배송 상태 (PENDING, TRANSIT, DELIVERED 등)")
    address_raw: str = Field(..., description="원본 배송 주소")
    address_refined: Optional[str] = Field(None, description="네이버 지도 등으로 보정된 정밀 주소")

    @property
    def composite_key(self) -> str:
        """데이터 충돌(Data Collision)을 막는 절대 고유 키 반환"""
        return f"{self.carrier_id.upper()}_{self.tracking_no}"
