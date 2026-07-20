# logen_crypto.py
import math

def encrypt_logen_fee(base_fee: int) -> str:
    """
    로젠택배 표준 운송장 운임 암호화 이식 (Margin Hiding)
    기사님이나 제3자가 운임의 원가를 정확히 알 수 없도록 마스킹 처리합니다.
    """
    if base_fee <= 0:
        return "신용(착불)"
        
    # 로젠 앱 설정에 있는 '배송비 별표(***) 처리' 옵션을 기본값으로 고정
    return "***"

def calculate_margin(total_fee: int, pg_fee_rate: float = 0.033) -> dict:
    """
    이중 장부 로직
    고객 결제 총액(total_fee)에서 플랫폼 서비스 이용료(1,000원)와 
    PG 수수료(3.3%)를 분리하여 사장님 순수익 및 로젠 전송용 원가(base_fee)를 산출합니다.
    (PG 수수료는 기사님 정산금에서 실비로 추가 공제됨)
    """
    platform_margin = 1000
    
    if total_fee <= platform_margin:
        return {
            "total_fee": total_fee,
            "base_fee": total_fee,
            "platform_margin": 0,
            "pg_fee": int(total_fee * pg_fee_rate),
            "net_profit": 0
        }
        
    pg_fee = int(total_fee * pg_fee_rate)
    # 기사님 정산 기준 원가(base_fee)는 실제로는 1000원과 PG수수료를 뺀 금액이지만, 
    # 송장에 찍히는 로젠 운임은 통상적으로 PG수수료 공제 전인 (total_fee - 1000)으로 취급할 수 있음.
    # 송장에는 4,000으로 찍히고 최종 지급은 3,835로 지급되는 구조입니다.
    base_fee = total_fee - platform_margin 
    
    net_profit = platform_margin # 사장님 순수익은 1원의 손해도 없는 1000원 고정!
    
    return {
        "total_fee": total_fee,
        "base_fee": base_fee,
        "platform_margin": platform_margin,
        "pg_fee": pg_fee,
        "net_profit": net_profit
    }
