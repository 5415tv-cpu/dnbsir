from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
import os
import json
import traceback

# Try to use the modern SDK, fallback to old one if needed
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

class VoiceTextRequest(BaseModel):
    text: str

class ChatMessage(BaseModel):
    message: str
    current_state: dict

def get_gemini_model(model_name="gemini-2.5-flash"):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY is missing.")
    genai.configure(api_key=api_key)
    # Using JSON mode for structured output
    return genai.GenerativeModel(model_name, generation_config={"response_mime_type": "application/json"})

# 1. Page Route
@router.get("/silver/courier", response_class=HTMLResponse)
async def silver_courier_page(request: Request):
    toss_client_key = os.getenv("TOSS_CLIENT_KEY", "test_ck_PBal2vxj81ND2OPW6a7135RQgOAN")
    # Using an empty store to force the user to provide info, testing chat UX
    store = {} 
    return templates.TemplateResponse("silver_courier.html", {
        "request": request, 
        "toss_client_key": toss_client_key,
        "store": store 
    })

# 1.5 Conversational AI Endpoint
@router.post("/api/ai/chat")
async def chat_with_ai(data: ChatMessage):
    if not HAS_GENAI:
        raise HTTPException(status_code=500, detail="Gemini SDK not installed")
        
    prompt = f"""
    You are an AI assistant helping elderly people send a parcel.
    You must extract information from the user's message and update the current state.
    Be very polite, use large, clear text conceptually (brief sentences), and speak like a friendly helper.

    CURRENT STATE (JSON):
    {json.dumps(data.current_state, ensure_ascii=False)}

    USER MESSAGE:
    "{data.message}"

    Required information to collect:
    - sender_name (보내는 분 이름)
    - sender_phone (보내는 분 전화번호, hyphens added)
    - sender_addr (보내는 분 주소, include details)
    - receiver_name (받는 분 이름)
    - receiver_phone (받는 분 전화번호, hyphens added)
    - receiver_addr (받는 분 주소, include details)
    - item_type (물품 종류: e.g., 김치, 과일, 옷, 서류 등)
    - quantity (몇 박스인지, default to 1 if not mentioned)
    
    INSTRUCTIONS:
    1. Extract any new information from the USER MESSAGE and merge it with the CURRENT STATE. Fix typos if obvious.
    2. Identify what required information is still missing.
    3. Generate a `next_message` (Korean) asking for ONE OR TWO missing pieces of information naturally. 
       - If everything is collected, `next_message` should summarize the order (Sender, Receiver, Item, Box count) and ask for final confirmation (e.g. "이대로 결제창을 띄워드릴까요?").
       - Keep `next_message` short, polite, and easy for the elderly to understand.
    4. Set `is_complete` to true ONLY if all required fields are present AND the user has agreed/confirmed to proceed in the current message.
    
    Return ONLY a valid JSON object with the following structure:
    {{
        "extracted_data": {{ updated state object with all gathered keys }},
        "next_message": "...",
        "is_complete": false or true
    }}
    """
    
    try:
        model = get_gemini_model()
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        result_json = json.loads(text.strip())
        return result_json
    except Exception as e:
        print(f"[!] AI Chat Parse Error: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "대화 처리 중 오류가 발생했습니다."})

# 2. Voice Parsing Endpoint
@router.post("/api/ai/parse-voice")
async def parse_voice(data: VoiceTextRequest):
    if not HAS_GENAI:
        raise HTTPException(status_code=500, detail="Gemini SDK not installed")
    
    prompt = f"""
    You are an AI assistant helping elderly people input parcel delivery information.
    Extract the following details from the user's spoken text.
    Return ONLY a valid JSON object with these keys (use empty string if not mentioned):
    - receiver_name: The name of the person receiving the parcel.
    - receiver_phone: The phone number of the receiver. Add hyphens if missing.
    - receiver_addr: The full address of where to send it.
    - item_type: What is being sent (e.g., 김치, 과일, 옷).
    
    User spoken text: "{data.text}"
    """
    
    try:
        model = get_gemini_model()
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        result_json = json.loads(text.strip())
        return result_json
    except Exception as e:
        print(f"[!] AI Voice Parse Error: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "음성 인식 처리 중 오류가 발생했습니다."})

# 3. Image Parsing Endpoint
@router.post("/api/ai/parse-image")
async def parse_image(image: UploadFile = File(...)):
    if not HAS_GENAI:
        raise HTTPException(status_code=500, detail="Gemini SDK not installed")
        
    try:
        content = await image.read()
        
        prompt = """
        You are an AI assistant helping elderly people parse handwritten or printed shipping labels.
        Extract the following details from the image.
        Return ONLY a valid JSON object with these keys (use empty string if not mentioned):
        - receiver_name: The name of the receiver (받는 사람/수령인).
        - receiver_phone: The phone number of the receiver. Add hyphens if missing.
        - receiver_addr: The full address of the receiver.
        - item_type: What is being sent, if visible (품목/내용물).
        """
        model = get_gemini_model("gemini-1.5-flash") # Use 1.5-flash for image parsing if 2.5 is not available
        
        # Prepare image using a standard dict
        image_part = {
            "mime_type": image.content_type or "image/jpeg",
            "data": content
        }
        
        response = model.generate_content([prompt, image_part])
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        result_json = json.loads(text.strip())
        return result_json
        
    except Exception as e:
        print(f"[!] AI Image Parse Error: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "사진 인식 처리 중 오류가 발생했습니다."})
