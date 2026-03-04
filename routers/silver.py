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
    # For now, pass a dummy store for points testing, or let it be empty
    store = {"points": 10000, "owner_name": "테스트할아버지", "phone": "010-9999-1111", "address": "서울시 노인정"}
    return templates.TemplateResponse("silver_courier.html", {
        "request": request, 
        "toss_client_key": toss_client_key,
        "store": store 
    })

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
        result_json = json.loads(response.text)
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
        
        # Prepare image for Gemini old SDK
        from google.generativeai.types import BlobDict
        image_blob = BlobDict(
            mime_type=image.content_type or "image/jpeg",
            data=content
        )
        
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
        response = model.generate_content([prompt, image_blob])
        result_json = json.loads(response.text)
        return result_json
        
    except Exception as e:
        print(f"[!] AI Image Parse Error: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "사진 인식 처리 중 오류가 발생했습니다."})
