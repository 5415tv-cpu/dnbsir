import streamlit as st
import google.generativeai as genai

def get_gemini_client(model_name='gemini-flash-latest'):
    """Gemini API 클라이언트 초기화 (기본값: flash 모델)"""
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY")
        if not api_key:
            return None
        genai.configure(api_key=api_key)
        # 2026년 기준 사용 가능한 최신 Flash 모델 시도
        try:
            return genai.GenerativeModel('gemini-flash-latest')
        except:
            return genai.GenerativeModel('gemini-pro') # 최후 폴백
    except Exception:
        return None

def classify_store_type(store_name):
    """상호명을 기반으로 업종 분류 (AI)"""
    model = get_gemini_client()
    if not model:
        # AI 연결 실패 시 기본 로직
        if any(keyword in store_name for keyword in ["식당", "맛집", "식사", "분식", "식사", "레스토랑", "가든", "포차"]):
            return "식당"
        elif any(keyword in store_name for keyword in ["편의점", "마트", "상회", "슈퍼", "CU", "GS25", "세븐"]):
            return "편의점"
        return "기타 일반사업자"

    try:
        prompt = f"상호명 '{store_name}'을 분석하여 '식당', '편의점', '택배/물류', '카페', '미용실', '기타' 중 하나로만 대답해줘."
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return "기타 일반사업자"

def get_ai_response(user_input, chat_history=None):
    """AI 상담원 응답 생성 (Gemini Flash 사용)"""
    model = get_gemini_client()
    if not model:
        return "죄송합니다. 현재 AI 시스템이 오프라인 상태입니다. 나중에 다시 시도해주세요."
    
    try:
        # 시스템 프롬프트 추가 (상담원 성격 부여)
        system_prompt = (
            "당신은 '동네비서' 서비스의 AI 전문 상담원입니다. "
            "친절하고 전문가답게 응답하세요. "
            "주요 서비스: 매장 예약 관리, 로젠택배 접수, 가맹점 포인트 및 문자 발송 시스템. "
            "사용자의 질문에 한국어로 명확하고 상세하게 답변하세요."
        )
        
        full_prompt = f"{system_prompt}\n\n사용자: {user_input}\n상담원:"
        response = model.generate_content(full_prompt)
        return response.text.strip()
    except Exception as e:
        return f"응답 생성 중 오류가 발생했습니다: {str(e)}"
