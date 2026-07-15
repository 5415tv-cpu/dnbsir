import requests
import time
import json
import os

API_BASE = "http://127.0.0.1:8005/api/v1/app/video"

# 1. 앱에서 영상 제작 요청 (Request)
print("1. 앱에서 대본 생성 요청 전송 중...")
request_data = {
    # 테스트를 위해 .env의 SOLAPI_SENDER_NUMBER와 동일하게 맞추면 알림톡 수신 가능
    "user_id": os.environ.get("SOLAPI_SENDER_NUMBER", "01023847447"),
    "merchant_facts": {
        "product": "경북 영주 꿀사과",
        "price": "5kg 29,900원",
        "origin": "경북 영주 소백산맥",
        "features": ["당도 14브릭스 이상", "산지직송", "무료배송"],
        "cta": "동네비서 앱 주문"
    }
}

response = requests.post(f"{API_BASE}/request", json=request_data)
if response.status_code != 200:
    print("❌ 대본 요청 실패:", response.text)
    exit(1)

res_json = response.json()
print("✅ 대본 생성 성공!")
session_id = res_json['session_id']
script = res_json['script_json']

print("\n--- 생성된 대본 ---")
for scene in script.get('scenes', []):
    print(f"씬 {scene['scene_id']}: {scene['narration']}")
print("-------------------\n")

# 2. 고객 확인 및 승인 (Confirm)
print("2. 고객이 앱에서 승인 버튼 클릭 (3초 대기...)")
time.sleep(3)

confirm_data = {
    "user_id": request_data["user_id"],
    "session_id": session_id,
    "script_json": script # 수정된 대본을 올린다고 가정
}

print("3. 승인 데이터 전송 중...")
conf_res = requests.post(f"{API_BASE}/confirm", json=confirm_data)
if conf_res.status_code != 200:
    print("❌ 승인 요청 실패:", conf_res.text)
    exit(1)

print("✅ 승인 완료! 백그라운드 워커에서 렌더링이 시작되었습니다.")
print("   응답:", conf_res.json())
print("\n이제 별도의 터미널에서 실행 중인 Celery Worker 로그를 확인하세요.")
print("렌더링이 완료되면 카카오 알림톡이 발송됩니다.")
