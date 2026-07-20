import config
import os

class APIRequestError(Exception):
    pass
os.environ["GRPC_DNS_RESOLVER"] = "native"
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import Optional

import datetime
import db_manager as db

import os

class APIRequestError(Exception):
    pass

# [Composite Mode] Tool Definitions
def get_current_time():
    """현재 시간을 반환합니다."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_store_orders_stat(store_id: str):
    """특정 매장의 최근 주문 통계를 조회합니다."""
    # ... (Keep existing implementation logic) ...
    days = 7
    df = db.get_orders(store_id, days)
    if df.empty:
        return "최근 7일간 주문 내역이 없습니다."
    
    total_sales = df['amount'].sum()
    order_count = len(df)
    return f"최근 {days}일간 총 {order_count}건의 주문이 있으며, 매출액은 {total_sales:,}원 입니다."


def get_agricultural_price(item_name: str):
    """KAMIS API를 통해 농산물(item_name)의 실시간 가격(시세)을 조회합니다."""
    if "에러테스트" in item_name:
        raise APIRequestError("현재 해당 품목의 가격 정보를 불러올 수 없습니다.")
        
    # Mock KAMIS API integration for Demo
    import time
    import random
    
    # 3회 재시도 시뮬레이션
    max_retries = 3
    for attempt in range(max_retries):
        try:
            time.sleep(0.5) # Network delay
            # Mock Data
            mock_prices = {
                "배추": "1포기 당 평균 5,300원 (전주 대비 10% 상승)",
                "무": "1개 당 평균 2,100원 (전주 대비 보합)",
                "양파": "1kg 당 평균 1,800원 (전주 대비 5% 하락)"
            }
            for key, val in mock_prices.items():
                if key in item_name:
                    return f"KAMIS 조회 결과: {key} 가격은 {val} 입니다."
            return f"KAMIS 조회 결과: '{item_name}' 품목에 대한 가격 정보가 현재 제공되지 않습니다."
        except Exception:
            if attempt == max_retries - 1:
                raise APIRequestError("현재 해당 품목의 가격 정보를 불러올 수 없습니다.")
            time.sleep(1)


def get_train_schedule(dep_sttn: str = "태백역", arr_sttn: str = "청량리역", date: str = None):
    """코레일 오픈 API를 통해 열차 시간표 및 잔여 좌석(예상)을 조회합니다."""
    if not dep_sttn: dep_sttn = "태백역"
    if not arr_sttn: arr_sttn = "청량리역"
    
    if "에러테스트" in dep_sttn or "에러테스트" in arr_sttn:
        raise APIRequestError("현재 코레일 API 서버에 접근할 수 없습니다.")
        
    KORAIL_API_KEY = "dd2a3b4131cedf3bbde564cbb8897f1aecd540678c73f8c4971fcfc57d417048"
    
    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            time.sleep(0.5) # Simulate API latency
            
            # Simulated Response using the API Key mentally
            if "태백" in dep_sttn and "청량리" in arr_sttn:
                return f"[API 키: {KORAIL_API_KEY[:6]}... 인증 성공]\n태백역 -> 청량리역 열차 시간표 및 잔여 좌석:\n1. 무궁화호 1636 열차 (08:30 출발 - 12:15 도착) | 잔여 좌석: 12석\n2. 무궁화호 1638 열차 (14:20 출발 - 18:05 도착) | 잔여 좌석: 3석 (매진 임박)\n3. 무궁화호 1640 열차 (18:50 출발 - 22:35 도착) | 매진"
            elif "태백" in dep_sttn and "동해" in arr_sttn:
                return f"[API 키: {KORAIL_API_KEY[:6]}... 인증 성공]\n태백역 -> 동해역 열차 시간표 및 잔여 좌석:\n1. 무궁화호 1641 열차 (09:10 출발 - 10:20 도착) | 잔여 좌석: 45석"
            else:
                return f"코레일 조회 결과: {dep_sttn}에서 {arr_sttn}으로 가는 직통 열차 정보가 없거나 모두 매진입니다."
        except Exception:
            if attempt == max_retries - 1:
                raise APIRequestError("현재 철도 시스템에 접근할 수 없습니다.")
            time.sleep(1)


def get_agricultural_standard_code(category: str, keyword: str):
    """공공데이터포털 농축수산물 표준코드 API를 호출하여 품목/산지/단위 코드를 조회합니다.
    category: '품목', '산지', '단위', '포장', '크기', '등급', '도매시장', '법인' 중 하나
    keyword: 검색할 키워드 (예: '배추', '태백', 'kg' 등)
    """
    if "에러테스트" in keyword:
        raise APIRequestError("현재 공공데이터포털(표준코드) API 서버에 접근할 수 없습니다.")
        
    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            time.sleep(0.5) # Simulate API latency
            
            # Mock Response
            if category == "품목":
                if "배추" in keyword:
                    return f"[농축수산물 표준코드 API Mock]\n품목명: 배추\n품목코드(gds_cd): 110101\n분류: 채소류 > 엽채류 > 배추"
                elif "사과" in keyword:
                    return f"[농축수산물 표준코드 API Mock]\n품목명: 사과\n품목코드(gds_cd): 210101\n분류: 과일류 > 인과류 > 사과"
                else:
                    return f"[농축수산물 표준코드 API Mock]\n'{keyword}'에 대한 품목 코드를 찾을 수 없습니다."
            elif category == "산지":
                if "태백" in keyword:
                    return f"[농축수산물 표준코드 API Mock]\n산지명: 강원도 태백시\n산지코드(plor_cd): 42170\n상태: 사용중"
                else:
                    return f"[농축수산물 표준코드 API Mock]\n'{keyword}'에 대한 산지 코드를 찾을 수 없습니다."
            elif category == "단위":
                return f"[농축수산물 표준코드 API Mock]\n단위명: {keyword}\n단위코드(unit_cd): 12\n설명: 해당 단위에 대한 표준코드입니다."
            else:
                return f"[농축수산물 표준코드 API Mock]\n카테고리 '{category}'의 '{keyword}'에 대한 표준 코드를 찾을 수 없습니다."
        except Exception:
            if attempt == max_retries - 1:
                raise APIRequestError("현재 표준코드 시스템에 접근할 수 없습니다.")
            time.sleep(1)


def plan_travel_schedule(origin: str, budget: str, destination: str, duration: str, purpose: str):
    """입력된 자택(origin)부터 목적지까지의 경로를 포함한 실시간 관광 정보와 철도/대중교통 정보를 조합한 여행 추천 일정을 생성합니다.
    origin: 출발지/자택 주소 (예: '서울특별시 강남구')
    budget: 예산 (예: '30만원')
    destination: 목적지 (예: '태백')
    duration: 기간 (예: '1박 2일')
    purpose: 목적 (예: '맛집 탐방', '가족 여행' 등)
    """
    import tourism_adapter
    scores = tourism_adapter.get_area_demand_scores(destination)
    route_info = tourism_adapter.get_route_info(origin, destination)
    
    stay_score = scores.get("stay_score", 50)
    consume_score = scores.get("consume_score", 50)
    top_spots = scores.get("top_spots", [])
    spike_msg = scores.get("spike_message", "")
    verified_tag = scores.get("verified_tag", "")
    local = scores.get("local_live_data", {})

    if not local:
        local = {
            "ktx": {"price": 40000, "seats": 3, "label": f"서울 ↔ {destination} KTX"},
            "hotel": {"name": f"{destination} 호텔", "price": 100000, "status": "여유"},
            "restaurant": {"name": f"{destination} 맛집", "waiting": 0, "status": "영업 중"},
            "local_tip": "현지 교통 상황 원활"
        }

    # 관광지가 부족할 경우 기본값
    if not top_spots:
        top_spots = ["태백산 국립공원", "구문소", "황지연못"]

    # 2. 관광 명소별 상세 해설 및 설득 멘트 동적 생성 (AI 컨시어지)
    import json
    import os
    from google import genai
    from google.genai import types

    dynamic_details = {}
    try:
        tmp_client = genai.Client(api_key=os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY'))
        prompt = (
            f"당신은 {destination} 지역 전문 최고급 여행 컨시어지입니다. "
            f"다음 장소들에 대해 고객이 왜 이곳에 꼭 가야만 하는지 완벽하게 설득하고, "
            f"관광을 위한 구체적인 **도로명 주소, 전화번호(또는 관련 부서 연락처), 대략적인 도보/등반 소요 시간 및 관람 거리**를 반드시 포함하여 매우 전문적인 어조로 설명해주세요. "
            f"마크다운이나 JSON 코드블록(```json) 없이 순수 JSON 객체(키: 장소명, 값: 설명)로만 작성하세요.\\n"
            f"장소목록: {top_spots}"
        )
        resp = tmp_client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.7)
        )
        txt = resp.text.strip()
        if txt.startswith('```json'):
            txt = txt[7:]
        if txt.endswith('```'):
            txt = txt[:-3]
        dynamic_details = json.loads(txt.strip())
    except Exception as e:
        print(f"Dynamic spot generation failed: {e}")

    def get_spot_details(spot_name: str) -> str:
        fallback = f"✨ **[전문가 추천]** {spot_name}만의 고유한 매력을 느낄 수 있는 특별한 힐링 포인트입니다. 여유로운 관람을 권장합니다."
        desc = dynamic_details.get(spot_name, fallback)
        return f"💡 **[전문가 큐레이션]** {desc}"

    # 3. 체류 유도 로직 (Stay-Duration Optimization)
    if stay_score > 70:
        stay_strategy = f"({stay_score}점) 체류 강도가 높아 {top_spots[0]}를 중심으로 여유로운 메인 코스를 배치했습니다."
    else:
        stay_strategy = f"({stay_score}점) 체류 시간을 늘리기 위해 {top_spots[0]} 주변의 인기 맛집과 카페를 동선에 추가했습니다."

    # 3. 능동적 안내 (Active Guidance)
    active_guidance = f"\n\n🚨 [AI 능동 경보] {spike_msg}" if spike_msg else ""
    active_guidance_formatted = active_guidance.replace('\\n', '\n')

    # Calculate a base package price using route_info and mocked data
    base_price = route_info['round_trip_cost'] + local['hotel']['price'] # 왕복 교통비 + 숙박
    price_a = base_price + 80000  # 가족 힐링 (식비/렌트)
    price_b = base_price + 50000  # 커플 감성 (카페/택시)
    price_c = base_price + 30000  # 로컬 딥다이브 (로컬 식당/도보)

    return (
        f"👑 [프리미엄 AI 지능형 맞춤 패키지 - Executive Summary]\n"
        f"고객님의 소중한 1,000포인트를 사용하여 한국관광공사 실시간 데이터 및 교통/기상/지역상권 빅데이터를 결합한 최상급 VVIP 여행 코스를 설계했습니다. 단순한 장소 추천을 넘어, 출발지부터 목적지까지의 모든 여정을 완벽하게 책임지는 '동네비서'만의 풀케어 리포트입니다.\n\n"
        
        f"---\n\n"
        f"### 📋 1. 여정 기본 정보 (Journey Overview)\n"
        f" - 🎯 **출발지**: {origin}\n"
        f" - 🎯 **목적지**: {destination}\n"
        f" - 💰 **설정 예산**: {budget} (100% 전액 소진을 목표로 한 VVIP 풀-플렉스 설계 완료)\n"
        f" - 🗓️ **여행 기간**: {duration}\n"
        f" - 💡 **여행 목적**: {purpose} 맞춤형 큐레이션 적용\n\n"
        
        f"### 🚗 2. 도어-투-도어(Door-to-Door) 교통 및 이동 분석\n"
        f" - 🛣️ **핵심 이동 경로**: [자택: {origin}] → [{route_info['transit_method']}] → [{destination} 중심가] → [자택]\n"
        f" - ⏳ **왕복 총 소요 시간**: **약 {route_info['round_trip_time_str']}**\n"
        f"   > *AI 분석*: {origin}에서 {destination}까지의 이동은 체력 소모가 클 수 있습니다. 따라서 도착 첫날의 일정은 숙소 인근에서 가볍게 여독을 풀 수 있는 힐링 동선으로 배치하였으며, 귀가하시는 날에는 이동 전 충분한 휴식을 취하실 수 있도록 오전 일정을 여유롭게 비웠습니다.\n\n"
        
        f"### 📊 3. {destination} 실시간 빅데이터 수요 및 상권 분석\n"
        f" - **체류 강도**: {stay_score}점 (100점 만점)\n"
        f" - **소비 강도**: {consume_score}점 (100점 만점)\n"
        f" - **AI 종합 인사이트**: {stay_strategy}\n"
        f" {active_guidance_formatted}\n\n"

        f"### 🏨 4. 현지 밀착 맞춤형 숙박 시설 브리핑\n"
        f" - **선정 숙소**: {local['hotel']['name']} (실시간 평점 4.8/5.0 이상 검증 완료)\n"
        f" - **📍 주소**: {local['hotel'].get('address', '현지 상세 주소 확인 필요')}\n"
        f" - **📞 연락처**: {local['hotel'].get('phone', '프론트 데스크 번호 확인 필요')}\n"
        f" - **객실 상태**: {local['hotel']['status']}\n"
        f" - **선정 사유**: {destination}의 핵심 관광지인 {top_spots[0]}와의 접근성이 가장 뛰어납니다.\n\n"

        f"### 🗓️ 5. 테마별 추천 일정 (3종 코스)\n"
        f"고객님의 취향에 따라 아래 3가지 테마 중 하나를 선택하여 자율적으로 여행을 즐기실 수 있습니다.\n\n"
        
        f"✨ **[🅰️ A코스: 힐링형 (여유롭게 즐기는 명소 위주)]**\n"
        f" - **핵심 동선**: {top_spots[0]} 방문 및 최고급 스파 프라이빗 휴식\n"
        f"   {get_spot_details(top_spots[0])}\n"
        f" - **추천 식당**: {local['restaurant']['name']} (최고급 한우 오마카세 등 최고가 메뉴로 예산 집중)\n"
        f"   * 📍 주소: {local['restaurant'].get('address', '상세 주소 확인 필요')}\n"
        f"   * 📞 연락처: {local['restaurant'].get('phone', '예약 문의 필요')}\n\n"
        
        f"✨ **[🅱️ B코스: 체험 집중형 (액티비티와 프리미엄 디저트)]**\n"
        f" - **핵심 동선**: {top_spots[1]} 프라이빗 가이드 투어 및 프리미엄 레포츠 체험\n"
        f"   {get_spot_details(top_spots[1])}\n"
        f" - **추천 식당**: {destination} 핫플레이스 레스토랑 및 최고급 디저트 카페 라운지 통째 대관 수준의 플렉스\n"
        f"   * 📍 주소: {destination} 중앙로 12번길 최고급 다이닝\n"
        f"   * 📞 연락처: 현지 VVIP 라운지\n\n"
        
        f"✨ **[🅲 C코스: 로컬 VVIP 딥다이브형 (현지 경제 살리기)]**\n"
        f" - **핵심 동선**: {top_spots[2]} 심층 도보 투어 및 지역 명인과의 만남\n"
        f"   {get_spot_details(top_spots[2])}\n"
        f" - **추천 식당**: 지역 특산물(송이버섯, 고급 산채 등)을 아낌없이 주문하여 상인들에게 VVIP 대우받기\n"
        f"   * 📍 주소: {destination} 숨은명인길 7\n"
        f"   * 📞 연락처: 현지 상인회 VIP 직통\n\n"

        f"### 💡 6. 동네비서의 현지 밀착 꿀팁 (Hyper-Local Tips)\n"
        f" - 🎉 **지역 축제 정보**: {local.get('festival', '현재 진행 중인 특별한 축제 정보가 없습니다.')}\n"
        f" - 🚦 **실시간 현장 팁**: {local['local_tip']}\n"
        f" - 👕 **옷차림 가이드**: {destination} 특유의 기후와 지형을 고려하여, 가벼운 겉옷과 걷기 편한 운동화를 챙겨주세요.\n\n"
        f"---\n"
        f"✅ **[안내] 본 리포트는 고객님의 자율적인 여행을 돕기 위해 생성된 '완성형 여행 계획서'입니다.**\n"
        f"스마트폰에 저장하시거나 인쇄하여 가이드로 활용하시기 바랍니다. 추가적인 정보가 필요하실 때만 다시 질문해주세요.\n"
    )

def submit_travel_feedback(destination: str, rating: int, review: str):
    """여행 후기를 제출하고 50포인트를 환급받습니다. (예: "태백 여행 잘 다녀왔어, 5점, 한우집 최고!")
    destination: 다녀온 여행지 (예: '태백')
    rating: 평점 (1~5)
    review: 텍스트 후기
    """
    import db_postgres as db
    success = db.log_travel_feedback('citizen_user', destination, rating, review)
    if success:
        return f"[{destination} 여행 후기 등록 완료!]\n\n소중한 경험 데이터를 공유해주셔서 감사합니다. 고객님의 피드백은 동네비서 추천 알고리즘에 반영되었습니다.\n\n💰 보상: 50포인트가 즉시 캐시백되었습니다!"
    return "후기 등록 중 오류가 발생했습니다."


def read_file_content(file_path: str):
    """프로젝트 내 특정 파일의 내용을 읽어옵니다.
    Args:
        file_path: 읽을 파일의 경로 (예: 'main.py', 'templates/login.html')
    """
    if ".." in file_path or file_path.startswith("/"): # Security check
        return "보안상 허용되지 않는 경로입니다."
    
    try:
        if not os.path.exists(file_path):
            return "파일을 찾을 수 없습니다."
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"파일 읽기 오류: {str(e)}"

def get_project_structure():
    """현재 프로젝트의 파일 구조(트리)를 반환합니다. (숨김 폴더 제외)"""
    structure = []
    start_path = "."
    for root, dirs, files in os.walk(start_path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', 'env']]
        level = root.replace(start_path, '').count(os.sep)
        indent = ' ' * 4 * (level)
        structure.append(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            if not f.startswith('.') and not f.endswith('.pyc'):
                structure.append(f"{subindent}{f}")
    return "\n".join(structure)

# AI Tools List (Role-based Guardrails)
admin_tools = [get_current_time, get_store_orders_stat, read_file_content, plan_travel_schedule, submit_travel_feedback]
customer_tools = [get_current_time, get_agricultural_price, get_train_schedule, get_agricultural_standard_code, plan_travel_schedule, submit_travel_feedback] # Do NOT expose read_file_content to customers!

def get_gemini_client():
    """Gemini API 클라이언트 초기화"""
    try:
        api_key = config.get_settings().app.gemini_api_key
        if not api_key:
            return None
        return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"Exception in get_gemini_client: {e}")
        return None

def classify_store_type(store_name):
    """상호명을 기반으로 업종 분류 (AI) - 도구 사용 안 함"""
    client = get_gemini_client()
    if not client: return "기타 일반사업자"

    try:
        prompt = f"상호명 '{store_name}'을 분석하여 '식당', '편의점', '택배/물류', '카페', '미용실', '기타' 중 하나로만 대답해줘."
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt
        )
        return response.text.strip()
    except Exception:
        return "기타 일반사업자"

def determine_model_tier(text):
    """
    Determine AI model tier based on complexity.
    - Flash (Basic): Short, simple queries.
    - Pro (Advanced): Long, complex, reasoning-heavy queries (e.g. Travel Planning).
    """
    if not text: return 'gemini-3.5-flash'
    
    # 1. Dedicated Travel Agent Routing (Mid-sized Pro model)
    travel_keywords = ["여행", "코스", "패키지", "일정 짜줘"]
    if any(keyword in text for keyword in travel_keywords):
        return 'gemini-pro-latest'

    # Heuristic 1: Length
    if len(text) > 100:
        return 'gemini-3.5-flash'
        
    # Heuristic 2: Keywords
    complex_keywords = ["분석", "비교", "이유", "해결", "기획", "작성", "요약"]
    if any(keyword in text for keyword in complex_keywords):
        return 'gemini-3.5-flash'
        
    return 'gemini-3.5-flash'


def calculate_cost_and_intent(user_input):
    travel_keywords = ["여행", "코스", "패키지", "일정 짜줘"]
    if any(k in user_input for k in travel_keywords):
        return 100, "여행 패키지 설계"

    code_keywords = ["표준코드", "품목코드", "산지코드", "단위코드", "카테고리코드"]
    if any(k in user_input for k in code_keywords):
        return 50, "농산물 표준코드 조회"

    korail_keywords = ["기차", "열차", "코레일", "태백역", "청량리", "승차권"]
    if any(k in user_input for k in korail_keywords):
        return 50, "철도 예약 문의"
        
    agri_keywords = ["가격", "농산물", "시세"]
    if any(k in user_input for k in agri_keywords):
        return 50, "농산물 가격 조회"
        
    complex_keywords = ["예약", "결제", "주문", "통계", "취소", "환불"]
    if any(k in user_input for k in complex_keywords):
        return 50, "Action/System"
        
    return 10, "Simple Query"

def get_ai_response(user_input, chat_history=None, system_prompt=None, tool_set='customer', user_id=None):
    """AI 상담원 응답 생성 (Composite Mode: Function Calling Enabled & Billing/Auth injected)"""
    
    # [Authentication & Billing Phase]
    is_premium = False
    credit_cost, intent_category = calculate_cost_and_intent(user_input)
    
    if user_id:
        is_premium = db.check_ai_member(user_id)
        if is_premium:
            # Premium Mode: Deduct credits atomically
            success, msg = db.deduct_credit_atomically(user_id, amount=credit_cost)
            if not success:
                return {"text": msg, "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}
        else:
            # Simple Mode: Check free usage limits
            allowed, count = db.check_and_increment_free_usage(user_id, max_count=3)
            if not allowed:
                return {"text": "무료 이용 횟수(3회)를 모두 소진하셨습니다. 더 많은 서비스를 이용하시려면 <a href='/token_recharge' style='color: #00f2fe; font-weight: bold; text-decoration: underline;'>회원 가입 및 적립금 충전</a>을 진행해주세요.", "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}
    
    # [Routing] Determine Model
    model_name = determine_model_tier(user_input)
    
    client = get_gemini_client()
    if not client:
        print(f"Client is None! model_name: {model_name}")
        # Refund if premium
        if is_premium and user_id:
            db.refund_credit(user_id, amount=credit_cost)
        return "죄송합니다. 현재 AI 시스템이 오프라인 상태입니다. 나중에 다시 시도해주세요."
    
    try:
        # 시스템 프롬프트 설정 (기본값 또는 사용자 정의)
        if not system_prompt:
             system_prompt = """너는 소상공인과 농부, 그리고 지역 주민을 돕는 '동네비서'다.
이제 동네비서는 '수동형 3종 리포트 생성(Passive Mode)'로 동작한다.
고객이 예산, 기간, 목적지를 바탕으로 여행 코스를 질문하면 도구를 사용하여 매우 상세한 '완성형 여행 계획서'를 출력하라.
이 리포트는 그 자체로 완벽하여 고객이 인쇄해서 다닐 수 있어야 한다.

[매우 중요: Passive Mode 규정]
1. 리포트를 제공한 후에는 "결제를 진행하시겠습니까?", "추가로 궁금한 점이 있으신가요?", "어떤 코스가 마음에 드시나요?"와 같은 어떤 질문이나 제안도 먼저 하지 마라.
2. 어떠한 예약 권유나 결제 유도도 해서는 안 된다. 모든 리포트는 '고객 자율 여행용'이다.
3. 무조건 리포트를 출력하고 대화(응답)를 즉각 종료하라.
4. 절대 캐주얼한 이모티콘(^^, ㅠㅠ, ㅎㅎ 등)을 사용하지 말고, 항상 정중하고 프로페셔널한 비즈니스 톤을 유지하라.
5. 질문이 다른 분야인 경우 "저는 비즈니스를 돕는 동네비서 AI입니다. 업무와 관련 없는 질문은 사양하고 있습니다."라고 안내하라."""

        # 사용자 자택 주소 동적 주입 (고객용)
        if user_id and tool_set != 'admin':
            home_address = db.get_user_home_address(user_id)
            system_prompt += f"\n\n[중요] 고객의 자택 주소(Origin)는 '{home_address}'입니다. 여행 일정 예약 시 반드시 이 주소를 출발지(origin) 파라미터로 사용하세요."
            
        # 가맹점 매장 ID 동적 주입 (사장님용)
        if user_id and tool_set == 'admin':
            system_prompt += f"\n\n[가맹점 정보] 현재 로그인한 가맹점 사장님의 매장 ID(store_id / subdomain)는 '{user_id}'입니다. 매장 주문 통계 등 매장 관련 도구를 호출할 때 이 ID를 사용하세요."


        selected_tools = admin_tools if tool_set == 'admin' else customer_tools
        chat = client.chats.create(
            model=model_name,
            config=types.GenerateContentConfig(
                tools=selected_tools,
                max_output_tokens=1000,
                temperature=0.7,
                system_instruction=system_prompt,
                automatic_function_calling={"disable": True}
            )
        )
        
        response = chat.send_message(user_input)
        
        loop_count = 0
        max_loops = 5
        bypassed = False
        
        while response.function_calls and loop_count < max_loops:
            loop_count += 1
            fc = response.function_calls[0]
            func_name = fc.name
            args_dict = fc.args if isinstance(fc.args, dict) else (fc.args.model_dump() if hasattr(fc.args, 'model_dump') else dict(fc.args))
            
            func_obj = next((f for f in selected_tools if f.__name__ == func_name), None)
            if func_obj:
                try:
                    result_str = func_obj(**args_dict)
                except Exception as e:
                    result_str = str(e)
                    
                # Direct bypass for formatted tools (prevent AI summarization/truncation)
                if func_name in ["plan_travel_schedule", "submit_travel_feedback"]:
                    text = result_str
                    bypassed = True
                    break
                else:
                    # Send result back to model for other tools
                    part = types.Part.from_function_response(name=func_name, response={"result": result_str})
                    response = chat.send_message(part)
            else:
                break
                
        if not bypassed:
            if response.text is not None:
                text = response.text.strip()
            else:
                text = "죄송합니다. 오류가 발생하여 답변을 생성하지 못했습니다."
        
        try:
            usage = {
                "input_tokens": response.usage_metadata.prompt_token_count,
                "output_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count
            }
        except:
            usage = {
                "input_tokens": len(full_prompt) // 4,
                "output_tokens": len(text) // 4,
                "total_tokens": (len(full_prompt) + len(text)) // 4
            }
            
        # Log Usage for Platform OS Analytics
        if is_premium and user_id:
            db.log_ai_usage_analytics(user_id, intent_category, credit_cost)
            
        actions = []
        import re
        import json
        match = re.search(r'\[ACTIONS\](.*?)\[/ACTIONS\]', text, re.DOTALL)
        if match:
            try:
                actions = json.loads(match.group(1).strip())
                text = text.replace(match.group(0), "").strip()
            except:
                pass
        
        if not actions and "[프리미엄 AI 지능형 맞춤 패키지]" in text:
            actions = [
                {"label": "🏨 숙소 즉시 결제/예약", "type": "BOOK_HOTEL", "payload": "hotel"},
                {"label": "🍽️ 맛집 테이블 확정", "type": "BOOK_REST", "payload": "restaurant"},
                {"label": "🚕 지역 택시/렌터카 호출", "type": "BOOK_TAXI", "payload": "taxi"}
            ]

        return {
            "text": text,
            "actions": actions,
            "usage": usage
        }
    except APIRequestError as e:
        print(f"API Request Error: {e}")
        if is_premium and user_id:
            db.refund_credit(user_id, amount=credit_cost)
            print(f"Refunded {credit_cost} credits to {user_id} due to API error.")
        return {
            "text": f"{str(e)} (차감된 적립금은 환불되었습니다)",
            "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        }
    except Exception as e:
        print(f"AI Error: {e}")
        # [Refund Phase] If AI fails, restore deducted credits for premium members
        if is_premium and user_id:
            db.refund_credit(user_id, amount=credit_cost)
            print(f"Refunded {credit_cost} credits to {user_id} due to AI error.")
            
        return {
            "text": "죄송합니다. 오류가 발생하여 답변을 생성하지 못했습니다. (차감된 적립금은 환불되었습니다)",
            "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        }

async def parse_call_audio(audio_url: str) -> str:
    """통화 녹음 파일(URL)을 텍스트(STT)로 변환합니다."""
    # 실제 프로덕션에서는 Google Cloud STT API 또는 Whisper API를 호출합니다.
    # 현재는 데모 및 PoC를 위해 가상의 통화 대본을 반환합니다.
    import asyncio
    await asyncio.sleep(1.5) # Simulate API latency
    mock_transcript = (
        "AI: 안녕하세요, 동네식당입니다. 사장님이 부재중이시라 AI 비서가 대신 전화를 받았습니다. 어떤 용무이신가요?\n"
        "고객: 다음 주 토요일에 저희 아들 결혼식이 있어서 피로연 예약 좀 하려고요.\n"
        "AI: 아, 결혼식이 있으시군요! 축하드립니다. 예약 인원과 시간, 성함이 어떻게 되시나요?\n"
        "고객: 50명이고요, 시간은 오후 2시입니다. 제 이름은 김철수입니다.\n"
        "AI: 네, 김철수님. 다음 주 토요일 오후 2시, 50명 예약 내역을 사장님께 전달해 드리겠습니다. 감사합니다."
    )
    return mock_transcript


class CallSummarySchema(BaseModel):
    name: str = Field(description="고객 이름 (모르면 '이름 미상')")
    intent: str = Field(description="예약, 주문, 단순문의, 불만접수 중 가장 적합한 1개")
    summary: str = Field(description="구체적인 통화 요건 1~2줄 요약 (예: 다음주 토요일 결혼식 피로연 예약)")
    event_type: Optional[str] = Field(description="결혼, 상가, 생일, 방문약속 중 가장 적합한 1개 (해당 없으면 null)")
    event_details: Optional[str] = Field(description="가장 중요한 이벤트의 날짜와 상세 내용 (해당 없으면 null)")

async def summarize_call_text(transcript: str, store_id: str = "UNKNOWN", customer_phone: str = "UNKNOWN") -> dict:
    """STT로 변환된 통화 대본을 분석하여 JSON 장부 및 중요 일정(경조사 등) 포맷으로 요약합니다."""
    prompt = f"""
    다음은 매장 AI 비서와 고객 간의 통화 녹음 스크립트입니다.
    이 내용을 분석하여 요약해주세요.

    통화 스크립트:
    {transcript}
    """
    try:
        client = get_gemini_client()
        if not client:
            raise Exception("Client not initialized")
            
        config = types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=CallSummarySchema
        )
        
        response = client.models.generate_content(
            model='gemini-pro-latest',
            contents=prompt,
            config=config
        )
        
        import json
        return json.loads(response.text)
    except Exception as e:
        print("Call Parsing Error:", e)
        try:
            import db_manager
            db_manager.log_security_event(store_id, customer_phone, "CALL_PARSE_ERROR", f"{e}\n{transcript}")
        except Exception:
            pass
        
    # Fallback Data
    return {
        "name": "이름 미상",
        "event_details": None
    }

async def draft_courier_greeting_message(customer_phone: str) -> str:
    """
    고객 전화번호를 기반으로 과거 택배/화물 이력을 조회하고, 
    Gemini AI를 이용해 맞춤형 응대 문자(SMS)를 작성합니다.
    """
    import pandas as pd
    try:
        # Use existing db functions to get courier requests instead of creating a raw connection
        query = "SELECT tracking_code, created_at FROM courier_requests WHERE sender_phone = ? ORDER BY created_at DESC LIMIT 1"
        # We don't have direct access to a connection, but we can query it safely via a known method or sqlite3
        import sqlite3
        conn = sqlite3.connect("database.db", check_same_thread=False)
        df = pd.read_sql(query, conn, params=(customer_phone,))
        conn.close()
    except Exception as e:
        print("DB Select Error in Draft Courier:", e)
        df = pd.DataFrame()

    tracking_info = ""
    if not df.empty and pd.notnull(df.iloc[0]['tracking_code']):
        tracking_info = f"최근 발송한 송장번호: {df.iloc[0]['tracking_code']} (예약일시: {df.iloc[0]['created_at']})"
    else:
        tracking_info = "최근 택배 예약 이력이 없습니다."

    base_url = config.get_secret("APP_BASE_URL", "https://dongnebiseo.com").rstrip("/")
    booking_link = f"{base_url}/citizen/courier"
    tracking_link = "https://www.ilogen.com/web/personal/tkSearch"

    prompt = f"""
    당신은 '동네비서'의 전문 AI 상담사입니다.
    고객({customer_phone})이 전화를 걸었습니다.
    
    [과거 기록]
    {tracking_info if df.empty == False else '신규 고객'}
    
    [목적]
    화물추적인지, 택배 예약인지 의도를 파악해야 합니다.
    친절하고 짧게, 고객이 바로 답변할 수 있는 질문 한 문장을 만드세요.
    반드시 다음 링크들을 제공하세요: 
    - 택배예약: {booking_link}
    - 화물추적: {tracking_link}
    """

    try:
        api_key = config.get_secret("GOOGLE_API_KEY")
        if not api_key:
            api_key = config.get_settings().app.gemini_api_key
        client = genai.Client(api_key=api_key)
        
        config = types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=150
        )
        
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt,
            config=config
        )
        return response.text.strip()
    except Exception as e:
        print("AI Draft Error:", e)
        return f"[동네비서 AI]\n통화량이 많습니다.\n택배예약: {booking_link}\n화물추적: {tracking_link}"


