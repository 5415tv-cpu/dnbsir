import config
import requests
import uuid
import time
import base64
import json

def call_naver_ocr(image_bytes):
    """
    Call Naver OCR API with image bytes.
    Returns: dict with {name, phone, address, items} or None
    """
    # 1. Check Secrets
    api_url = config.get_secret("naver_ocr_url")
    secret_key = config.get_secret("naver_ocr_secret")
    
    # 2. Mock Mode if keys missing
    if not api_url or not secret_key:
        time.sleep(2) # Simulate delay
        return _get_mock_data()
        
    # 3. Real API Call
    try:
        request_json = {
            "images": [
                {
                    "format": "jpg",
                    "name": "demo_image",
                    "data": base64.b64encode(image_bytes).decode('utf-8')
                }
            ],
            "requestId": str(uuid.uuid4()),
            "version": "V2",
            "timestamp": int(time.time() * 1000)
        }
        
        headers = {
            "X-OCR-SECRET": secret_key,
            "Content-Type": "application/json"
        }
        
        response = requests.post(api_url, headers=headers, data=json.dumps(request_json))
        if response.status_code == 200:
            result = response.json()
            return _parse_ocr_result(result)
        else:
            print(f"OCR Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"OCR Exception: {e}")
        return None

def _get_mock_data():
    """Returns dummy data for demonstration"""
    return {
        "sender_name": "김철수",
        "sender_phone": "010-1234-5678",
        "receiver_name": "홍길동",
        "receiver_phone": "010-9876-5432",
        "address": "서울시 강남구 테헤란로 123, 101호",
        "item_name": "의류(티셔츠)",
        "message": "부재시 문앞 보관"
    }

def _parse_ocr_result(ocr_json):
    """
    Parse Naver OCR raw response to extract key fields.
    This is heuristic-based.
    """
    # Simplification: Just concatenate all text for now or look for keywords.
    # A real implementation would filter by coordinate or field mapping.
    full_text = ""
    for image in ocr_json.get("images", []):
        for field in image.get("fields", []):
            full_text += field.get("inferText", "") + " "
            
    # Naive Extraction (Demo)
    return {
        "sender_name": "", # Logic needed
        "receiver_name": "",
        "address": full_text[:50] + "...", # Just dump text
        "raw_text": full_text
    }
