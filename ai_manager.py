import config
import google.generativeai as genai

import datetime
import db_sqlite

import os

# [Composite Mode] Tool Definitions
def get_current_time():
    """현재 시간을 반환합니다."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_store_orders_stat(store_id: str):
    """특정 매장의 최근 주문 통계를 조회합니다."""
    # ... (Keep existing implementation logic) ...
    days = 7
    df = db_sqlite.get_orders(store_id, days)
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
        subindent = ' ' * end(f4 * (level + 1)
        for f in files:
            if not f.startswith('.') and not f.endswith('.pyc'):
                structure.append(f"{subindent}{f}")
    return "\n".join(structure)

# AI Tools List
ai_tools = [get_current_time, get_store_orders_stat, read_file_content]

def get_gemini_client(model_name='gemini-3.1-pro'):
    """Gemini API 클라이언트 초기화"""
    try:
        api_key = config.get_secret("GOOGLE_API_KEY")
        if not api_key:
            return None
        genai.configure(api_key=api_key)
        
        return genai.GenerativeModel(model_name, tools=ai_tools)
    except Exception:
        return None

def classify_store_type(store_name):
    """상호명을 기반으로 업종 분류 (AI) - 도구 사용 안 함"""
    # ... (Keep existing implementation but verify client usage) ...
    # Simplified client for classification to avoid overhead
    api_key = config.get_secret("GOOGLE_API_KEY")
    if not api_key: return "기타 일반사업자"
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3.1-pro') # Use Flash for simple tasks

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
    if not text: return 'gemini-3.1-pro'

    # Heuristic 1: Length
    if len(text) > 100:
        return 'gemini-3.1-pro'
        
    # Heuristic 2: Keywords
    complex_keywords = ["분석", "비교", "이유", "해결", "기획", "작성", "요약"]
    if any(keyword in text for keyword in complex_keywords):
        return 'gemini-3.1-pro'
        
    return 'gemini-3.1-pro'

def get_ai_response(user_input, chat_history=None, system_prompt=None):
    """AI 상담원 응답 생성 (Composite Mode: Function Calling Enabled)"""
    
    # [Routing] Determine Model
    model_name = determine_model_tier(user_input)
    # print(f"[*] Routing to Model: {model_name}") # Optional logging
    
    model = get_gemini_client(model_name)
    if not model:
        return "죄송합니다. 현재 AI 시스템이 오프라인 상태입니다. 나중에 다시 시도해주세요."
    
    try:
        # 시스템 프롬프트 설정 (기본값 또는 사용자 정의)
        if not system_prompt:
             # Default system prompt (Simplified for brevity in this view)
             system_prompt = "당신은 AI 상담원입니다."

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
