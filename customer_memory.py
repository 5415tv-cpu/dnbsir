"""
🧠 고객 정보 기억 모듈 (Customer Memory)
- AI 대화 중 고객 정보 추출
- 재방문 고객 인식 및 개인화 인사
- 취향/선호도 기반 추천
"""

import re

from datetime import datetime
from typing import Optional, Dict, List, Tuple

# DB 함수 임포트
from db_manager import (
    get_customer, get_customer_by_phone, save_customer,
    update_customer_field, increment_customer_order
)


# ==========================================
# 📱 전화번호 정규화
# ==========================================

def normalize_phone(phone: str) -> str:
    """전화번호 정규화 (하이픈, 공백 제거)"""
    if not phone:
        return ""
    return re.sub(r'[\s\-\.]', '', phone)


def format_phone(phone: str) -> str:
    """전화번호 포맷팅 (010-1234-5678 형식)"""
    normalized = normalize_phone(phone)
    if len(normalized) == 11 and normalized.startswith('010'):
        return f"{normalized[:3]}-{normalized[3:7]}-{normalized[7:]}"
    elif len(normalized) == 10:
        return f"{normalized[:3]}-{normalized[3:6]}-{normalized[6:]}"
    return normalized


# ==========================================
# 🔍 대화에서 정보 추출
# ==========================================

def extract_customer_info_from_text(text: str) -> Dict:
    """
    텍스트에서 고객 정보 추출
    
    Args:
        text: 대화 내용
    
    Returns:
        추출된 정보 {'name', 'phone', 'address', 'preferences', 'notes'}
    """
    extracted = {
        'name': None,
        'phone': None,
        'address': None,
        'preferences': None,
        'notes': None
    }
    
    # 전화번호 추출 (다양한 형식 지원)
    phone_patterns = [
        r'01[0-9][\s\-\.]?\d{3,4}[\s\-\.]?\d{4}',  # 010-1234-5678, 01012345678
        r'01[0-9]\d{7,8}',  # 01012345678
    ]
    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            extracted['phone'] = normalize_phone(match.group())
            break
    
    # 이름 추출 패턴
    name_patterns = [
        r'(?:제\s*이름은?|저는?|나는?)\s*([가-힣]{2,4})(?:이?에요|입니다|이야|예요|야)',
        r'([가-힣]{2,4})(?:이?라고\s*합니다|입니다)',
        r'이름[은이]?\s*([가-힣]{2,4})',
        r'([가-힣]{2,4})\s*(?:이?에요|예요)(?:\s*이름)?',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text)
        if match:
            name = match.group(1)
            # 일반적인 이름 길이 확인 (2-4글자)
            if 2 <= len(name) <= 4:
                extracted['name'] = name
                break
    
    # 주소 추출 패턴
    address_patterns = [
        r'(?:주소[는은이]?|배달\s*주소[는은이]?)\s*([가-힣0-9\s\-\,\.]+(?:동|로|길|아파트|빌딩|오피스텔|주택|호)[가-힣0-9\s\-\,\.]*)',
        r'([가-힣]+(?:시|도)\s*[가-힣]+(?:구|군|시)\s*[가-힣0-9\s\-\,\.]+(?:동|로|길)[가-힣0-9\s\-\,\.]*)',
        r'(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)[가-힣0-9\s\-\,\.]+(?:동|호|층)',
    ]
    for pattern in address_patterns:
        match = re.search(pattern, text)
        if match:
            address = match.group(1).strip()
            if len(address) >= 5:  # 최소 길이 확인
                extracted['address'] = address
                break
    
    # 취향/선호사항 추출 패턴
    preference_patterns = [
        r'(?:저는?|나는?|전)\s*([가-힣]+(?:을|를)?)\s*(?:좋아해요|좋아합니다|좋아함|좋아|선호해요|선호합니다)',
        r'(?:맵[지는게]?\s*(?:않[게은]|못)|덜\s*맵게|안\s*맵게)',  # 맵기 선호
        r'(?:매운\s*(?:거|것|음식)[을를]?\s*좋아)',
        r'(?:알[러레]르기|알레르기)[가이]?\s*있[어으]',
        r'([가-힣]+)\s*(?:빼|빼고|빼주세요|제외)',  # 재료 제외
        r'(?:채식|비건|베지테리언)',
    ]
    
    preferences = []
    for pattern in preference_patterns:
        matches = re.findall(pattern, text)
        preferences.extend(matches if isinstance(matches, list) else [matches])
    
    # 취향 관련 키워드 직접 검색
    preference_keywords = {
        '맵게': '매운 음식 선호',
        '안 맵게': '맵지 않게',
        '덜 맵게': '맵지 않게',
        '채식': '채식주의',
        '비건': '비건',
        '알레르기': '알레르기 있음',
        '당뇨': '당뇨 주의',
        '저염': '저염식 선호',
    }
    
    for keyword, preference in preference_keywords.items():
        if keyword in text:
            preferences.append(preference)
    
    if preferences:
        # 중복 제거 및 문자열 변환
        unique_prefs = list(set([p for p in preferences if isinstance(p, str) and p]))
        extracted['preferences'] = ', '.join(unique_prefs)
    
    # 요청사항/메모 추출
    notes_patterns = [
        r'(?:요청사항|요청|부탁)[은는이]?\s*[:：]?\s*([가-힣0-9\s\,\.]+)',
        r'(?:문\s*앞|경비실|벨\s*누르지)',
        r'(?:조용히|빨리|천천히)',
    ]
    
    notes = []
    for pattern in notes_patterns:
        match = re.search(pattern, text)
        if match:
            note = match.group(1) if match.lastindex else match.group()
            notes.append(note.strip())
    
    if notes:
        extracted['notes'] = ', '.join(notes)
    
    return extracted


def extract_info_with_ai(text: str, model) -> Dict:
    """
    AI를 사용해 대화에서 고객 정보 추출 (더 정확함)
    
    Args:
        text: 대화 내용
        model: Gemini 모델 인스턴스
    
    Returns:
        추출된 정보
    """
    if not model:
        return extract_customer_info_from_text(text)
    
    try:
        prompt = f"""다음 대화에서 고객 정보를 추출해주세요. 
정보가 없으면 해당 필드는 비워두세요.

대화 내용:
"{text}"

다음 형식으로만 응답해주세요 (JSON 형식):
{{
  "name": "고객 이름 (2-4글자 한글)",
  "phone": "전화번호 (숫자만, 예: 01012345678)",
  "address": "배달 주소",
  "preferences": "음식 취향이나 선호사항 (예: 매운 음식 좋아함, 알레르기 있음)",
  "notes": "특별 요청사항 (예: 문 앞에 놔주세요)"
}}

정보가 없는 필드는 빈 문자열("")로 남겨두세요."""

        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # JSON 파싱 시도
        import json
        
        # JSON 블록 추출
        json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            extracted = json.loads(json_match.group())
            
            # 전화번호 정규화
            if extracted.get('phone'):
                extracted['phone'] = normalize_phone(extracted['phone'])
            
            return extracted
        
        return extract_customer_info_from_text(text)
        
    except Exception as e:
        # AI 추출 실패 시 정규식 방식 사용
        return extract_customer_info_from_text(text)


# ==========================================
# 💾 고객 정보 저장 및 업데이트
# ==========================================

def update_customer_from_conversation(
    customer_id: str,
    store_id: str,
    conversation_text: str,
    model=None
) -> Tuple[bool, Dict]:
    """
    대화 내용에서 고객 정보를 추출하여 업데이트
    
    Args:
        customer_id: 고객 ID (전화번호)
        store_id: 가게 ID
        conversation_text: 대화 내용
        model: AI 모델 (선택)
    
    Returns:
        (성공 여부, 추출된 정보)
    """
    # 정보 추출
    if model:
        extracted = extract_info_with_ai(conversation_text, model)
    else:
        extracted = extract_customer_info_from_text(conversation_text)
    
    # 추출된 정보가 있으면 저장
    has_info = any(v for v in extracted.values() if v)
    
    if has_info:
        # 기존 고객 정보 가져오기
        existing = get_customer(customer_id, store_id)
        
        if existing:
            # 기존 고객 업데이트
            for field, value in extracted.items():
                if value:
                    if field == 'preferences' and existing.get('preferences'):
                        # 기존 취향에 추가
                        current_prefs = existing.get('preferences', '')
                        if value not in current_prefs:
                            value = f"{current_prefs}, {value}" if current_prefs else value
                    
                    update_customer_field(customer_id, field, value, store_id)
        else:
            # 신규 고객 저장
            customer_data = {
                'customer_id': customer_id,
                'store_id': store_id,
                'phone': customer_id,  # 전화번호를 ID로 사용
                **{k: v for k, v in extracted.items() if v}
            }
            save_customer(customer_data)
    
    return has_info, extracted


# ==========================================
# 👋 개인화된 인사말 생성
# ==========================================

def generate_welcome_message(customer: Dict, store_name: str = "") -> str:
    """
    재방문 고객을 위한 개인화된 인사말 생성
    
    Args:
        customer: 고객 정보 딕셔너리
        store_name: 가게 이름
    
    Returns:
        개인화된 인사말
    """
    if not customer:
        return None
    
    name = customer.get('name', '')
    preferences = customer.get('preferences', '')
    total_orders = customer.get('total_orders', 0)
    last_visit = customer.get('last_visit', '')
    
    # 인사말 구성
    messages = []
    
    # 이름이 있으면 이름으로 인사
    if name:
        messages.append(f"반갑습니다, {name}님! 🎉")
    else:
        messages.append("다시 찾아주셔서 감사합니다! 🎉")
    
    # 방문 횟수 언급
    if total_orders > 0:
        if total_orders >= 10:
            messages.append(f"벌써 {total_orders}번째 주문이시네요! 단골 고객님 감사합니다! 💝")
        elif total_orders >= 5:
            messages.append(f"{total_orders}번째 방문이시네요! 항상 감사합니다! 😊")
        else:
            messages.append(f"{total_orders}번째 방문을 환영해요! 🙌")
    
    # 취향 기억
    if preferences:
        # 취향 정보를 자연스럽게 언급
        pref_mention = preferences.split(',')[0].strip()  # 첫 번째 취향만
        messages.append(f"지난번에 '{pref_mention}'이라고 말씀하셨던 거 기억하고 있어요!")
    
    # 마지막 방문일 언급
    if last_visit:
        try:
            last_date = datetime.strptime(last_visit.split()[0], "%Y-%m-%d")
            days_ago = (datetime.now() - last_date).days
            
            if days_ago == 0:
                messages.append("오늘도 찾아주셨군요!")
            elif days_ago <= 7:
                messages.append(f"얼마 전에도 오셨었죠!")
            elif days_ago <= 30:
                messages.append(f"한동안 안 오셨네요, 보고 싶었어요!")
        except:
            pass
    
    return " ".join(messages)


def get_personalized_greeting(phone: str, store_id: str, store_name: str = "") -> Tuple[Optional[str], Optional[Dict]]:
    """
    전화번호로 고객을 조회하고 개인화된 인사말 반환
    
    Args:
        phone: 고객 전화번호
        store_id: 가게 ID
        store_name: 가게 이름
    
    Returns:
        (인사말, 고객 정보) 또는 (None, None)
    """
    customer_id = normalize_phone(phone)
    customer = get_customer(customer_id, store_id)
    
    if customer:
        greeting = generate_welcome_message(customer, store_name)
        return greeting, customer
    
    return None, None


# ==========================================
# 📊 대화 컨텍스트 관리
# ==========================================

class CustomerContext:
    """고객 대화 컨텍스트 관리 클래스"""
    
    def __init__(self, store_id: str, store_name: str = ""):
        self.store_id = store_id
        self.store_name = store_name
        self.customer_id = None
        self.customer_info = None
        self.conversation_history = []
        self.extracted_info = {}
    
    def set_customer(self, phone: str):
        """고객 설정 (전화번호로)"""
        self.customer_id = normalize_phone(phone)
        self.customer_info = get_customer(self.customer_id, self.store_id)
        return self.customer_info
    
    def get_welcome_message(self) -> Optional[str]:
        """환영 메시지 가져오기"""
        if self.customer_info:
            return generate_welcome_message(self.customer_info, self.store_name)
        return None
    
    def add_message(self, role: str, content: str, model=None):
        """대화 메시지 추가 및 정보 추출"""
        self.conversation_history.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
        
        # 사용자 메시지에서 정보 추출
        if role == 'user' and self.customer_id:
            has_info, extracted = update_customer_from_conversation(
                self.customer_id, 
                self.store_id, 
                content,
                model
            )
            
            if has_info:
                self.extracted_info.update({k: v for k, v in extracted.items() if v})
                # 고객 정보 갱신
                self.customer_info = get_customer(self.customer_id, self.store_id)
    
    def complete_order(self):
        """주문 완료 시 호출 - 주문 횟수 증가"""
        if self.customer_id:
            return increment_customer_order(self.customer_id, self.store_id)
        return 0
    
    def get_context_summary(self) -> str:
        """AI에게 전달할 고객 컨텍스트 요약"""
        if not self.customer_info:
            return ""
        
        summary_parts = []
        
        if self.customer_info.get('name'):
            summary_parts.append(f"고객 이름: {self.customer_info['name']}")
        
        if self.customer_info.get('preferences'):
            summary_parts.append(f"고객 취향: {self.customer_info['preferences']}")
        
        if self.customer_info.get('address'):
            summary_parts.append(f"단골 주소: {self.customer_info['address']}")
        
        if self.customer_info.get('notes'):
            summary_parts.append(f"요청사항: {self.customer_info['notes']}")
        
        if self.customer_info.get('total_orders', 0) > 0:
            summary_parts.append(f"총 주문 횟수: {self.customer_info['total_orders']}회")
        
        if summary_parts:
            return "[고객 정보]\n" + "\n".join(summary_parts)
        
        return ""


# ==========================================
# 🎯 AI 프롬프트 헬퍼
# ==========================================

def get_ai_system_prompt_with_customer(store_info: Dict, customer_context: CustomerContext) -> str:
    """
    고객 정보를 포함한 AI 시스템 프롬프트 생성
    
    Args:
        store_info: 가게 정보
        customer_context: 고객 컨텍스트
    
    Returns:
        시스템 프롬프트
    """
    store_name = store_info.get('name', '가게')
    menu_text = store_info.get('menu_text', '')
    
    prompt = f"""당신은 '{store_name}'의 친절한 AI 주문 도우미입니다.

[가게 정보]
가게명: {store_name}
메뉴: {menu_text}

"""
    
    # 고객 정보 추가
    customer_summary = customer_context.get_context_summary()
    if customer_summary:
        prompt += f"""
{customer_summary}

위 고객 정보를 기억하고, 고객의 취향에 맞는 추천과 개인화된 응대를 해주세요.
고객이 새로운 정보(이름, 주소, 취향 등)를 알려주면 자연스럽게 기억한다고 말해주세요.

"""
    
    prompt += """[응대 지침]
1. 친절하고 따뜻하게 응대합니다
2. 고객의 취향과 요청사항을 기억하고 반영합니다
3. 메뉴 추천 시 고객의 선호도를 고려합니다
4. 짧고 자연스러운 한국어로 대화합니다
5. 이모지를 적절히 사용하여 친근하게 대화합니다"""
    
    return prompt


