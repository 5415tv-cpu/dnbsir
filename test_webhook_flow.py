import requests
import json
import time
import sys

# Windows cp949 에러 방지용 UTF-8 설정
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
import time

URL = "http://127.0.0.1:8005/api"

def send_message(user_id, utterance):
    payload = {
        "userRequest": {
            "user": {"id": user_id},
            "utterance": utterance
        }
    }
    try:
        res = requests.post(URL, json=payload)
        print(f"\n[USER: {utterance}]")
        print(f"STATUS: {res.status_code}")
        print(f"RAW RES: {res.text}")
        print(f"[BOT ] {res.json()['template']['outputs'][0]['simpleText']['text']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Test 1: Requesting a video script")
    send_message("test_user_999", "사과 농장 홍보 영상 하나 만들어줘")
    
    time.sleep(2)
    
    print("\nTest 2: Approving the script")
    send_message("test_user_999", "승인")
