import os
import random
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response

# 절대 경로 기준 설정 (/home/g5415tv/myserver)
# 배포 환경에서는 지정된 절대 경로를, 로컬에서는 현재 디렉토리를 기준으로 합니다.
if os.path.exists('/home/g5415tv/myserver'):
    BASE_DIR = '/home/g5415tv/myserver'
else:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)

# 세션 보안 (환경변수에서 불러옴)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-1234')
from datetime import timedelta
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
# SESSION_COOKIE_SECURE is enabled in production (POSIX/Linux) but disabled for local HTTP testing
app.config['SESSION_COOKIE_SECURE'] = (os.name == 'posix' or os.environ.get('DB_BACKEND') == 'postgres')
app.config['SESSION_COOKIE_HTTPONLY'] = True

# 핵심 로직이 분리된 모듈 임포트
import tantan_services as services

@app.route('/')
def index():
    # 탄탄제작소 회사 소개 메인 페이지
    return render_template('tantan_index.html')

@app.route('/tech-detail')
def tech_detail():
    # 정부지원 및 기술소개 상세 페이지
    return render_template('tantan_tech_detail.html')

@app.route('/download')
def download():
    # 동네비서 안드로이드 앱 다운로드 센터
    return render_template('tantan_download.html')

@app.route('/terms')
def terms():
    # 동네비서 이용약관 및 개인정보 처리방침
    return render_template('tantan_terms.html')

@app.route('/api/app_version')
def app_version():
    return {"latest_version": "1.9.3", "min_version": "1.0.0", "update_url": "https://dongnebiseo.com/static/apps/dongnebiseo_latest.apk"}

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 폼 제출 시 임시로 홈페이지로 리다이렉트 (가입 상담 접수)
        flash('상담이 접수되었습니다! 담당자가 곧 연락드리겠습니다.', 'success')
        return redirect(url_for('index'))
    return render_template('tantan_register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if services.authenticate_admin(username, password):
            session.permanent = True
            session['admin_logged_in'] = True
            return redirect(url_for('dashboard'), 303)
            
        # 로그인 실패
        flash('아이디 또는 비밀번호가 올바르지 않습니다.', 'error')
            
    return render_template('tantan_login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    # POST로 잘못 들어온 경우 GET으로 리다이렉트
    if request.method == 'POST':
        return redirect(url_for('dashboard'))
    # 보안: 로그인된 관리자만 접근 가능
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    tab = request.args.get('tab')
    stats = services.get_dashboard_stats(tab=tab)
    return render_template('tantan_dashboard.html', stats=stats, current_tab=tab)

@app.route('/documentary-dashboard')
def documentary_dashboard():
    # 보안: 로그인된 관리자만 접근 가능
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    stats = services.get_dashboard_stats()
    return render_template('tantan_documentary.html', stats=stats)

@app.route('/dongnae-dashboard')
def dongnae_dashboard():
    """동네비서 전국 물류 관리 대시보드"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    return render_template('tantan_dongnae.html')

@app.route('/documentary/start')
def documentary_start():
    return render_template('tantan_documentary_start.html')


# =============================================================
# 📡 콜백 블랙박스 모니터 (동네비서 DB 직접 읽기 — 볼륨 마운트)
# =============================================================
import sqlite3 as _sqlite3

# Docker 볼륨으로 마운트된 동네비서 DB 경로
_DNB_DB = "/app/dnb_db/database.db"

def _dnb_query_logs(date_from=None, date_to=None, stage=None, phone=None, limit=300):
    """webhook_logs 직접 조회"""
    if not os.path.exists(_DNB_DB):
        return {"success": False, "error": f"DB 파일 없음: {_DNB_DB}"}
    try:
        # immutable=1: WAL/lock 파일 생성 없이 읽기전용 열기 (read-only 볼륨 대응)
        conn = _sqlite3.connect(f"file:{_DNB_DB}?immutable=1", uri=True)
        conn.row_factory = _sqlite3.Row
        cur = conn.cursor()
        where, params = [], []
        if date_from:
            where.append("DATE(received_at) >= ?")
            params.append(date_from)
        if date_to:
            where.append("DATE(received_at) <= ?")
            params.append(date_to)
        if stage:
            where.append("stage = ?")
            params.append(stage)
        if phone:
            where.append("customer_phone LIKE ?")
            params.append(f"%{phone}%")
        sql = "SELECT * FROM webhook_logs"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY received_at DESC LIMIT ?"
        params.append(int(limit))
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return {"success": True, "logs": rows, "total": len(rows)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _dnb_query_stats(date_from=None, date_to=None):
    """webhook_logs 통계 직접 집계"""
    if not os.path.exists(_DNB_DB):
        return {"success": False, "error": f"DB 파일 없음: {_DNB_DB}"}
    try:
        # immutable=1: WAL/lock 파일 생성 없이 읽기전용 열기
        conn = _sqlite3.connect(f"file:{_DNB_DB}?immutable=1", uri=True)
        cur = conn.cursor()
        where, params = [], []
        if date_from:
            where.append("DATE(received_at) >= ?")
            params.append(date_from)
        if date_to:
            where.append("DATE(received_at) <= ?")
            params.append(date_to)
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        def count(stage_val):
            cur.execute(f"SELECT COUNT(*) FROM webhook_logs {clause} AND stage=?", params + [stage_val])
            return cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM webhook_logs {clause}", params)
        total = cur.fetchone()[0]
        conn.close()
        return {
            "success": True, "total": total,
            "sms_ok":      count('SMS_OK'),
            "sms_fail":    count('SMS_FAIL'),
            "cooldown":    count('COOLDOWN'),
            "auth_fail":   count('AUTH_FAIL'),
            "state_cached":count('STATE_CACHED'),
            "outgoing":    count('OUTGOING_SKIP'),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.route('/admin/webhook-monitor')
def webhook_monitor():
    """콜백 블랙박스 모니터 페이지"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    return render_template('tantan_webhook_monitor.html')

@app.route('/api/admin/webhook-logs')
def proxy_webhook_logs():
    """동네비서 webhook_logs 조회 (DB 직접)"""
    if not session.get('admin_logged_in'):
        return {"success": False, "error": "Unauthorized"}, 401
    return _dnb_query_logs(
        date_from=request.args.get('date_from'),
        date_to=request.args.get('date_to'),
        stage=request.args.get('stage'),
        phone=request.args.get('phone'),
        limit=request.args.get('limit', 300),
    )

@app.route('/api/admin/webhook-stats')
def proxy_webhook_stats():
    """동네비서 webhook_stats 집계 (DB 직접)"""
    if not session.get('admin_logged_in'):
        return {"success": False, "error": "Unauthorized"}, 401
    return _dnb_query_stats(
        date_from=request.args.get('date_from'),
        date_to=request.args.get('date_to'),
    )

# ──────────────────────────────────────────────
# 가입자 상세 / 수정 / 삭제 API
# ──────────────────────────────────────────────
@app.route('/api/admin/store/<store_id>', methods=['GET'])
def api_store_detail(store_id):
    """가입자 전체 정보 조회"""
    if not session.get('admin_logged_in'):
        return {"success": False, "error": "Unauthorized"}, 401
    store = services.get_store_detail(store_id)
    if not store:
        return {"success": False, "error": "가입자 없음"}, 404
    return {"success": True, "store": store}

@app.route('/api/admin/store/<store_id>', methods=['POST'])
def api_store_update(store_id):
    """가입자 정보 수정"""
    if not session.get('admin_logged_in'):
        return {"success": False, "error": "Unauthorized"}, 401
    data = request.get_json(force=True) or {}
    ok, msg = services.update_store(store_id, data)
    return {"success": ok, "message": msg}, (200 if ok else 400)

@app.route('/api/admin/store/<store_id>/delete', methods=['POST'])
def api_store_delete(store_id):
    """가입자 삭제"""
    if not session.get('admin_logged_in'):
        return {"success": False, "error": "Unauthorized"}, 401
    ok, msg = services.delete_store(store_id)
    return {"success": ok, "message": msg}, (200 if ok else 400)

@app.route('/api/admin/funnel-stats')
def proxy_funnel_stats():
    """콜백 퍼널 전환율 통계 (SMS발송→클릭→가입→구매)"""
    if not session.get('admin_logged_in'):
        return {"success": False, "error": "Unauthorized"}, 401
    if not os.path.exists(_DNB_DB):
        return {"success": False, "error": f"DB 없음: {_DNB_DB}"}
    try:
        date_from = request.args.get('date_from')
        date_to   = request.args.get('date_to')
        conn = _sqlite3.connect(f"file:{_DNB_DB}?immutable=1", uri=True)
        cur  = conn.cursor()

        # SMS 발송 (webhook_logs SMS_OK)
        wh_where  = ["stage='SMS_OK'"]
        wh_params = []
        if date_from:
            wh_where.append("DATE(received_at) >= ?"); wh_params.append(date_from)
        if date_to:
            wh_where.append("DATE(received_at) <= ?"); wh_params.append(date_to)
        cur.execute(f"SELECT COUNT(*) FROM webhook_logs WHERE {' AND '.join(wh_where)}", wh_params)
        sms_sent = cur.fetchone()[0]

        # 클릭 / 가입 / 구매 (callback_funnel)
        cf_where, cf_params = [], []
        if date_from:
            cf_where.append("DATE(link_clicked_at) >= ?"); cf_params.append(date_from)
        if date_to:
            cf_where.append("DATE(link_clicked_at) <= ?"); cf_params.append(date_to)
        cf_clause = ("WHERE " + " AND ".join(cf_where)) if cf_where else ""

        def cnt(extra=None):
            sql = f"SELECT COUNT(*) FROM callback_funnel {cf_clause}"
            p   = list(cf_params)
            if extra:
                sql += (" AND " if cf_clause else " WHERE ") + extra
            cur.execute(sql, p)
            return cur.fetchone()[0]

        clicks     = cnt()
        registered = cnt("registered_at IS NOT NULL")
        purchased  = cnt("purchased_at IS NOT NULL")
        conn.close()

        def pct(n, total):
            return round(n / total * 100, 1) if total else 0

        return {
            "success":       True,
            "sms_sent":      sms_sent,
            "clicks":        clicks,
            "registered":    registered,
            "purchased":     purchased,
            "click_rate":    pct(clicks,     sms_sent),
            "register_rate": pct(registered, sms_sent),
            "purchase_rate": pct(purchased,  sms_sent),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================
# 🚨 시스템 로그 API (동네비서 서버 로그 직접 읽기)
# =============================================================
@app.route('/api/logs')
def api_system_logs():
    if not session.get('admin_logged_in'):
        return {"success": False, "error": "Unauthorized"}, 401

    lines_count = int(request.args.get('lines', 100))
    level = request.args.get('level', 'ALL')

    # 도커 볼륨으로 마운트된 동네비서 로그 파일
    log_path = '/app/dnb_logs/error.log'
    if not os.path.exists(log_path):
        return {"logs": [], "total": 0, "message": "로그 파일 없음 (서버 정상 운영 중)"}

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        all_lines = [l.rstrip() for l in f.readlines() if l.strip()]

    if level != 'ALL':
        all_lines = [l for l in all_lines if f'| {level}' in l]

    total = len(all_lines)
    recent = all_lines[-lines_count:]
    error_count = sum(1 for l in all_lines if '| ERROR' in l)

    return {"logs": recent, "total": total, "error_count": error_count}


@app.route('/api/logs/files')
def api_log_files():
    if not session.get('admin_logged_in'):
        return {"success": False, "error": "Unauthorized"}, 401

    log_dir = '/app/dnb_logs'
    if not os.path.exists(log_dir):
        return {"files": []}

    files = []
    for fname in sorted(os.listdir(log_dir), reverse=True):
        fpath = os.path.join(log_dir, fname)
        if os.path.isfile(fpath) and 'error.log' in fname:
            size_kb = round(os.path.getsize(fpath) / 1024, 1)
            files.append({"name": fname, "size_kb": size_kb})
    return {"files": files}


# =============================================================
# 💰 정산 관리 API
# =============================================================
@app.route('/api/settlement/list')
def api_settlement_list():
    if not session.get('admin_logged_in'):
        return {"success": False, "error": "Unauthorized"}, 401
    data = services.get_settlements()
    return {"success": True, "settlements": data}


@app.route('/api/settlement/approve', methods=['POST'])
def api_settlement_approve():
    if not session.get('admin_logged_in'):
        return {"success": False, "error": "Unauthorized"}, 401
    data = request.get_json()
    settlement_id = data.get('id')
    ok = services.update_settlement_status(settlement_id, 'APPROVED')
    return {"success": ok}


@app.route('/api/settlement/transfer', methods=['POST'])
def api_settlement_transfer():
    if not session.get('admin_logged_in'):
        return {"success": False, "error": "Unauthorized"}, 401
    data = request.get_json()
    settlement_id = data.get('id')
    ok = services.update_settlement_status(settlement_id, 'TRANSFERRED')
    return {"success": ok}


@app.route('/api/admin/ledger', methods=['POST'])
def update_ledger():
    if not session.get('admin_logged_in'):
        return {"success": False, "error": "Unauthorized"}, 401
        
    try:
        data = request.get_json()
        revenue = int(data.get('manual_revenue', 0))
        expense = int(data.get('manual_expense', 0))
        
        if services.update_admin_ledger(revenue, expense):
            return {"success": True}
        else:
            return {"success": False, "error": "DB Update Failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}, 400

# ---------------------------------------------------------
# 동네비서 비디오 솔루션 파이프라인 (Phase 1 API Mock)
# ---------------------------------------------------------
import time

@app.route('/api/video/requests', methods=['GET'])
def api_video_requests():
    if not session.get('admin_logged_in'):
        return {"success": False, "error": "Unauthorized"}, 401
    requests = services.get_pending_video_requests()
    return {"success": True, "requests": requests}

@app.route('/api/video/analyze', methods=['POST'])
def api_video_analyze():
    if not session.get('admin_logged_in'):
        return {"success": False, "error": "Unauthorized"}, 401
    time.sleep(1.5) # Simulating AI processing time
    return {"success": True, "message": "입력된 오디오와 사진에서 30초 분량(6개 씬)의 최적 시나리오 및 프롬프트가 성공적으로 추출되었습니다."}

@app.route('/api/video/generate', methods=['POST'])
def api_video_generate():
    if not session.get('admin_logged_in'):
        return {"success": False, "error": "Unauthorized"}, 401
    time.sleep(2.0)
    return {"success": True, "message": "Veo 엔진이 9:16 비율의 무자막 영상 클립 6개를 스타일 일관성(Style Fix)을 유지하며 생성 완료했습니다."}

@app.route('/api/video/synthesize', methods=['POST'])
def api_video_synthesize():
    if not session.get('admin_logged_in'):
        return {"success": False, "error": "Unauthorized"}, 401
    time.sleep(1.5)
    return {"success": True, "message": "Python/FFmpeg 시스템이 밀리초(ms) 단위로 완벽하게 싱크를 맞춰 동네비서 로고와 한글 자막 합성을 마쳤습니다."}

@app.route('/api/video/qc', methods=['POST'])
def api_video_qc():
    if not session.get('admin_logged_in'):
        return {"success": False, "error": "Unauthorized"}, 401
    time.sleep(1.0)
    return {"success": True, "message": "Gemini Vision QC 통과! 영상 내 오타 및 프레임 오류가 발견되지 않았습니다. 앱으로 즉시 배포 가능합니다."}

# ---------------------------------------------------------
# Local GPU (ComfyUI API) 보안 터널 브릿지
# ---------------------------------------------------------
@app.route('/api/documentary/request', methods=['POST'])
def api_documentary_request():
    if request.content_type and request.content_type.startswith('multipart/form-data'):
        text = request.form.get('text', '')
        theme = request.form.get('theme', 'q18')
        mood = request.form.get('mood', 'energetic')
        
        svd_input_dir = r"C:\Users\A\Desktop\SVD_Input"
        import os
        os.makedirs(svd_input_dir, exist_ok=True)
        
        # Save story context for the Master Orchestrator
        import json
        from datetime import datetime
        context = {
            "text": text,
            "theme": theme,
            "mood": mood,
            "timestamp": datetime.now().isoformat()
        }
        with open(os.path.join(svd_input_dir, "story_context.json"), "w", encoding="utf-8") as f:
            json.dump(context, f, ensure_ascii=False, indent=4)
        
        photos = request.files.getlist('photos')
        if photos:
            from werkzeug.utils import secure_filename
            for i, photo in enumerate(photos):
                if photo.filename:
                    filename = secure_filename(photo.filename)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_name = f"web_{timestamp}_{i}_{filename}"
                    photo.save(os.path.join(svd_input_dir, safe_name))
    else:
        data = request.json or {}
        text = data.get('text', '')
        theme = data.get('theme', 'q18')
        mood = data.get('mood', 'energetic')
    
    request_id = services.add_video_request("guest", "GuestUser", text, theme)
    if request_id:
        return {"success": True, "job_id": f"vultr-job-{theme}-{request_id}"}
    return {"success": False, "error": "DB Error"}, 500

# GPU Worker 스크립트가 Polling 방식으로 작업을 가져가는 API
@app.route('/api/gpu/job', methods=['GET'])
def api_gpu_job():
    auth = request.headers.get('Authorization')
    if auth != "Bearer tantan-secure-tunnel-token-2026":
        return {"success": False, "error": "Unauthorized Tunnel Access"}, 401
    
    pending_jobs = services.get_pending_video_requests()
    if not pending_jobs:
        return {"success": False, "message": "No pending jobs"}
        
    job = pending_jobs[0]
    services.update_video_request_status(job['id'], 'processing')
    
    user_text = job['story'] or "정도"
    theme = job['images'] or "q18"
    
    return {
        "success": True,
        "job": {
            "job_id": f"vultr-job-{theme}-{job['id']}",
            "theme": theme,
            "prompt": {
                "3": {
                    "class_type": "KSampler",
                    "inputs": {
                        "seed": random.randint(100000, 999999), "steps": 20, "cfg": 7.5, "sampler_name": "euler", "scheduler": "normal", "denoise": 1,
                        "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]
                    }
                },
                "4": {
                    "class_type": "CheckpointLoaderSimple",
                    "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}
                },
                "5": {
                    "class_type": "EmptyLatentImage",
                    "inputs": {"width": 1024, "height": 1024, "batch_size": 1}
                },
                "6": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"text": user_text, "clip": ["4", 1]}
                },
                "7": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"text": "bad quality, watermark, noisy", "clip": ["4", 1]}
                },
                "8": {
                    "class_type": "VAEDecode",
                    "inputs": {"samples": ["3", 0], "vae": ["4", 2]}
                },
                "9": {
                    "class_type": "SaveImage",
                    "inputs": {"filename_prefix": f"tantan_{theme}_{job['id']}", "images": ["8", 0]}
                }
            }
        }
    }
import queue
import json

class MessageAnnouncer:
    def __init__(self):
        self.listeners = []

    def listen(self):
        q = queue.Queue(maxsize=100)
        self.listeners.append(q)
        return q

    def announce(self, msg):
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(msg)
            except queue.Full:
                del self.listeners[i]

gpu_announcer = MessageAnnouncer()

# GPU Worker 스크립트가 작업 상태 및 렌더링 결과를 갱신하는 API
@app.route('/api/gpu/upload', methods=['POST'])
def api_gpu_upload():
    auth = request.headers.get('Authorization')
    if auth != "Bearer tantan-secure-tunnel-token-2026":
        return {"success": False, "error": "Unauthorized Tunnel Access"}, 401

    if 'file' not in request.files:
        return {"success": False, "error": "No file part"}, 400
        
    file = request.files['file']
    if file.filename == '':
        return {"success": False, "error": "No selected file"}, 400
        
    import os
    import time
    from werkzeug.utils import secure_filename
    
    upload_folder = os.path.join(app.root_path, 'static', 'outputs')
    os.makedirs(upload_folder, exist_ok=True)
    
    filename = secure_filename(file.filename)
    # Add timestamp to avoid cache conflicts
    name, ext = os.path.splitext(filename)
    unique_filename = f"{name}_{int(time.time())}{ext}"
    
    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)
    
    # Convert image to a short video with zoom-pan effect using FFmpeg
    if ext.lower() in ['.png', '.jpg', '.jpeg']:
        import subprocess
        video_filename = f"{name}_{int(time.time())}.mp4"
        video_path = os.path.join(upload_folder, video_filename)
        try:
            # Apply a slow zoom-in (Ken Burns) effect for 5 seconds at 25fps (125 frames)
            cmd = [
                'ffmpeg', '-y', '-loop', '1', '-i', file_path,
                '-vf', "zoompan=z='min(zoom+0.0015,1.5)':d=125:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720",
                '-c:v', 'libx264', '-t', '5', '-pix_fmt', 'yuv420p', video_path
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            unique_filename = video_filename
        except Exception as e:
            print(f"FFmpeg video conversion failed: {e}")
            # If it fails, fallback to the original image
    
    return {
        "success": True, 
        "url": f"/static/outputs/{unique_filename}"
    }

@app.route('/api/gpu/status', methods=['POST'])
def api_gpu_status():
    auth = request.headers.get('Authorization')
    if auth != "Bearer tantan-secure-tunnel-token-2026":
        return {"success": False, "error": "Unauthorized Tunnel Access"}, 401
    
    data = request.json
    job_id = data.get('job_id')
    status = data.get('status')
    message = data.get('message', '')
    
    # Broadcast to SSE
    sse_msg = f"data: {json.dumps({'job_id': job_id, 'status': status, 'message': message})}\n\n"
    gpu_announcer.announce(sse_msg)
    
    # If completed, extract URL and update database
    if status == 'COMPLETED':
        try:
            msg_obj = json.loads(message)
            url = msg_obj.get('url', '')
            # Extract request_id from job_id (e.g., vultr-job-q18-3)
            parts = job_id.split('-')
            if len(parts) >= 4:
                request_id = parts[-1]
                services.update_video_request_complete(request_id, url)
        except Exception as e:
            print(f"Failed to update complete status in DB: {e}")
    
    return {"success": True, "message": f"Status updated for {job_id} -> {status}"}

@app.route('/api/gpu/metrics', methods=['POST'])
def api_gpu_metrics():
    auth = request.headers.get('Authorization')
    if auth != "Bearer tantan-secure-tunnel-token-2026":
        return {"success": False, "error": "Unauthorized Tunnel Access"}, 401
    
    data = request.json
    vram_used = data.get('vram_used', 0)
    vram_total = data.get('vram_total', 12282)
    
    # Broadcast to SSE
    sse_msg = f"data: {json.dumps({'type': 'metrics', 'vram_used': vram_used, 'vram_total': vram_total})}\n\n"
    gpu_announcer.announce(sse_msg)
    
    return {"success": True, "message": "Metrics updated"}

@app.route('/api/gpu/stream')
def api_gpu_stream():
    def stream():
        messages = gpu_announcer.listen()
        while True:
            try:
                msg = messages.get(timeout=15)
                yield msg
            except queue.Empty:
                yield ": heartbeat\n\n"
            
    return Response(stream(), mimetype='text/event-stream')

# 404 에러 핸들러 (사용자 친화적 페이지)

# ──────────────────────────────────────────────────────────────
# [TEMP] 솔라피 발송 직접 테스트 라우터
# ──────────────────────────────────────────────────────────────
@app.route('/api/test/solapi')
def test_solapi():
    import traceback, datetime, re, hmac, hashlib, uuid, requests as _req
    from flask import Response as _Resp

    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # ── 환경변수 ──────────────────────────────────────────────
    api_key        = os.getenv('SOLAPI_API_KEY', '')
    api_secret     = os.getenv('SOLAPI_API_SECRET', '')
    fixed_sender   = os.getenv('SOLAPI_SENDER_NUMBER', os.getenv('SENDER_PHONE', '01023847447'))
    pf_id          = os.getenv('SOLAPI_PF_ID', '')
    template_id    = os.getenv('SOLAPI_TEMPLATE_ID', '')

    # 수신자 = 대표님 번호 (테스트용)
    client_target_phone = re.sub(r'[^0-9]', '', fixed_sender)

    env_keys = ['SOLAPI_API_KEY','SOLAPI_API_SECRET','SOLAPI_SENDER_NUMBER',
                'SENDER_PHONE','SOLAPI_PF_ID','SOLAPI_TEMPLATE_ID']
    env_rows = ''
    for k in env_keys:
        v = os.getenv(k, '')
        masked = (v[:4]+'****'+v[-3:]) if len(v) > 10 else ('OK' if v else 'MISSING')
        col = '#dc2626' if not v else '#16a34a'
        env_rows += (
            f'<tr><td style="padding:6px 14px;color:#94a3b8;white-space:nowrap">{k}</td>'
            f'<td style="padding:6px 14px;color:{col};font-family:monospace">{masked}</td></tr>'
        )

    sms_ok = 'NOT_RUN'; sms_info = ''
    atalk_ok = 'NOT_RUN'; atalk_info = ''

    def _make_auth_header():
        date = datetime.datetime.now().astimezone().isoformat()
        salt = uuid.uuid4().hex
        sig  = hmac.new(
            api_secret.encode('utf-8'),
            (date + salt).encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f'HMAC-SHA256 apiKey={api_key}, date={date}, salt={salt}, signature={sig}'

    # ── SMS 테스트 ────────────────────────────────────────────
    if not api_key or not api_secret:
        sms_ok = 'SKIP'; sms_info = 'SOLAPI_API_KEY / API_SECRET 없음'
    elif not client_target_phone:
        sms_ok = 'SKIP'; sms_info = 'SOLAPI_SENDER_NUMBER 없음'
    else:
        try:
            payload = {
                'message': {
                    'to':   client_target_phone,  # 수신자: 정형화된 대표 번호 (테스트)
                    'from': fixed_sender,          # 발신자: 솔라피 등록 상수
                    'text': '[탄탄제작소] SMS Test OK ' + now_str,
                }
            }
            r1 = _req.post(
                'https://api.solapi.com/messages/v4/send',
                headers={'Authorization': _make_auth_header(), 'Content-Type': 'application/json'},
                json=payload, timeout=10
            )
            sms_ok = 'SUCCESS' if r1.status_code == 200 else f'FAIL({r1.status_code})'
            sms_info = r1.text[:400]
        except Exception as e1:
            sms_ok = 'ERROR'
            sms_info = type(e1).__name__ + ': ' + str(e1)[:400] + '\n\n' + traceback.format_exc()[-700:]

    # ── Alimtalk 테스트 ───────────────────────────────────────
    if not api_key or not api_secret:
        atalk_ok = 'SKIP'; atalk_info = 'API 키 없음'
    elif not template_id or not pf_id:
        atalk_ok = 'SKIP'; atalk_info = f'SOLAPI_TEMPLATE_ID={template_id!r} / SOLAPI_PF_ID={pf_id!r}'
    elif not client_target_phone:
        atalk_ok = 'SKIP'; atalk_info = '수신자 번호 없음'
    else:
        try:
            payload2 = {
                'message': {
                    'to':   client_target_phone,
                    'from': fixed_sender,
                    'text': '[탄탄제작소] Alimtalk Test ' + now_str,
                    'kakaoOptions': {
                        'pfId': pf_id,
                        'templateId': template_id,
                        'variables': {'#{event}': 'TantanfabTest', '#{time}': now_str},
                    }
                }
            }
            r2 = _req.post(
                'https://api.solapi.com/messages/v4/send',
                headers={'Authorization': _make_auth_header(), 'Content-Type': 'application/json'},
                json=payload2, timeout=10
            )
            atalk_ok = 'SUCCESS' if r2.status_code == 200 else f'FAIL({r2.status_code})'
            atalk_info = r2.text[:400]
        except Exception as e2:
            atalk_ok = 'ERROR'
            atalk_info = type(e2).__name__ + ': ' + str(e2)[:400] + '\n\n' + traceback.format_exc()[-700:]

    def badge(s):
        col = '#16a34a' if 'SUCCESS' in s else ('#f59e0b' if 'SKIP' in s else '#dc2626')
        return f'<span style="background:{col};color:#fff;padding:3px 12px;border-radius:20px;font-weight:700;font-size:.8rem">{s}</span>'

    def prebox(s):
        if not s: return ''
        return (f'<pre style="background:#020617;color:#fbbf24;padding:12px;border-radius:8px;'
                f'font-size:.74rem;margin-top:8px;white-space:pre-wrap;word-break:break-all;'
                f'border:1px solid #1e293b">{s}</pre>')

    html = (
        "<!DOCTYPE html><html lang='ko'><head>"
        "<meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>탄탄제작소 Solapi Test</title>"
        "<link href='https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap' rel='stylesheet'>"
        "<style>"
        "*{box-sizing:border-box;margin:0;padding:0}"
        "body{font-family:'Noto Sans KR',sans-serif;background:#0f172a;color:#f1f5f9;padding:32px 16px}"
        ".card{background:#1e293b;border-radius:20px;padding:28px;max-width:860px;margin:0 auto 20px;box-shadow:0 25px 50px rgba(0,0,0,.5)}"
        ".pbox{background:#0f172a;border:2px solid #f59e0b;border-radius:14px;padding:18px 24px;"
        "display:flex;align-items:center;gap:20px;margin-bottom:20px;flex-wrap:wrap}"
        ".plabel{font-size:.72rem;font-weight:800;color:#f59e0b;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px}"
        ".pnum{font-size:1.25rem;font-weight:900;font-family:monospace;color:#fbbf24}"
        "h1{font-size:1.4rem;font-weight:900;margin-bottom:4px}"
        ".sub{color:#64748b;font-size:.85rem;margin-bottom:20px}"
        "h3{font-size:.9rem;font-weight:700;color:#94a3b8;margin:20px 0 8px;display:flex;align-items:center;gap:8px}"
        "table{width:100%;border-collapse:collapse;background:#0f172a;border-radius:10px;overflow:hidden}"
        "tr{border-bottom:1px solid #1e293b}tr:last-child{border-bottom:none}td{vertical-align:top;font-size:.84rem}"
        ".btn{display:block;text-align:center;padding:13px;background:#f59e0b;border-radius:10px;"
        "color:#0f172a;text-decoration:none;font-weight:800;font-size:.95rem;max-width:860px;margin:0 auto}"
        "</style></head><body>"
        "<div class='card'>"
        "<h1>&#x1F9EA; 탄탄제작소 Solapi Direct Test</h1>"
        f"<p class='sub'>Time: {now_str}</p>"
        "<div class='pbox'>"
        "<div style='font-size:2rem'>&#x1F4F2;</div>"
        "<div style='flex:1'>"
        "<div class='plabel'>&#x1F4E8; Recipient — 메시지 받는 사람</div>"
        f"<div class='pnum'>{client_target_phone}</div>"
        "</div>"
        "<div style='width:2px;background:#334155;height:48px;border-radius:2px'></div>"
        "<div style='flex:1'>"
        "<div class='plabel'>&#x1F4E4; Sender — 솔라피 발신번호 (상수)</div>"
        f"<div class='pnum' style='color:#94a3b8'>{fixed_sender}</div>"
        "</div>"
        "</div>"
        f"<h3>&#x1F511; ENV Variables</h3><table>{env_rows}</table>"
        f"<h3>&#x1F4AC; SMS: {badge(sms_ok)}</h3>{prebox(sms_info)}"
        f"<h3>&#x1F514; Alimtalk: {badge(atalk_ok)}</h3>{prebox(atalk_info)}"
        "</div>"
        "<a href='/api/test/solapi' class='btn'>&#x21BA; Re-run Test</a>"
        "</body></html>"
    )
    return _Resp(html, mimetype='text/html')


@app.errorhandler(404)
def page_not_found(e):
    return render_template('tantan_404.html'), 404

# 500 에러 핸들러 (사용자 친화적 페이지)
@app.errorhandler(500)
def internal_server_error(e):
    return render_template('tantan_500.html'), 500

if __name__ == '__main__':
    # Gunicorn 환경이 아닐 때만 실행됨
    app.run(host='0.0.0.0', port=5000, debug=True)
