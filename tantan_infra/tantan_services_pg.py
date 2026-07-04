import os
import psycopg2
import psycopg2.extras

# 데이터베이스 경로 설정
# 1. Vultr 프로덕션 환경 경로 확인
if os.path.exists('/var/www/dnbsir/database.db'):
    DB_PATH = '/var/www/dnbsir/database.db'
# 2. 로컬 개발 환경 경로 확인
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database.db')

def authenticate_admin(username, password):
    """
    관리자 로그인 인증을 수행합니다.
    환경변수 또는 config.toml에 지정된 계정 및 비밀번호와 비교합니다.
    """
    # 1. Check environment variables
    admin_user = os.environ.get('ADMIN_USERNAME')
    admin_pass = os.environ.get('ADMIN_PASSWORD')
    
    # 2. Check config.toml if env vars are not set
    if not admin_user or not admin_pass:
        try:
            import toml
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.toml')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = toml.load(f)
                admin_user = admin_user or config.get('admin', {}).get('username')
                admin_pass = admin_pass or config.get('admin', {}).get('password')
        except Exception as e:
            print(f"Error loading admin config from toml: {e}")
            
    # 3. Check secrets.toml in parent directory (for local development/test convenience)
    if not admin_user or not admin_pass:
        try:
            import toml
            secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'secrets.toml')
            if os.path.exists(secrets_path):
                with open(secrets_path, 'r', encoding='utf-8') as f:
                    secrets = toml.load(f)
                admin_user = admin_user or secrets.get('admin', {}).get('id')
                admin_pass = admin_pass or secrets.get('admin', {}).get('password')
        except Exception as e:
            print(f"Error loading admin config from secrets.toml: {e}")

    # 4. Fallback to secure defaults if everything else fails
    if not admin_user:
        admin_user = 'admin8705'
    if not admin_pass:
        admin_pass = 'Aass12!!'
        
    # Check if the username matches the configured admin username OR standard admin identifiers,
    # and if the password matches the configured admin password.
    allowed_usernames = [admin_user, "master", "010-2384-7447", "01023847447"]
    return username in allowed_usernames and password == admin_pass

def calculate_korean_income_tax(taxable_income):
    """
    국세청 종합소득세 과세표준(2024년 귀속) 기준을 바탕으로 소득세를 계산합니다.
    (과세표준 * 세율) - 누진공제액
    """
    if taxable_income <= 0:
        return 0
    elif taxable_income <= 14000000:
        return int(taxable_income * 0.06)
    elif taxable_income <= 50000000:
        return int(taxable_income * 0.15 - 1260000)
    elif taxable_income <= 88000000:
        return int(taxable_income * 0.24 - 5760000)
    elif taxable_income <= 150000000:
        return int(taxable_income * 0.35 - 15440000)
    elif taxable_income <= 300000000:
        return int(taxable_income * 0.38 - 19940000)
    elif taxable_income <= 500000000:
        return int(taxable_income * 0.40 - 25940000)
    elif taxable_income <= 1000000000:
        return int(taxable_income * 0.42 - 35940000)
    else:
        return int(taxable_income * 0.45 - 65940000)

# ──────────────────────────────────────────────
# 가입자 상세조회 / 수정 / 삭제 (PostgreSQL)
# ──────────────────────────────────────────────
def get_store_detail(store_id):
    """특정 가입자 전체 컬럼 조회"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM stores WHERE store_id = %s", (store_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"[get_store_detail] {e}")
        return None


def update_store(store_id, fields: dict):
    """가입자 정보 수정 (허용 필드만)"""
    ALLOWED = {
        'name', 'owner_name', 'phone', 'category', 'info', 'address',
        'wallet_balance', 'points', 'membership', 'subscription_tier',
        'role', 'status', 'my_referral_code', 'referrer_id',
        'biz_number', 'bank_code', 'account_number', 'account_holder',
        'smart_callback_on', 'auto_reply_msg', 'auto_reply_missed', 'auto_reply_end',
        'fee_rate', 'marketing_agreed', 'memo'
    }
    safe = {k: v for k, v in fields.items() if k in ALLOWED}
    if not safe:
        return False, "수정 가능한 필드가 없습니다"
    try:
        conn = get_connection()
        c = conn.cursor()
        set_clause = ", ".join(f"{k} = %s" for k in safe)
        values = list(safe.values()) + [store_id]
        c.execute(f"UPDATE stores SET {set_clause} WHERE store_id = %s", values)
        conn.commit()
        conn.close()
        return True, "수정 완료"
    except Exception as e:
        return False, str(e)


def delete_store(store_id):
    """가입자 삭제"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM stores WHERE store_id = %s", (store_id,))
        affected = c.rowcount
        conn.commit()
        conn.close()
        if affected == 0:
            return False, "해당 가입자 없음"
        return True, "삭제 완료"
    except Exception as e:
        return False, str(e)


def get_dashboard_stats(tab=None):
    """
    PostgreSQL 데이터베이스에서 관리자 대시보드용 주요 지표를 집계하여 반환합니다.
    """
    stats = {
        'total_users': 0,
        'total_citizens': 0,
        'total_farmers': 0,
        'total_drivers': 0,
        'total_stores': 0,
        'total_sms': 0,
        'total_deliveries': 0,
        'total_ai_calls': 0,
        'manual_revenue': 0,
        'manual_expense': 0,
        'est_sms_cost': 0,
        'est_ai_cost': 0,
        'total_est_cost': 0,
        'total_wallet_balance': 0,
        'total_revenue': 0,
        'total_expense': 0,
        'net_profit': 0,
        'est_vat': 0,
        'est_income_tax': 0,
        'db_size_mb': 0.0,
        'db_status': 'unknown',
        'db_message': '데이터베이스 로딩 대기 중',
        'all_stores': [],
        'recent_ai_logs': [],
        'recent_sms_logs': [],
        'recent_reservations': [],
        'recent_deliveries': [],
        'recent_drivers': [],
        'recent_stores': []
    }
    
    try:
        conn = psycopg2.connect(dbname="dongnebiseo", user="tandan", password="대표님비밀번호", host="host.docker.internal", port="5432")
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # 관리자용 설정 테이블 초기화 (최초 1회)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()
        
        # 수기 장부 내역 가져오기
        cursor.execute("SELECT key, value FROM admin_settings WHERE key IN ('manual_revenue', 'manual_expense')")
        settings_dict = {row['key']: row['value'] for row in cursor.fetchall()}
        
        manual_revenue = int(settings_dict.get('manual_revenue', '0'))
        manual_expense = int(settings_dict.get('manual_expense', '0'))
        stats['manual_revenue'] = manual_revenue
        stats['manual_expense'] = manual_expense
        
        # 1. 일반 사용자 수
        cursor.execute("SELECT COUNT(*) as count FROM users")
        stats['total_users'] = cursor.fetchone()['count']
        
        # 2. 전체 가입자/매장 수
        cursor.execute("SELECT role FROM stores")
        all_roles = [row['role'] for row in cursor.fetchall()]
        stats['total_stores'] = sum(1 for r in all_roles if r in ['owner', None, ''])
        stats['total_citizens'] = sum(1 for r in all_roles if r == 'citizen')
        stats['total_farmers'] = sum(1 for r in all_roles if r == 'farmer')
        stats['total_users'] = len(all_roles)
        
        # 3. SMS 발송 건수
        cursor.execute("SELECT COUNT(*) as count FROM sms_logs")
        stats['total_sms'] = cursor.fetchone()['count']
        
        # 4. 배송 건수
        try:
            cursor.execute("SELECT COUNT(*) as count FROM courier_requests")
            stats['total_deliveries'] = cursor.fetchone()['count']
        except Exception:
            conn.rollback()
            stats['total_deliveries'] = 0
            
        # 5. AI 통화/응답 처리 건수
        cursor.execute("SELECT COUNT(*) as count FROM ai_call_logs")
        stats['total_ai_calls'] = cursor.fetchone()['count']
        
        # 5-1. 등록된 배달 기사/라이더 수
        total_drivers = 0
        try:
            cursor.execute("SELECT COUNT(*) as count FROM couriers")
            total_drivers += cursor.fetchone()['count']
        except Exception:
            conn.rollback()
        try:
            cursor.execute("SELECT COUNT(*) as count FROM riders")
            total_drivers += cursor.fetchone()['count']
        except Exception:
            conn.rollback()
        stats['total_drivers'] = total_drivers
        
        # 6. 최근 AI 통화 내역
        if tab == 'ai' or not tab:
            cursor.execute("""
                SELECT store_id, customer_phone, summary, created_at 
                FROM ai_call_logs 
                ORDER BY id DESC LIMIT 50
            """)
            stats['recent_ai_logs'] = [dict(row) for row in cursor.fetchall()]
        
        # 7. 최근 SMS 발송 내역
        if tab == 'sms' or not tab:
            cursor.execute("""
                SELECT store_id, phone, message, status, created_at 
                FROM sms_logs 
                ORDER BY id DESC LIMIT 50
            """)
            stats['recent_sms_logs'] = [dict(row) for row in cursor.fetchall()]
            
        # 최근 예약 내역
        if tab == 'reservations' or not tab:
            try:
                cursor.execute("""
                    SELECT store_id, customer_name, res_date, res_time, status 
                    FROM reservations 
                    ORDER BY id DESC LIMIT 50
                """)
                stats['recent_reservations'] = [dict(row) for row in cursor.fetchall()]
            except Exception:
                conn.rollback()
                
        # 최근 택배 내역
        if tab == 'deliveries' or not tab:
            try:
                cursor.execute("""
                    SELECT citizen_id as store_id, sender_name, receiver_name, receiver_phone, status, tracking_code as tracking_num 
                    FROM courier_requests 
                    ORDER BY request_id DESC LIMIT 50
                """)
                stats['recent_deliveries'] = [dict(row) for row in cursor.fetchall()]
            except Exception:
                conn.rollback()
                
        # 배달 기사 내역
        if tab == 'drivers' or not tab:
            stats['recent_drivers'] = []
            try:
                cursor.execute("SELECT courier_id as driver_id, name, phone, '택배기사' as type, status, created_at FROM couriers ORDER BY created_at DESC LIMIT 25")
                stats['recent_drivers'].extend([dict(row) for row in cursor.fetchall()])
            except Exception:
                conn.rollback()
            try:
                cursor.execute("SELECT rider_id as driver_id, name, phone, '배달라이더' as type, status, created_at FROM riders ORDER BY created_at DESC LIMIT 25")
                stats['recent_drivers'].extend([dict(row) for row in cursor.fetchall()])
            except Exception:
                conn.rollback()
        
        # 8. 전체 가맹점 목록 (관제용 - 필터링)
        if tab in ['stores', 'citizens', 'farmers'] or not tab:
            query = "SELECT store_id, name, owner_name, phone, points, wallet_balance, created_at, role, my_referral_code FROM stores"
            if tab == 'stores':
                query += " WHERE role NOT IN ('citizen', 'farmer') OR role IS NULL"
            elif tab == 'citizens':
                query += " WHERE role = 'citizen'"
            elif tab == 'farmers':
                query += " WHERE role = 'farmer'"
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query)
            stats['all_stores'] = [dict(row) for row in cursor.fetchall()]
        
        # 비용 계산 (단가 가정: SMS 15원, AI 20원)
        stats['est_sms_cost'] = stats['total_sms'] * 15
        stats['est_ai_cost'] = stats['total_ai_calls'] * 20
        stats['total_est_cost'] = stats['est_sms_cost'] + stats['est_ai_cost']
        
        # 전체 상점 잔액 (매출/충전금액 추정)
        cursor.execute("SELECT SUM(wallet_balance) as sum_balance FROM stores")
        total_balance = cursor.fetchone()['sum_balance']
        total_balance = total_balance if total_balance else 0
        stats['total_wallet_balance'] = total_balance
        
        # 실제 매출 및 지출 재계산 (수기 입력 포함)
        stats['total_revenue'] = total_balance + manual_revenue
        stats['total_expense'] = stats['total_est_cost'] + manual_expense
        stats['net_profit'] = stats['total_revenue'] - stats['total_expense']
        
        # 세금 계산 (국세청 기본 공식 적용)
        stats['est_vat'] = max(0, int((stats['total_revenue'] - stats['total_expense']) * 0.1))
        taxable_income = stats['net_profit']
        stats['est_income_tax'] = calculate_korean_income_tax(taxable_income)
        
        # DB 상태 및 용량 체크 (대용량 경고 로직)
        try:
            cursor.execute("SELECT pg_database_size('dongnebiseo') as db_size")
            db_size_bytes = cursor.fetchone()['db_size']
            db_size_mb = db_size_bytes / (1024.0 * 1024.0)
            stats['db_size_mb'] = db_size_mb
            
            if db_size_mb > 50.0 or stats['total_users'] > 100000:
                stats['db_status'] = 'warning'
                stats['db_message'] = '데이터베이스 용량이 임계점(50MB)을 초과했거나 동시 접속자가 많습니다. 안정적인 서비스를 위해 대용량 외부 DB(Google Cloud SQL 등)로의 마이그레이션을 준비해 주세요.'
            else:
                stats['db_status'] = 'healthy'
                stats['db_message'] = '정상 작동 중'
        except Exception as e:
            stats['db_status'] = 'unknown'
            stats['db_message'] = 'DB 용량 확인 불가'

        # 9. 지점별 정산 및 지급 현황 (택배비 / 직판 / 위탁판매)
        courier_data = {}
        try:
            cursor.execute("SELECT store_id, fare, status FROM deliveries WHERE status IN ('완료', '배송완료', '수거완료', '접수완료')")
            for row in cursor.fetchall():
                s_id = row['store_id']
                if not s_id: continue
                fare = int(row['fare'] or 0)
                payout = fare - 1000 - int(fare * 0.033)
                if payout < 0: payout = 0
                courier_data[s_id] = courier_data.get(s_id, 0) + payout
        except Exception as e:
            try:
                conn.rollback()
            except:
                pass
            print(f"Error fetching courier payouts: {e}")

        sales_data = {}
        try:
            cursor.execute("SELECT store_id, type, net_amount, amount, fee_amount FROM orders")
            for row in cursor.fetchall():
                s_id = row['store_id']
                if not s_id: continue
                o_type = row['type']
                
                net_amount = row['net_amount']
                if net_amount is None:
                    amount = int(row['amount'] or 0)
                    fee_amount = int(row['fee_amount'] or amount * 0.033)
                    net_amount = amount - fee_amount
                else:
                    net_amount = int(net_amount)
                
                if s_id not in sales_data:
                    sales_data[s_id] = {'direct_sales': 0, 'consignment_sales': 0}
                    
                if o_type in ['FARM', 'DIRECT']:
                    sales_data[s_id]['direct_sales'] += net_amount
                elif o_type in ['CONSIGN', '위탁']:
                    sales_data[s_id]['consignment_sales'] += net_amount
        except Exception as e:
            try:
                conn.rollback()
            except:
                pass
            print(f"Error fetching orders payouts: {e}")

        branch_settlements = []
        try:
            cursor.execute("SELECT store_id, name, owner_name, phone FROM stores WHERE role IS NULL OR role = '' OR role = 'owner' ORDER BY name ASC")
            for row in cursor.fetchall():
                s_id = row['store_id']
                c_payout = courier_data.get(s_id, 0)
                
                s_info = sales_data.get(s_id, {'direct_sales': 0, 'consignment_sales': 0})
                d_sales = s_info['direct_sales']
                c_sales = s_info['consignment_sales']
                
                total_payout = c_payout + d_sales + c_sales
                
                branch_settlements.append({
                    'store_id': s_id,
                    'name': row['name'] or '이름 없음',
                    'owner_name': row['owner_name'] or '미입력',
                    'phone': row['phone'] or '미입력',
                    'courier_payout': c_payout,
                    'direct_sales': d_sales,
                    'consignment_sales': c_sales,
                    'total_payout': total_payout
                })
        except Exception as e:
            try:
                conn.rollback()
            except:
                pass
            print(f"Error merging branch settlements: {e}")

        stats['branch_settlements'] = branch_settlements
        
        conn.close()
    except Exception as e:
        print(f"Error fetching dashboard stats: {e}")
        
    return stats

def init_video_requests_table():
    try:
        conn = psycopg2.connect(dbname="dongnebiseo", user="tandan", password="대표님비밀번호", host="host.docker.internal", port="5432")
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_requests (
                id SERIAL PRIMARY KEY,
                store_id TEXT,
                store_name TEXT,
                status TEXT DEFAULT 'pending',
                requested_at TEXT,
                completed_at TEXT
            )
        ''')
        # Add new columns if they don't exist
        try:
            cursor.execute("ALTER TABLE video_requests ADD COLUMN story TEXT")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE video_requests ADD COLUMN images TEXT")
        except Exception:
            pass
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error init video table: {e}")

def add_video_request(store_id, store_name, story="", images=""):
    init_video_requests_table()
    try:
        conn = psycopg2.connect(dbname="dongnebiseo", user="tandan", password="대표님비밀번호", host="host.docker.internal", port="5432")
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        import datetime
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO video_requests (store_id, store_name, story, images, requested_at) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (store_id, store_name, story, images, now)
        )
        new_id = cursor.fetchone()['id']
        conn.commit()
        conn.close()
        return new_id
    except Exception as e:
        print(f"Error adding video request: {e}")
        return None

def update_video_request_status(request_id, status):
    try:
        conn = psycopg2.connect(dbname="dongnebiseo", user="tandan", password="대표님비밀번호", host="host.docker.internal", port="5432")
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("UPDATE video_requests SET status = %s WHERE id = %s", (status, request_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating video request status: {e}")
        return False

def get_pending_video_requests():
    init_video_requests_table()
    try:
        conn = psycopg2.connect(dbname="dongnebiseo", user="tandan", password="대표님비밀번호", host="host.docker.internal", port="5432")
        pass # handled by RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM video_requests WHERE status = 'pending' ORDER BY requested_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error fetching video requests: {e}")
        return []

def get_store_video_requests(store_id):
    init_video_requests_table()
    try:
        conn = psycopg2.connect(dbname="dongnebiseo", user="tandan", password="대표님비밀번호", host="host.docker.internal", port="5432")
        pass # handled by RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM video_requests WHERE store_id = %s ORDER BY requested_at DESC", (store_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error fetching store video requests: {e}")
        return []

def complete_video_request(request_id):
    try:
        conn = psycopg2.connect(dbname="dongnebiseo", user="tandan", password="대표님비밀번호", host="host.docker.internal", port="5432")
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("UPDATE video_requests SET status = 'completed', completed_at = %s WHERE id = %s", (now, request_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error completing video request: {e}")
        return False

def authenticate_store(username, password):
    """
    database.db의 stores 테이블을 조회하여 상점(소상공인) 로그인을 인증합니다.
    username은 store_id 혹은 phone 번호로 매칭합니다.
    """
    try:
        conn = psycopg2.connect(dbname="dongnebiseo", user="tandan", password="대표님비밀번호", host="host.docker.internal", port="5432")
        pass # handled by RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute(
            "SELECT store_id, name, owner_name, points, wallet_balance FROM stores WHERE (store_id = %s OR phone = %s) AND password = %s",
            (username, username, password)
        )
        store = cursor.fetchone()
        conn.close()
        
        if store:
            return dict(store)
    except Exception as e:
        print(f"Error authenticating store: {e}")
        
    return None

def get_store_dashboard_data(store_id):
    """
    특정 상점의 고유 데이터(내 상점 정보, 최근 AI/SMS/배송 로그)를 가져옵니다.
    """
    data = {
        'info': {},
        'ai_logs': [],
        'sms_logs': [],
        'deliveries': []
    }
    
    try:
        conn = psycopg2.connect(dbname="dongnebiseo", user="tandan", password="대표님비밀번호", host="host.docker.internal", port="5432")
        pass # handled by RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # 상점 정보
        cursor.execute("SELECT name, owner_name, points, wallet_balance, phone FROM stores WHERE store_id = %s", (store_id,))
        store_info = cursor.fetchone()
        if store_info:
            data['info'] = dict(store_info)
            
        # 최근 AI 콜백 내역 5건
        cursor.execute("SELECT customer_phone, summary, created_at FROM ai_call_logs WHERE store_id = %s ORDER BY created_at DESC LIMIT 5", (store_id,))
        data['ai_logs'] = [dict(row) for row in cursor.fetchall()]
        
        # 최근 SMS 발송 내역 5건
        cursor.execute("SELECT phone, message, status, created_at FROM sms_logs WHERE store_id = %s ORDER BY created_at DESC LIMIT 5", (store_id,))
        data['sms_logs'] = [dict(row) for row in cursor.fetchall()]
        
        # 최근 택배 배송 내역 5건
        cursor.execute("SELECT item_name, receiver_name, status, created_at FROM deliveries WHERE store_id = %s ORDER BY created_at DESC LIMIT 5", (store_id,))
        data['deliveries'] = [dict(row) for row in cursor.fetchall()]
        
        # 최근 상품/방문 예약 접수 내역 5건
        cursor.execute("SELECT customer_name, contact, res_date, res_time, status, created_at FROM reservations WHERE store_id = %s ORDER BY created_at DESC LIMIT 5", (store_id,))
        data['reservations'] = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
    except Exception as e:
        print(f"Error fetching store data: {e}")
        
    return data

def find_store_id(owner_name, phone):
    """
    이름(owner_name)과 전화번호(phone)로 상점 아이디를 찾습니다.
    """
    try:
        conn = psycopg2.connect(dbname="dongnebiseo", user="tandan", password="대표님비밀번호", host="host.docker.internal", port="5432")
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # owner_name이나 name(상호명) 중 하나라도 일치하면 검색
        cursor.execute(
            "SELECT store_id FROM stores WHERE (owner_name = %s OR name = %s) AND phone = %s",
            (owner_name, owner_name, phone)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return row[0]
    except Exception as e:
        print(f"Error finding store id: {e}")
        
    return None

def reset_store_password(store_id, phone, new_password):
    """
    상점 아이디(store_id)와 전화번호(phone)가 일치하면 새로운 비밀번호로 변경합니다.
    """
    try:
        conn = psycopg2.connect(dbname="dongnebiseo", user="tandan", password="대표님비밀번호", host="host.docker.internal", port="5432")
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # 계정 검증
        cursor.execute(
            "SELECT store_id FROM stores WHERE store_id = %s AND phone = %s",
            (store_id, phone)
        )
        row = cursor.fetchone()
        
        if row:
            # 일치하면 비밀번호 업데이트
            cursor.execute(
                "UPDATE stores SET password = %s WHERE store_id = %s",
                (new_password, store_id)
            )
            conn.commit()
            conn.close()
            return True
            
        conn.close()
    except Exception as e:
        print(f"Error resetting password: {e}")
        
    return False

def create_store_account(owner_name, phone, category, store_name, password):
    """
    새로운 상점 계정을 생성하고 초기 포인트(1000)를 지급합니다.
    store_id는 휴대폰 번호(phone)와 동일하게 설정합니다.
    """
    try:
        conn = psycopg2.connect(dbname="dongnebiseo", user="tandan", password="대표님비밀번호", host="host.docker.internal", port="5432")
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # 중복 계정 체크 (휴대폰 번호 기준)
        cursor.execute("SELECT store_id FROM stores WHERE store_id = %s OR phone = %s", (phone, phone))
        if cursor.fetchone():
            conn.close()
            return False, "이미 가입된 휴대폰 번호입니다."
            
        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 새 계정 INSERT (초기 지갑 잔액 1000포인트)
        cursor.execute("""
            INSERT INTO stores (store_id, password, name, owner_name, phone, category, points, wallet_balance, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, 0, 1000, %s)
        """, (phone, password, store_name, owner_name, phone, category, now))
        
        conn.commit()
        conn.close()
        return True, "회원가입이 성공적으로 완료되었습니다."
    except Exception as e:
        print(f"Error creating account: {e}")
        return False, f"가입 처리 중 오류가 발생했습니다: {e}"

def update_admin_ledger(revenue, expense):
    """
    수기 매출/지출 내역을 데이터베이스에 업데이트합니다.
    """
    try:
        conn = psycopg2.connect(dbname="dongnebiseo", user="tandan", password="대표님비밀번호", host="host.docker.internal", port="5432")
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # 테이블 생성 확인
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # 데이터 갱신
        cursor.execute("INSERT INTO admin_settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", ("manual_revenue", str(revenue)))
        cursor.execute("INSERT INTO admin_settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", ("manual_expense", str(expense)))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating admin ledger: {e}")
        return False


# =============================================================
# 💰 정산 관리 함수
# =============================================================
def _init_settlements_table(conn):
    """settlements 테이블이 없으면 생성"""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settlements (
            id SERIAL PRIMARY KEY,
            store_id TEXT NOT NULL,
            store_name TEXT,
            owner_name TEXT,
            phone TEXT,
            amount INTEGER NOT NULL DEFAULT 0,
            fee INTEGER NOT NULL DEFAULT 0,
            net_amount INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'PENDING',
            description TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            approved_at TIMESTAMP,
            transferred_at TIMESTAMP
        )
    """)
    conn.commit()


def get_settlements():
    """전체 정산 목록 조회 (최신순)"""
    try:
        conn = psycopg2.connect(dbname="dongnebiseo", user="tandan", password="대표님비밀번호", host="host.docker.internal", port="5432")
        _init_settlements_table(conn)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT id, store_id, store_name, owner_name, phone,
                   amount, fee, net_amount, status, description,
                   to_char(created_at, 'YYYY-MM-DD HH24:MI') as created_at,
                   to_char(approved_at, 'YYYY-MM-DD HH24:MI') as approved_at,
                   to_char(transferred_at, 'YYYY-MM-DD HH24:MI') as transferred_at
            FROM settlements
            ORDER BY created_at DESC
            LIMIT 200
        """)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"Error fetching settlements: {e}")
        return []


def update_settlement_status(settlement_id, new_status):
    """정산 상태 변경: PENDING → APPROVED → TRANSFERRED"""
    import datetime
    valid = {'APPROVED', 'TRANSFERRED', 'PENDING'}
    if new_status not in valid:
        return False
    try:
        conn = psycopg2.connect(dbname="dongnebiseo", user="tandan", password="대표님비밀번호", host="host.docker.internal", port="5432")
        cursor = conn.cursor()
        now = datetime.datetime.now()

        if new_status == 'APPROVED':
            cursor.execute(
                "UPDATE settlements SET status=%s, approved_at=%s WHERE id=%s AND status='PENDING'",
                (new_status, now, settlement_id)
            )
        elif new_status == 'TRANSFERRED':
            cursor.execute(
                "UPDATE settlements SET status=%s, transferred_at=%s WHERE id=%s AND status='APPROVED'",
                (new_status, now, settlement_id)
            )
        else:
            cursor.execute("UPDATE settlements SET status=%s WHERE id=%s", (new_status, settlement_id))

        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0
    except Exception as e:
        print(f"Error updating settlement status: {e}")
        return False


def create_settlement(store_id, store_name, owner_name, phone, amount, fee_rate=0.033, description=''):
    """새 정산 항목 생성 (수수료 자동 계산)"""
    fee = int(amount * fee_rate)
    net_amount = amount - fee
    try:
        conn = psycopg2.connect(dbname="dongnebiseo", user="tandan", password="대표님비밀번호", host="host.docker.internal", port="5432")
        _init_settlements_table(conn)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO settlements (store_id, store_name, owner_name, phone, amount, fee, net_amount, status, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDING', %s)
            RETURNING id
        """, (store_id, store_name, owner_name, phone, amount, fee, net_amount, description))
        new_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        return new_id
    except Exception as e:
        print(f"Error creating settlement: {e}")
        return None
