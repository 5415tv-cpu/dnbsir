from flask import Flask, request, jsonify
import google.generativeai as genai
from celery import Celery
import os
import uuid
import sys
from pathlib import Path

# media_worker 모듈 임포트를 위한 sys.path 설정
ROOT = Path(r"C:\Users\A\Desktop\AI_Store")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from media_worker.pipeline.script_generator import generate_script

# ==========================================
# 1. 제미나이 AI 및 워커(Celery) 세팅
# ==========================================
genai.configure(api_key="AIzaSyCsbEwG5sIP20GafzwyH9askctgGIzvysg")
model = genai.GenerativeModel('gemini-flash-latest')

REDIS_URL = os.environ.get('DONGNE_REDIS_URL', 'redis://127.0.0.1:6379/0')
celery_app = Celery('webhook_client', broker=REDIS_URL)

app = Flask(__name__)

# 영상 결과물을 제공할 정적 폴더 생성
VIDEO_DIR = ROOT / "static" / "videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

@app.route('/videos/<path:filename>')
def serve_video(filename):
    from flask import send_from_directory
    return send_from_directory(str(VIDEO_DIR), filename)

# 임시 메모리 저장소: 앱에서 요청한 대본 세션 상태 관리
APP_SESSIONS = {}

# 임시 메모리 저장소: 고객별 승인 대기 상태 관리 (카카오 챗봇용)
# 구조: { user_id: { 'script': '대본 내용', 'status': 'WAITING_APPROVAL' } }
PENDING_ORDERS = {}

# ==========================================
# 2. App 연동 API 라우트
# ==========================================

@app.route('/api/v1/app/video/request', methods=['POST'])
def app_video_request():
    """앱에서 농장 정보를 받아 영상 대본(Script)을 생성해 반환"""
    try:
        body = request.get_json(force=True)
        user_id = body.get('user_id', 'unknown_user')
        merchant_facts = body.get('merchant_facts', {})
        
        if not merchant_facts:
            return jsonify({"status": "error", "message": "merchant_facts is required"}), 400

        print(f"[{user_id}] App에서 영상 대본 생성 요청 수신")
        
        script_json = generate_script(merchant_facts)
        
        session_id = str(uuid.uuid4())
        APP_SESSIONS[session_id] = {
            'user_id': user_id,
            'script_json': script_json,
            'status': 'WAITING_APPROVAL'
        }
        
        return jsonify({
            "status": "success",
            "session_id": session_id,
            "script_json": script_json
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/v1/app/video/confirm', methods=['POST'])
def app_video_confirm():
    """앱에서 대본을 확인하고 렌더링(제작)을 승인"""
    try:
        body = request.get_json(force=True)
        user_id = body.get('user_id')
        session_id = body.get('session_id')
        script_json = body.get('script_json') 
        
        if not session_id or session_id not in APP_SESSIONS:
            return jsonify({"status": "error", "message": "Invalid session_id"}), 404
            
        session_data = APP_SESSIONS[session_id]
        if not script_json:
            script_json = session_data['script_json']
            
        # 워커로 프리미엄 렌더링 작업 전송
        task = celery_app.send_task(
            'worker.render_short_form_video',
            args=[user_id, script_json]
        )
        print(f"[{user_id}] 프리미엄 렌더링 작업 전송. Task ID: {task.id}")
        
        del APP_SESSIONS[session_id]
        return jsonify({
            "status": "processing",
            "task_id": task.id
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# 3. 기존 카카오 챗봇용 라우트
# ==========================================

@app.route('/api', methods=['POST']) 
def kakao_chat():
    try:
        body = request.get_json(force=True)
        if not body:
            body = {}
        
        # 카카오톡 유저 고유 ID (없으면 'test_user' 사용)
        user_id = body.get('userRequest', {}).get('user', {}).get('id', 'test_user')
        user_message = body.get('userRequest', {}).get('utterance', '').strip()
        
        print(f"[{user_id}] 들어온 메시지: {user_message}")
        
        # 2. 상태 확인 로직 (대본 승인 대기 중인지 체크)
        user_state = PENDING_ORDERS.get(user_id)
        
        if user_state and user_state['status'] == 'WAITING_APPROVAL':
            # 사용자가 승인 또는 거절을 선택한 경우
            if user_message in ["승인", "진행해", "좋아", "진행", "콜", "ok", "OK", "오케이"]:
                # 승인 처리: 워커로 렌더링 작업 전송
                script_content = user_state['script']
                
                # 워커 큐로 작업 보내기
                task = celery_app.send_task(
                    'worker.render_short_form_video',
                    args=[
                        user_id,
                        "https://dnbsir.com/dummy_apple.jpg", # 임시 썸네일
                        script_content
                    ]
                )
                print(f"[{user_id}] 렌더링 작업 전송 완료. Task ID: {task.id}")
                
                # 상태 초기화
                del PENDING_ORDERS[user_id]
                
                reply_text = "✅ 대본이 승인되었습니다!\n탄탄제작소 시스템이 즉시 렌더링을 시작합니다.\n영상이 완성되면 다시 알려드리겠습니다."
                
            elif user_message in ["거절", "취소", "아니", "별로"]:
                # 거절 처리: 상태 초기화
                del PENDING_ORDERS[user_id]
                reply_text = "❌ 영상 제작이 취소되었습니다. 원하시는 내용을 다시 자세히 말씀해 주시면 새로운 대본을 짜드릴게요!"
                
            else:
                # 엉뚱한 대답 처리
                reply_text = "현재 대본 승인 대기 중입니다.\n이 대본으로 영상을 제작하려면 '승인', 취소하려면 '취소'를 입력해 주세요."
                
            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [{"simpleText": {"text": reply_text}}]
                }
            })
            
        # 3. 새로운 영상 기획 요청인 경우 (제미나이 대본 생성)
        system_prompt = (
            f"너는 동네비서 홍보 영상을 기획하는 천재 마케터야. "
            f"사용자가 제품이나 상황을 입력하면, 반드시 다음 4가지 핵심 포인트를 포함해서 30초짜리 숏폼 대본을 짜줘.\n"
            f"1. 고객의 전화\n"
            f"2. 전화를 받는 농부/소상공인\n"
            f"3. 핸드폰 간편 주문 링크 전송 및 결제 (가장 강조)\n"
            f"4. 택배 기사의 빠르고 정확한 배달\n"
            f"사용자 요청: {user_message}"
        )
        
        response = model.generate_content(system_prompt)
        ai_answer = response.text
        
        # 상태를 승인 대기 중으로 변경
        PENDING_ORDERS[user_id] = {
            'script': ai_answer,
            'status': 'WAITING_APPROVAL'
        }
        
        # 카카오톡 응답 메시지에 "승인 여부 묻기" 추가
        final_reply = f"[AI가 작성한 영상 대본]\n\n{ai_answer}\n\n====================\n💡 이 대본으로 바로 영상을 제작할까요?\n(진행하려면 '승인', 취소하려면 '취소'를 입력해 주세요)"
        
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": final_reply}}]
            }
        })

    except Exception as e:
        import traceback
        with open('error.log', 'w', encoding='utf-8') as f:
            f.write(f"에러 발생: {e}\n")
            traceback.print_exc(file=f)
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": "현재 시스템 점검 중이거나 응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요."}}]
            }
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8005)