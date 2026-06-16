
import httpx
import logging
import db_manager as db
from sms_manager import send_alimtalk

# 로젠택배 API 설정 (정석 가이드)
LOGEN_API_URL = "https://api.ilogen.com/v1/booking"
LOGEN_API_KEY = "your_logen_auth_key"

# 결제 수단별 수수료 설정값 (정석 변수화)
FEE_RATES = {
    "CASH": 0.00,      # 현금
    "CARD": 0.03,      # 신용카드
    "PAY": 0.037,      # 카카오/네이버페이
    "TRANSFER": 0.015  # 실시간 계좌이체
}

def calculate_precise_settlement(amount: int, method: str):
    """
    [결제금액]과 [결제수단]을 받아 1원 단위까지 정산합니다.
    """
    # 1. 수수료율 추출 (등록되지 않은 수단은 기본 3% 적용)
    fee_rate = FEE_RATES.get(method, 0.03)

    # 2. 사장님 마진(10%) 계산 및 반올림
    my_margin = round(amount * 0.1)

    # 3. 결제 수수료 계산 및 반올림
    payment_fee = round(amount * fee_rate)

    # 4. 로젠택배 전송액 (최종 배송비)
    logen_amount = amount - (my_margin + payment_fee)

    return {
        "method": method,
        "total": amount,
        "margin": my_margin,
        "fee": payment_fee,
        "logen_net": logen_amount
    }

async def send_to_logen(order_id: str):
    """
    결제 완료된 주문을 로젠택배로 전송하고 운송장을 발급받습니다.
    """
    # 0. 주문 정보 조회
    order_data = db.get_order_by_id(order_id)
    if not order_data:
        logging.error(f"Order not found: {order_id}")
        return False

    # 1. 로젠 표준 규격 데이터 매핑
    sender_name = order_data.get('sender_name', '발송인')
    sender_tel = order_data.get('sender_tel', '010-0000-0000')
    sender_addr = order_data.get('sender_addr', '주소 미입력')

    receiver_name = order_data.get('receiver_name', '수령인')
    receiver_tel = order_data.get('customer_phone', '010-0000-0000')
    receiver_addr = order_data.get('receiver_addr', '주소 미입력')

    product_name = order_data.get('item_name', '일반 물품')
    total_amount = int(order_data.get('amount', 0))
    payment_method = order_data.get('payment_method', 'CARD')

    # 정산 금액 계산 (Precise)
    settlement = calculate_precise_settlement(total_amount, payment_method)
    logen_price = settlement['logen_net']

    logen_payload = {
        "slip_no": "", # 신규 접수는 공란
        "s_name": sender_name,
        "s_tel1": sender_tel,
        "s_addr": sender_addr,
        "r_name": receiver_name,
        "r_tel1": receiver_tel,
        "r_addr": receiver_addr,
        "p_name": product_name,
        "pay_type": "현금", # 로젠 쪽에는 현금으로 통일하거나 계약에 따름
        "charge": logen_price # 정산된 택배비 전송
    }

    async with httpx.AsyncClient() as client:
        try:
            if LOGEN_API_KEY == "your_logen_auth_key":
                # Mock Success
                import random
                mock_inv = f"250-{random.randint(1000,9999)}-{random.randint(1000,9999)}"
                db.update_order_tracking(order_id, mock_inv)
                logging.info(f"Logen Mock Success: {mock_inv}, Price: {logen_price}, Fee: {settlement['fee']}")
                return True

            response = await client.post(
                LOGEN_API_URL,
                json=logen_payload,
                headers={"Authorization": f"Bearer {LOGEN_API_KEY}"},
                timeout=5.0
            )

            if response.status_code == 200:
                result = response.json()
                invoice_no = result.get('invoice_no')
                if invoice_no:
                    db.update_order_tracking(order_id, invoice_no)
                    return True

            logging.error(f"Logen API Fail: {response.text}")
            return False

        except Exception as e:
            logging.error(f"로젠택배 접수 실패: {str(e)}")
            return False

async def process_refund(order_id: str):
    """
    주문 취소/환불 처리
    """
    order_data = db.get_order_by_id(order_id)
    if not order_data:
        return False

    total_amount = int(order_data.get('amount', 0))
    payment_method = order_data.get('payment_method', 'CARD')

    settlement = calculate_precise_settlement(total_amount, payment_method)

    # 환불 시: 수수료 + 마진 차감 후 환불
    deducted = settlement['margin'] + settlement['fee']
    refund_amt = settlement['logen_net']

    # 로그 기록
    logging.info(f"Refund Process: Order={order_id}, Refund={refund_amt}, Deducted={deducted}")

    # 고객에게 환불 안내 알림톡 발송
    cust_phone = order_data.get('customer_phone') or order_data.get('sender_tel')
    if cust_phone:
        msg = f"주문이 취소되었습니다.\n환불 예정 금액: {refund_amt}원\n(차감: {deducted}원)"
        send_alimtalk(cust_phone, msg, template_id="PAY_REFUND")

    return True
