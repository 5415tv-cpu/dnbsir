import config
import os
os.environ["GRPC_DNS_RESOLVER"] = "native"
import google.generativeai as genai
from pydantic import BaseModel, Field
from typing import Optional

import datetime
import db_manager as db

import os

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
admin_tools = [get_current_time, get_store_orders_stat, read_file_content]
customer_tools = [get_current_time] # Do NOT expose read_file_content to customers!

def get_gemini_client(model_name='gemini-3.5-flash', tool_set='customer'):
    """Gemini API 클라이언트 초기화"""
    try:
        api_key = config.get_settings().app.gemini_api_key
        if not api_key:
            return None
        genai.configure(api_key=api_key)
        
        selected_tools = admin_tools if tool_set == 'admin' else customer_tools
        return genai.GenerativeModel(model_name, tools=selected_tools)
    except Exception as e:
        print(f"Exception in get_gemini_client: {e}")
        return None

def classify_store_type(store_name):
    """상호명을 기반으로 업종 분류 (AI) - 도구 사용 안 함"""
    # ... (Keep existing implementation but verify client usage) ...
    # Simplified client for classification to avoid overhead
    api_key = config.get_settings().app.gemini_api_key
    if not api_key: return "기타 일반사업자"
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-flash-latest') # Use Flash for simple tasks

    try:
        prompt = f"상호명 '{store_name}'을 분석하여 '식당', '편의점', '택배/물류', '카페', '미용실', '기타' 중 하나로만 대답해줘."
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return "기타 일반사업자"

def determine_model_tier(text):
    """
    Determine AI model tier based on complexity.
    - Flash (Basic): Short, simple queries.
    - Pro (Advanced): Long, complex, reasoning-heavy queries.
    """
    if not text: return 'gemini-flash-latest'

    # Heuristic 1: Length
    if len(text) > 100:
        return 'gemini-pro-latest'
        
    # Heuristic 2: Keywords
    complex_keywords = ["분석", "비교", "이유", "해결", "기획", "작성", "요약"]
    if any(keyword in text for keyword in complex_keywords):
        return 'gemini-3.5-flash'
        
    return 'gemini-3.5-flash'

def get_ai_response(user_input, chat_history=None, system_prompt=None, tool_set='customer'):
    """AI 상담원 응답 생성 (Composite Mode: Function Calling Enabled)"""
    
    # [Routing] Determine Model
    model_name = determine_model_tier(user_input)
    # print(f"[*] Routing to Model: {model_name}") # Optional logging
    
    model = get_gemini_client(model_name, tool_set=tool_set)
    if not model:
        print(f"Model is None! model_name: {model_name}, tool_set: {tool_set}")
        return "죄송합니다. 현재 AI 시스템이 오프라인 상태입니다. 나중에 다시 시도해주세요."
    
    try:
        # 시스템 프롬프트 설정 (기본값 또는 사용자 정의)
        if not system_prompt:
             system_prompt = """너는 소상공인과 농부를 돕는 '동네비서'다. 
명심하라: '동네비서'의 주요 업무(매장/농장 매출, 고객 통계, 작물 상태, 비즈니스 관리)와 관련이 없는 질문은 절대 받지 않는다.
날씨, 길찾기, 기차 시간 등 업무와 무관한 질문에는 절대 답하지 말고 정중히 거절하라.
절대 캐주얼한 이모티콘(^^, ㅠㅠ, ㅎㅎ 등)을 사용하지 말고, 항상 정중하고 프로페셔널한 비즈니스 톤을 유지하라.
업무 외적인 질문이 들어오면 "사장님, 저는 소상공인과 농부의 비즈니스를 돕는 동네비서 AI입니다. 동네비서 업무와 관련 없는 질문은 정중히 사양하고 있습니다. 매장이나 농장 운영에 관한 질문을 남겨주시면 최선을 다해 돕겠습니다."라고 단호하고 예의 바르게 안내하라.
답변은 기호(별표 등)를 쓰지 말고 줄바꿈을 활용하여 평문(Plain text)으로 깔끔하게 작성하라."""

        chat = model.start_chat(enable_automatic_function_calling=True)
        
        # [Billing] Calculate input tokens approximately or rely on response metadata
        full_prompt = f"{system_prompt}\n\n사용자: {user_input}"
        
        # Enforce Token Limit for Cost Control (Approx 500 tokens ~ 2000 chars)
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=500,
            temperature=0.7
        )
        
        response = chat.send_message(full_prompt, generation_config=generation_config)
        
        text = response.text.strip()
        
        # [Billing] Extract Token Usage
        # Handle cases where usage_metadata might be missing or different structure
        try:
            usage = {
                "input_tokens": response.usage_metadata.prompt_token_count,
                "output_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count
            }
        except:
            # Fallback estimation if metadata is missing (1 char ~ 0.25 token)
            usage = {
                "input_tokens": len(full_prompt) // 4,
                "output_tokens": len(text) // 4,
                "total_tokens": (len(full_prompt) + len(text)) // 4
            }
            
        return {
            "text": text,
            "usage": usage
        }
    except Exception as e:
        print(f"AI Error: {e}")
        return {
            "text": "죄송합니다. 오류가 발생했습니다.",
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
        model = get_gemini_client('gemini-pro-latest', tool_set='admin')
        if not model:
            raise Exception("Model not initialized")
            
        generation_config = genai.types.GenerationConfig(
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=CallSummarySchema
        )
        
        response = model.generate_content(prompt, generation_config=generation_config)
        
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
        # 지연 최소화를 위해 1.5-flash 모델 사용
        api_key = config.get_secret("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-flash-latest')
        
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            max_output_tokens=150
        )
        
        response = model.generate_content(prompt, generation_config=generation_config)
        return response.text.strip()
    except Exception as e:
        print("AI Draft Error:", e)
        return f"[동네비서 AI]\n통화량이 많습니다.\n택배예약: {booking_link}\n화물추적: {tracking_link}"


