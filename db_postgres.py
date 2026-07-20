import psycopg2
import psycopg2.extras
import os
from datetime import datetime
import json
import pandas as pd

DB_FILE = "database.db"

def get_connection():
    try:
        # Connect to local postgresql
        conn = psycopg2.connect(
            dbname="dongnebiseo",
            user="tandan",
            password="대표님비밀번호",
            host="localhost",
            port="5432"
        )
        # Use RealDictCursor to act like sqlite3.Row
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn
    except Exception as e:
        print(f"DB Error: {e}")
        return None

def init_db():
    """Initialize the database tables."""
    conn = get_connection()
    if conn is None:
        print("[!] PostgreSQL Connection failed during init_db()")
        return
    conn.autocommit = True
    c = conn.cursor()

    # 1. Users / User Management
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            password TEXT,
            name TEXT,
            phone TEXT,
            level TEXT,
            joined_at TEXT,
            total_payment INTEGER DEFAULT 0,
            fee_amount INTEGER DEFAULT 0,
            settle_date TEXT,
            settle_status TEXT,
            net_amount INTEGER DEFAULT 0,
            plan_status TEXT,
            home_address TEXT
        )
    ''')
    
    # Add home_address column if not exists
    try:
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS home_address TEXT")
    except Exception:
        pass
    
    # 2. Stores
    c.execute('''
        CREATE TABLE IF NOT EXISTS stores (
            store_id TEXT PRIMARY KEY,
            password TEXT,
            name TEXT,
            owner_name TEXT,
            phone TEXT,
            category TEXT,
            info TEXT,
            menu_text TEXT,
            printer_ip TEXT,
            table_count INTEGER DEFAULT 0,
            seats_per_table INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0,
            membership TEXT,
            created_at TEXT,
            referrer_id TEXT DEFAULT '',
            subscription_tier TEXT DEFAULT 'general',
            first_tx_completed INTEGER DEFAULT 0,
            business_type TEXT DEFAULT 'hotel'
        )
    ''')

    # Migration for stores table business_type in PostgreSQL
    try:
        c.execute("ALTER TABLE stores ADD COLUMN IF NOT EXISTS business_type TEXT DEFAULT 'hotel'")
    except Exception:
        pass


    # 2-0. Driver Rewards
    c.execute('''
        CREATE TABLE IF NOT EXISTS rewards (
            id SERIAL PRIMARY KEY,
            driver_id TEXT,
            store_id TEXT,
            amount INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    ''')
    
    # 2-1. Couriers (Parcel Drivers)
    c.execute('''
        CREATE TABLE IF NOT EXISTS couriers (
            courier_id TEXT PRIMARY KEY,
            name TEXT,
            phone TEXT,
            company TEXT,
            vehicle_type TEXT,
            status TEXT,
            created_at TEXT
        )
    ''')

    # 2-2. Riders (Delivery Part-time)
    c.execute('''
        CREATE TABLE IF NOT EXISTS riders (
            rider_id TEXT PRIMARY KEY,
            name TEXT,
            phone TEXT,
            area TEXT,
            status TEXT,
            created_at TEXT
        )
    ''')
    
    # 2-3. Courier Requests (Citizen -> Logistics)
    c.execute('''
        CREATE TABLE IF NOT EXISTS courier_requests (
            request_id SERIAL PRIMARY KEY,
            citizen_id TEXT,
            sender_name TEXT,
            sender_phone TEXT,
            sender_addr TEXT,
            receiver_name TEXT,
            receiver_phone TEXT,
            receiver_addr TEXT,
            item_type TEXT,
            weight TEXT,
            status TEXT DEFAULT 'pending',
            payment_method TEXT,
            tracking_code TEXT,
            created_at TEXT,
            FOREIGN KEY(citizen_id) REFERENCES stores(store_id)
        )
    ''')

    # 3. Business Records (General, Delivery, Farmer)
    # Using a single flexible table or separate ones. Separate is cleaner for this legacy code.
    c.execute('''
        CREATE TABLE IF NOT EXISTS records_general (
            id SERIAL PRIMARY KEY,
            store_id TEXT,
            date_time TEXT,
            customer_name TEXT,
            contact TEXT,
            menu_info TEXT,
            head_count INTEGER,
            reservation_time TEXT,
            is_ai_served INTEGER,
            amount INTEGER,
            created_at TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS records_delivery (
            id SERIAL PRIMARY KEY,
            store_id TEXT,
            date_time TEXT,
            sender_name TEXT,
            receiver_name TEXT,
            receiver_addr TEXT,
            item_type TEXT,
            tracking_code TEXT,
            fee INTEGER,
            status TEXT,
            created_at TEXT
        )
    ''')

    # 4. Wallet & Logs
    c.execute('''
        CREATE TABLE IF NOT EXISTS wallet_logs (
            id SERIAL PRIMARY KEY,
            store_id TEXT,
            change_type TEXT,
            amount INTEGER,
            balance_after INTEGER,
            memo TEXT,
            created_at TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS wallet_topups (
            id SERIAL PRIMARY KEY,
            store_id TEXT,
            amount INTEGER,
            depositor TEXT,
            status TEXT,
            processed_at TEXT,
            requested_at TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS message_logs (
            id SERIAL PRIMARY KEY,
            store_id TEXT,
            receiver TEXT,
            cost INTEGER,
            status TEXT,
            channel TEXT,
            created_at TEXT
        )
    ''')


    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            store_id TEXT,
            name TEXT,
            price INTEGER,
            description TEXT,
            image_path TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id SERIAL PRIMARY KEY,
            store_id TEXT,
            customer_name TEXT,
            contact TEXT,
            res_date TEXT,
            res_time TEXT,
            head_count INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            guest_info TEXT,
            room_id TEXT,
            check_in TEXT,
            check_out TEXT,
            expiry_time INTEGER
        )
    ''')

    # Migration for existing PostgreSQL databases
    for col, col_type in [("guest_info", "TEXT"), ("room_id", "TEXT"), ("check_in", "TEXT"), ("check_out", "TEXT"), ("expiry_time", "INTEGER")]:
        try:
            c.execute(f"ALTER TABLE reservations ADD COLUMN IF NOT EXISTS {col} {col_type}")
        except Exception:
            pass



    c.execute('''
        CREATE TABLE IF NOT EXISTS store_settings (
            store_id TEXT,
            key TEXT,
            value TEXT,
            PRIMARY KEY (store_id, key)
        )
    ''')
    

    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            store_id TEXT,
            type TEXT, -- MENU, RESERVE, PARCEL
            item_name TEXT,
            amount INTEGER,
            fee_amount INTEGER DEFAULT 0,
            net_amount INTEGER DEFAULT 0,
            settlement_status TEXT DEFAULT 'pending',
            customer_phone TEXT,
            created_at TEXT
        )
    ''') 
    
    # 5. Schema Migration (Safe Add)
    try:
        c.execute("ALTER TABLE delivery_orders ADD COLUMN waybill_number TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE delivery_orders ADD COLUMN error_message TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE delivery_orders ADD COLUMN payload TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE stores ADD COLUMN fee_rate REAL DEFAULT 0.033")
    except: pass
    try:
        c.execute("ALTER TABLE stores ADD COLUMN wallet_balance INTEGER DEFAULT 0")
    except: pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN fee_amount INTEGER DEFAULT 0")
    except: pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN net_amount INTEGER DEFAULT 0")
    except: pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN settlement_status TEXT DEFAULT 'pending'")
    except: pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN courier_id TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN rider_id TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN courier_id TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN rider_id TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN payment_method TEXT DEFAULT 'CARD'")
    except: pass
    
    try:
        c.execute("ALTER TABLE stores ADD COLUMN is_signed INTEGER DEFAULT 0")
    except: pass
    try:
        c.execute("ALTER TABLE stores ADD COLUMN role TEXT DEFAULT 'merchant'")
    except: pass

    # Kakao Biz Customization
    try:
        c.execute("ALTER TABLE stores ADD COLUMN kakao_biz_key TEXT")
    except: pass

    # ... (rest of init_db)


    # ... (rest of init_db)
    try:
        c.execute("ALTER TABLE stores ADD COLUMN use_custom_kakao INTEGER DEFAULT 0")
    except: pass

    # Smart Callback — DEFAULT 1 (항상 활성화, 절대 풀리지 않음)
    try:
        c.execute("ALTER TABLE stores ADD COLUMN smart_callback_on INTEGER DEFAULT 1")
    except: pass
    # 기존 레코드가 0으로 되어 있으면 1로 강제 복구
    try:
        c.execute("UPDATE stores SET smart_callback_on=1 WHERE smart_callback_on IS NULL OR smart_callback_on=0")
        conn.commit()
    except: pass
    try:
        c.execute("ALTER TABLE stores ADD COLUMN smart_callback_text TEXT")
    except: pass
    
    # Auto Reply Settings
    try:
        c.execute("ALTER TABLE stores ADD COLUMN auto_reply_msg TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE stores ADD COLUMN auto_reply_missed INTEGER DEFAULT 1")
    except: pass
    try:
        c.execute("ALTER TABLE stores ADD COLUMN auto_reply_end INTEGER DEFAULT 0")
    except: pass
    
    # Auto Refill Settings
    try:
        c.execute("ALTER TABLE stores ADD COLUMN auto_refill_on INTEGER DEFAULT 0")
    except: pass
    try:
        c.execute("ALTER TABLE stores ADD COLUMN auto_refill_amount INTEGER DEFAULT 50000")
    except: pass

    # ★ stores.my_referral_code — DNBXK7A2 형식 고유 추천인 코드 (PostgreSQL)
    try:
        c.execute("ALTER TABLE stores ADD COLUMN my_referral_code TEXT DEFAULT ''")
    except: pass
    try:
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS uidx_stores_referral_code ON stores(my_referral_code) WHERE my_referral_code <> ''")
    except: pass

    # Product Inventory
    try:
        c.execute("ALTER TABLE products ADD COLUMN inventory INTEGER DEFAULT 100")
    except: pass

    # Customers (CRM / Memory)
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
            customer_id TEXT,
            store_id TEXT,
            name TEXT,
            phone TEXT,
            address TEXT,
            preferences TEXT,
            notes TEXT,
            total_orders INTEGER DEFAULT 0,
            last_visit TEXT,
            created_at TEXT,
            UNIQUE(customer_id, store_id)
        )
    ''')

    # Virtual Number Mapping (050)
    c.execute('''
        CREATE TABLE IF NOT EXISTS virtual_numbers (
            virtual_number TEXT PRIMARY KEY,
            store_id TEXT,
            label TEXT,
            status TEXT,
            created_at TEXT
        )
    ''')
    
    # SMS Logs
    c.execute('''CREATE TABLE IF NOT EXISTS sms_logs
                 (id SERIAL PRIMARY KEY,
                  store_id TEXT,
                  phone TEXT,
                  category TEXT,
                  message TEXT,
                  status TEXT,
                  response TEXT,
                  created_at TEXT)''')
                  
    # AI Call Logs
    c.execute('''
        CREATE TABLE IF NOT EXISTS ai_call_logs (
            id SERIAL PRIMARY KEY,
            store_id TEXT,
            customer_phone TEXT,
            customer_name TEXT,
            intent TEXT,
            summary TEXT,
            audio_url TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TEXT
        )
    ''')
    
    try:
        c.execute("ALTER TABLE ai_call_logs ADD COLUMN event_type TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE ai_call_logs ADD COLUMN event_details TEXT")
    except: pass

    # AI Security Logs
    c.execute('''
        CREATE TABLE IF NOT EXISTS security_logs (
            id SERIAL PRIMARY KEY,
            store_id TEXT,
            customer_phone TEXT,
            event_type TEXT,
            payload TEXT,
            created_at TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS call_logs (
            id SERIAL PRIMARY KEY,
            customer_phone TEXT,
            my_number TEXT,
            call_type TEXT,
            received_at TEXT,
            status TEXT DEFAULT '대기'
        )
    ''')

    # 9. 보내는 사람 기본 마스터 테이블 (어르신 택배 전용)
    c.execute('''
        CREATE TABLE IF NOT EXISTS delivery_users (
            user_id BIGSERIAL PRIMARY KEY,
            phone_number VARCHAR(15) UNIQUE NOT NULL,
            recent_sender_name VARCHAR(50),
            recent_zip_code VARCHAR(5),
            recent_road_address VARCHAR(255),
            recent_detailed_address VARCHAR(255),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 10. 실제 택배 주문 마스터 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS delivery_orders (
            order_id VARCHAR(50) PRIMARY KEY,
            user_id BIGINT REFERENCES delivery_users(user_id) ON DELETE SET NULL,
            sender_name VARCHAR(50) NOT NULL,
            sender_phone VARCHAR(15) NOT NULL,
            pickup_zip_code VARCHAR(5) NOT NULL,
            pickup_road_address VARCHAR(255) NOT NULL,
            pickup_detailed_address VARCHAR(255) NOT NULL,
            order_status VARCHAR(20) DEFAULT 'DRAFT',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            waybill_number VARCHAR(50),
            error_message TEXT,
            payload TEXT
        )
    ''')

    # 11. 받는 사람들 테이블 (1:N 배송 연계)
    c.execute('''
        CREATE TABLE IF NOT EXISTS order_recipients (
            recipient_id BIGSERIAL PRIMARY KEY,
            order_id VARCHAR(50) REFERENCES delivery_orders(order_id) ON DELETE CASCADE,
            receiver_name VARCHAR(50) NOT NULL,
            receiver_phone VARCHAR(15) NOT NULL,
            delivery_zip_code VARCHAR(5) NOT NULL,
            delivery_road_address VARCHAR(255) NOT NULL,
            delivery_detailed_address VARCHAR(255) NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS market_orders (
            order_id VARCHAR(50) PRIMARY KEY,          -- 고유 주문번호 (예: MK-20260604-001)
            customer_name VARCHAR(50) NOT NULL,        -- 고객 성함
            phone_number VARCHAR(20) NOT NULL,         -- 연락처
            zip_code VARCHAR(10) NOT NULL,             -- 우편번호 (다음 주소 API 필수 규격)
            base_address VARCHAR(255) NOT NULL,        -- 정제된 도로명/지번 주소
            detail_address VARCHAR(255) NOT NULL,      -- 어르신 수기 입력 상세 주소
            product_name VARCHAR(100) NOT NULL,        -- 판매 품목 (예: 태백 감자 1박스)
            total_amount INT NOT NULL,                 -- 최종 결제 금액
            current_status VARCHAR(30) DEFAULT 'PAID', -- 현재 상태 (PAID, PENDING, SHIPPING, COMPLETED, ERROR)
            waybill_no VARCHAR(50),                    -- 로젠택배 운송장 번호 (초기 null)
            sender_name VARCHAR(50) DEFAULT '탄탄제작소', -- 보내는 사람 성함
            sender_phone VARCHAR(20) DEFAULT '010-2384-7447', -- 보내는 사람 연락처
            sender_address VARCHAR(255) DEFAULT '강원특별자치도 태백시 태붐로 54', -- 보내는 사람 주소
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    try:
        c.execute("ALTER TABLE market_orders ADD COLUMN IF NOT EXISTS sender_name VARCHAR(50) DEFAULT '탄탄제작소'")
        c.execute("ALTER TABLE market_orders ADD COLUMN IF NOT EXISTS sender_phone VARCHAR(20) DEFAULT '010-2384-7447'")
        c.execute("ALTER TABLE market_orders ADD COLUMN IF NOT EXISTS sender_address VARCHAR(255) DEFAULT '강원특별자치도 태백시 태붐로 54'")
    except Exception as e:
        print(f"Alter Table Warning (sender fields): {e}")

    c.execute('''
        CREATE TABLE IF NOT EXISTS order_status_history (
            history_id SERIAL PRIMARY KEY,
            order_id VARCHAR(50) REFERENCES market_orders(order_id),
            changed_status VARCHAR(30) NOT NULL,
            reason TEXT,                               -- 변경 사유 또는 API 에러 로그 저장
            worker_identity VARCHAR(50) NOT NULL,      -- 변경 주체 (SYSTEM, ADMIN, DRIVER)
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 12. Unified Cost Logging, Activity, Wallet, and Settlements (Zero UI & Soft Delete)
    c.execute('''
        CREATE TABLE IF NOT EXISTS usage_costs_log (
            id SERIAL PRIMARY KEY,
            store_id VARCHAR(50) NOT NULL,
            service_type VARCHAR(30) NOT NULL,
            units_used INTEGER NOT NULL DEFAULT 0,
            unit_price INTEGER NOT NULL DEFAULT 0,
            calculated_cost INTEGER NOT NULL,
            request_metadata TEXT,
            status VARCHAR(15) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_usage_costs_store ON usage_costs_log(store_id, created_at) WHERE deleted_at IS NULL')

    c.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id SERIAL PRIMARY KEY,
            order_id VARCHAR(50) NOT NULL,
            store_id VARCHAR(50) NOT NULL,
            activity_type VARCHAR(30) NOT NULL,
            rider_id VARCHAR(50) DEFAULT NULL,
            delivery_fee INTEGER NOT NULL DEFAULT 0,
            rider_payout INTEGER NOT NULL DEFAULT 0,
            platform_fee INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_activity_order ON activity_logs(order_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_activity_rider ON activity_logs(rider_id, created_at) WHERE deleted_at IS NULL')

    c.execute('''
        CREATE TABLE IF NOT EXISTS wallet_transactions (
            id SERIAL PRIMARY KEY,
            store_id VARCHAR(50) NOT NULL,
            transaction_type VARCHAR(20) NOT NULL,
            amount INTEGER NOT NULL,
            balance_after INTEGER NOT NULL,
            reference_table VARCHAR(50) NOT NULL,
            reference_id BIGINT NOT NULL,
            memo TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_wallet_store_history ON wallet_transactions(store_id, created_at) WHERE deleted_at IS NULL')

    c.execute('''
        CREATE TABLE IF NOT EXISTS settlement_records (
            id SERIAL PRIMARY KEY,
            store_id VARCHAR(50) NOT NULL,
            settlement_date DATE NOT NULL,
            gross_sales INTEGER NOT NULL DEFAULT 0,
            total_fees INTEGER NOT NULL DEFAULT 0,
            net_payout INTEGER NOT NULL DEFAULT 0,
            status VARCHAR(15) NOT NULL,
            processed_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
        )
    ''')
    c.execute('CREATE UNIQUE INDEX IF NOT EXISTS uidx_settlement_store_date ON settlement_records(store_id, settlement_date) WHERE deleted_at IS NULL')

    c.execute('''
        CREATE TABLE IF NOT EXISTS ai_user_credits (
            user_id TEXT PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            updated_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS ai_free_usages (
            user_id TEXT PRIMARY KEY,
            question_count INTEGER DEFAULT 0,
            last_used_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS ai_usage_logs (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            intent TEXT,
            cost INTEGER,
            created_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS ai_travel_feedback (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            destination TEXT,
            rating INTEGER,
            review TEXT,
            reward_points INTEGER,
            created_at TEXT
        )
    ''')


    try:
        if not conn.autocommit:
            conn.commit()
    except Exception:
        pass
    conn.close()

def log_travel_feedback(user_id: str, destination: str, rating: int, review: str) -> bool:
    """사용자의 여행 피드백을 저장하고 50포인트를 환급(캐시백)합니다."""
    conn = get_connection()
    c = conn.cursor()
    reward = 50
    try:
        # 1. 피드백 저장
        c.execute('''
            INSERT INTO ai_travel_feedback (user_id, destination, rating, review, reward_points, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (user_id, destination, rating, review, reward, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        # 2. 포인트 환급 (기존 잔액이 없으면 생성)
        c.execute('SELECT balance FROM ai_user_credits WHERE user_id = %s FOR UPDATE', (user_id,))
        row = c.fetchone()
        if row:
            new_balance = row[0] + reward
            c.execute('UPDATE ai_user_credits SET balance = %s, updated_at = %s WHERE user_id = %s',
                      (new_balance, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
        else:
            c.execute('INSERT INTO ai_user_credits (user_id, balance, updated_at) VALUES (%s, %s, %s)',
                      (user_id, reward, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        # 3. 내역 로깅
        c.execute('''
            INSERT INTO ai_usage_logs (user_id, intent, cost, created_at)
            VALUES (%s, %s, %s, %s)
        ''', (user_id, 'travel_feedback_reward', -reward, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Feedback Log Error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def log_sms(store_id, phone, category, message, status, response=""):
    """
    SMS 발송 이력 저장
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO sms_logs (store_id, phone, category, message, status, response, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                  (store_id, phone, category, message, status, str(response), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except Exception as e:
        print(f"Log Error: {e}")
    finally:
        conn.close()

def get_sms_logs(store_id=None, limit=50):
    conn = get_connection()
    try:
        if store_id:
            query = "SELECT * FROM sms_logs WHERE store_id = %s ORDER BY id DESC LIMIT %s"
            return pd.read_sql_query(query, conn, params=(store_id, limit))
        else:
            query = "SELECT * FROM sms_logs ORDER BY id DESC LIMIT %s"
            return pd.read_sql_query(query, conn, params=(limit,))
    except:
        return pd.DataFrame()
    finally:
        conn.close()

# Initialize on module load
init_db()

# ==========================================
# AI Call Logs Methods
# ==========================================

def log_security_event(store_id, customer_phone, event_type, payload):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO security_logs (store_id, customer_phone, event_type, payload, created_at)
            VALUES (%s, %s, %s, %s, %s)
        ''', (store_id, customer_phone, event_type, payload, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    except Exception as e:
        print(f"Security Log Error: {e}")
        return False
    finally:
        conn.close()

def get_security_logs_summary(hours=24):
    conn = get_connection()
    try:
        # SQLite datetime with modifier
        query = f"SELECT store_id, event_type, count(*) as count FROM security_logs WHERE created_at >= datetime('now', 'localtime', '-{hours} hours') GROUP BY store_id, event_type"
        df = pd.read_sql_query(query, conn)
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def save_ai_call_log(store_id, customer_phone, customer_name, intent, summary, audio_url="", event_type=None, event_details=None):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO ai_call_logs (store_id, customer_phone, customer_name, intent, summary, audio_url, created_at, event_type, event_details)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (store_id, customer_phone, customer_name, intent, summary, audio_url, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), event_type, event_details))
        conn.commit()
        return True
    except Exception as e:
        print(f"AI Call Log Save Error: {e}")
        return False
    finally:
        conn.close()

def get_ai_call_logs(store_id, limit=50):
    conn = get_connection()
    try:
        query = "SELECT * FROM ai_call_logs WHERE store_id = %s ORDER BY id DESC LIMIT %s"
        return pd.read_sql_query(query, conn, params=(store_id, limit))
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def mark_ai_call_read(log_id, store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE ai_call_logs SET is_read = 1 WHERE id = %s AND store_id = %s", (log_id, store_id))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

# ... (Existing code) ...

# ==========================================
# Order & Analytics
# ==========================================

def save_order(data):
    conn = get_connection()
    c = conn.cursor()
    try:
        # Get Fee Rate
        store_id = data.get('store_id')
        amount = int(data.get('amount', 0))
        
        # Default rate 3.3% if not found
        c.execute("SELECT fee_rate FROM stores WHERE store_id = %s", (store_id,))
        row = c.fetchone()
        rate = row['fee_rate'] if row and row['fee_rate'] is not None else 0.033
        
        fee = int(amount * rate)
        net = amount - fee
        
        c.execute('''
            INSERT INTO orders (store_id, type, item_name, amount, fee_amount, net_amount, settlement_status, customer_phone, payment_method, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            store_id,
            data.get('type'),
            data.get('item_name'),
            amount,
            fee,
            net,
            'pending',
            data.get('customer_phone'),
            data.get('payment_method', 'CARD'),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Order Save Error: {e}")
        return False
    finally:
        conn.close()

def get_orders(store_id, days=30):
    conn = get_connection()
    try:
        # Simple date diff could be done in SQL or Python. SQL is faster.
        # SQLite 'now', '-30 days' syntax
        query = f"SELECT * FROM orders WHERE store_id = %s AND created_at >= date('now', '-{days} days')"
        df = pd.read_sql(query, conn, params=(store_id,))
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def get_all_orders_admin(days=30):
    conn = get_connection()
    try:
        query = f"SELECT * FROM orders WHERE created_at >= date('now', '-{days} days')"
        df = pd.read_sql(query, conn)
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def get_customer_stats(store_id, phone):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('''
            SELECT COUNT(*) as count, SUM(amount) as total 
            FROM orders 
            WHERE store_id = %s AND customer_phone = %s
        ''', (store_id, phone))
        row = c.fetchone()
        if row:
            return {"visit_count": row['count'], "total_spend": row['total'] or 0}
        return {"visit_count": 0, "total_spend": 0}
    except Exception:
        return {"visit_count": 0, "total_spend": 0}
    finally:
        conn.close()


# ... (Existing code) ...

# ==========================================
# Settings (KV Store)
# ==========================================

def save_setting(store_id, key, value):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO store_settings (store_id, key, value) ON CONFLICT (store_id, key) DO UPDATE SET value = EXCLUDED.value
            VALUES (%s, %s, %s)
        ''', (store_id, key, str(value)))
        conn.commit()
        return True
    except Exception as e:
        print(f"Setting Save Error: {e}")
        return False
    finally:
        conn.close()

def get_all_settings(store_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT key, value FROM store_settings WHERE store_id = %s", (store_id,))
        rows = c.fetchall()
        return {row['key']: row['value'] for row in rows}
    except Exception:
        return {}
    finally:
        conn.close()


# ... (Existing User Mgmt / Store Mgmt code preserved) ...

# ==========================================
# Product Management
# ==========================================

def save_product(data):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO products (store_id, name, price, description, image_path, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            data.get('store_id'),
            data.get('name'),
            data.get('price'),
            data.get('description'),
            data.get('image_path'),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Product Save Error: {e}")
        return False
    finally:
        conn.close()

def get_products(store_id):
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM products WHERE store_id = %s AND is_active = 1 ORDER BY sort_order ASC", conn, params=(store_id,))
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

# ==========================================
# Reservation Management
# ==========================================

def save_reservation(data):
    # ... (Keep existing implementation) ...
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO reservations (store_id, customer_name, contact, res_date, res_time, head_count, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('store_id'),
            data.get('customer_name'),
            data.get('contact'),
            data.get('res_date'),
            data.get('res_time'),
            data.get('head_count', 1),
            data.get('status', 'confirmed'),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Reservation Save Error: {e}")
        return False
    finally:
        conn.close()

def update_reservation_status(reservation_id, status):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE reservations SET status = %s WHERE id = %s", (status, reservation_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Reservation Update Error: {e}")
        return False
    finally:
        conn.close()

def get_reservations(store_id):
    # ... (Keep existing) ...
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM reservations WHERE store_id = %s ORDER BY res_date, res_time", conn, params=(store_id,))
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


# ==========================================
# User Management
# ==========================================

def get_user_home_address(user_id):
    """사용자의 자택 주소를 반환합니다."""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT home_address FROM users WHERE id = %s", (user_id,))
        row = c.fetchone()
        if row and row['home_address']:
            return row['home_address']
        return "자택 주소 미등록 (기본값: 서울특별시 강남구 테헤란로)"
    except Exception as e:
        print(f"Error get_user_home_address: {e}")
        return "서울특별시 강남구 테헤란로"
    finally:
        conn.close()

# ==== Users Table Operations ==========================================

def save_user(user_data):
    conn = get_connection()
    c = conn.cursor()
    try:
        # Migration: ensure home_address column exists
        try:
            c.execute("ALTER TABLE users ADD COLUMN home_address TEXT")
        except:
            pass
        # user_data expects keys: '아이디', '상호명', etc. mapping to DB columns
        c.execute('''
            INSERT INTO users (id, name, level, phone, joined_at) ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, level=EXCLUDED.level, phone=EXCLUDED.phone
            VALUES (%s, %s, %s, %s, %s)
        ''', (
            user_data.get('아이디'),
            user_data.get('상호명'),
            user_data.get('유저 등급'),
            user_data.get('연락처'),
            user_data.get('가입일시')
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"DB Error: {e}")
        return False
    finally:
        conn.close()

def update_store_auto_reply(store_id, msg, missed, end, refill_on=0, refill_amount=50000):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE stores 
            SET auto_reply_msg = %s, 
                auto_reply_missed = %s, 
                auto_reply_end = %s,
                auto_refill_on = %s,
                auto_refill_amount = %s
            WHERE store_id = %s
        ''', (msg, missed, end, refill_on, refill_amount, store_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Auto Reply Update Error: {e}")
        return False
    finally:
        conn.close()


def update_store_agreement(store_id, owner_name, marketing_agreed):
    """
    Update agreement status for a store (SQLite).
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        # Ensure column exists for legacy DBs
        try:
            c.execute("ALTER TABLE stores ADD COLUMN is_signed INTEGER DEFAULT 0")
        except:
            pass
        try:
            c.execute("ALTER TABLE stores ADD COLUMN signed_at TEXT")
        except:
            pass

        c.execute(
            "UPDATE stores SET is_signed = 1, owner_name = %s, signed_at = %s WHERE store_id = %s",
            (owner_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), store_id),
        )
        conn.commit()
    except Exception as e:
        print(f"Agreement Update Error: {e}")
        return False
    finally:
        conn.close()

    # Save marketing agreement as a setting if possible
    try:
        save_setting(store_id, "marketing_agreed", "True" if marketing_agreed else "False")
    except Exception as e:
        print(f"Marketing Agree Save Error: {e}")
    return True

def get_all_users():
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM users", conn)
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def get_user(user_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = c.fetchone()
        if row:
            return dict(row)
        return None
    except Exception:
        return None
    finally:
        conn.close()

def delete_user(user_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Delete Error: {e}")
        return False
    finally:
        conn.close()

# ==========================================
# Store Management
# ==========================================

def get_store(store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM stores WHERE store_id = %s", (store_id,))
        row = c.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()

def get_store_virtual_number(store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM virtual_numbers WHERE store_id = %s", (store_id,))
        row = c.fetchone()
        if row:
            return dict(row)
        return None
    except Exception as e:
        print(f"Virtual Number Fetch Error: {e}")
        return None
    finally:
        conn.close()

import random as _random
import string as _string

# ==========================================
# 추천인 코드 (Referral Code) 유틸리티
# ==========================================

def generate_unique_referral_code(prefix: str = "DNB") -> str:
    """
    DNBXK7A2 형식의 고유 추천인 코드 생성.
    prefix(DNB) + 대문자+숫자 5자리 = 총 8자리.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        chars = _string.ascii_uppercase + _string.digits
        for _ in range(10):
            suffix = ''.join(_random.choices(chars, k=5))
            code = prefix + suffix
            c.execute("SELECT 1 FROM stores WHERE my_referral_code = %s", (code,))
            if not c.fetchone():
                return code
        suffix = ''.join(_random.choices(chars, k=6))
        return prefix + suffix
    finally:
        conn.close()


def get_store_by_referral_code(code: str):
    """추천인 코드로 가게 정보 조회."""
    if not code:
        return None
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM stores WHERE my_referral_code = %s", (code.strip().upper(),))
        row = c.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"[get_store_by_referral_code Error] {e}")
        return None
    finally:
        conn.close()


def save_store(store_data):
    conn = get_connection()
    c = conn.cursor()
    try:
        # store_id is key
        store_id = store_data.get('store_id') or store_data.get('phone') # Fallback
        
        # 신규 가입 시 추천인 코드 자동 생성
        my_referral_code = store_data.get('my_referral_code', '')
        if not my_referral_code:
            c.execute("SELECT my_referral_code FROM stores WHERE store_id = %s", (store_id,))
            existing = c.fetchone()
            if existing and existing.get('my_referral_code'):
                my_referral_code = existing['my_referral_code']
            else:
                my_referral_code = generate_unique_referral_code()

        c.execute('''
            INSERT INTO stores (
                store_id, password, name, owner_name, phone, category,
                info, menu_text, printer_ip, table_count, seats_per_table,
                points, membership, is_signed, signed_at, role, user_role,
                created_at, my_referral_code, business_type
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (store_id) DO UPDATE SET
                password = EXCLUDED.password,
                name = EXCLUDED.name,
                owner_name = EXCLUDED.owner_name,
                phone = EXCLUDED.phone,
                category = EXCLUDED.category,
                info = EXCLUDED.info,
                menu_text = EXCLUDED.menu_text,
                printer_ip = EXCLUDED.printer_ip,
                table_count = EXCLUDED.table_count,
                seats_per_table = EXCLUDED.seats_per_table,
                points = EXCLUDED.points,
                membership = EXCLUDED.membership,
                is_signed = EXCLUDED.is_signed,
                signed_at = EXCLUDED.signed_at,
                role = EXCLUDED.role,
                user_role = EXCLUDED.user_role,
                my_referral_code = COALESCE(NULLIF(stores.my_referral_code, ''), EXCLUDED.my_referral_code),
                business_type = EXCLUDED.business_type
        ''', (
            store_id,
            store_data.get('password'),
            store_data.get('name'),
            store_data.get('owner_name'),
            store_data.get('phone'),
            store_data.get('category'),
            store_data.get('info'),
            store_data.get('menu_text'),
            store_data.get('printer_ip'),
            store_data.get('table_count', 0),
            store_data.get('seats_per_table', 0),
            store_data.get('points', 0),
            store_data.get('membership'),
            store_data.get('is_signed', 0),
            store_data.get('signed_at'),
            store_data.get('role'),
            store_data.get('user_role'),
            store_data.get('created_at', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            my_referral_code,
            store_data.get('business_type', 'hotel')
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Store Save Error: {e}")
        return False
    finally:
        conn.close()


def get_all_stores():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM stores ORDER BY created_at DESC")
        rows = c.fetchall()
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

# ==========================================
# Wallet Logic
# ==========================================

def log_wallet(store_id, change_type, amount, balance_after, memo):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO wallet_logs (store_id, change_type, amount, balance_after, memo, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (store_id, change_type, amount, balance_after, memo, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    finally:
        conn.close()

def request_topup(store_id, amount, depositor):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO wallet_topups (store_id, amount, depositor, status, requested_at)
            VALUES (%s, %s, %s, %s, %s)
        ''', (store_id, amount, depositor, "pending", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    finally:
        conn.close()


def get_wallet_logs(store_id=None, limit=200):
    conn = get_connection()
    try:
        if store_id:
            return pd.read_sql(
                "SELECT * FROM wallet_logs WHERE store_id = %s ORDER BY id DESC LIMIT %s",
                conn,
                params=(store_id, limit),
            )
        return pd.read_sql(
            "SELECT * FROM wallet_logs ORDER BY id DESC LIMIT %s",
            conn,
            params=(limit,),
        )
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def get_pending_topups():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM wallet_topups WHERE status = 'pending'")
        rows = c.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

# ==========================================
# Business Records
# ==========================================

def save_business_record(user_type, data):
    conn = get_connection()
    c = conn.cursor()
    try:
        if user_type == "일반사업자":
            c.execute('''
                INSERT INTO records_general (date_time, customer_name, contact, menu_info, head_count, amount, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                data.get('일시'), data.get('고객명'), data.get('연락처'), 
                data.get('메뉴/인원'), data.get('인원'), data.get('결제금액'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        elif user_type == "택배사업자":
             c.execute('''
                INSERT INTO records_delivery (date_time, sender_name, receiver_name, receiver_addr, item_type, fee, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                data.get('접수일시'), data.get('발송인명'), data.get('수령인명'),
                data.get('수령인 주소(AI추출)'), data.get('물품종류'), data.get('수수료'),
                data.get('상태', '접수완료'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        
        conn.commit()
        return True, "저장 성공"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

# ==========================================
# Table & Room Management (Using store_settings)
# ==========================================
def get_store_tables(store_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT value FROM store_settings WHERE store_id = %s AND key = 'tables'", (store_id,))
        row = c.fetchone()
        if row:
            return json.loads(row['value'])
        return []
    except Exception:
        return []
    finally:
        conn.close()

def save_store_tables(store_id, tables_data):
    # tables_data should be a list of dicts
    # We reuse the existing save_setting logic which handles connection
    import json
    json_str = json.dumps(tables_data, ensure_ascii=False)

# ==========================================
# Ledger (Bookkeeping) Management
# ==========================================
def create_ledger_table():
    conn = get_connection()
    if conn is None:
        print("[!] PostgreSQL Connection failed. Skipping ledger table creation.")
        return
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS ledger_records (
            id SERIAL PRIMARY KEY,
            store_id TEXT,
            date TEXT,
            type TEXT,
            category TEXT,
            amount INTEGER,
            memo TEXT,
            proof_path TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Auto-run migration
create_ledger_table()

def save_ledger_record(data):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO ledger_records (store_id, date, type, category, amount, memo, proof_path, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('store_id'),
            data.get('date'),
            data.get('type'),
            data.get('category'),
            data.get('amount'),
            data.get('memo'),
            data.get('proof_path'),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Ledger Save Error: {e}")
        return False
    finally:
        conn.close()

def get_ledger_records(store_id, month_str=None):
    # month_str: '2024-05'
    conn = get_connection()
    try:
        query = "SELECT * FROM ledger_records WHERE store_id = %s"
        params = [store_id]
        
        if month_str:
            query += " AND date LIKE ?"
            params.append(f"{month_str}%")
            
        query += " ORDER BY date DESC, id DESC"
        
        return pd.read_sql(query, conn, params=params)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def delete_ledger_record(record_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM ledger_records WHERE id = %s", (record_id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()




def request_topup(store_id, amount, depositor):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO wallet_topups (store_id, amount, depositor, status, requested_at)
            VALUES (%s, %s, %s, %s, %s)
        ''', (store_id, amount, depositor, "pending", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    finally:
        conn.close()


def get_wallet_logs(store_id=None, limit=200):
    conn = get_connection()
    try:
        if store_id:
            return pd.read_sql(
                "SELECT * FROM wallet_logs WHERE store_id = %s ORDER BY id DESC LIMIT %s",
                conn,
                params=(store_id, limit),
            )
        return pd.read_sql(
            "SELECT * FROM wallet_logs ORDER BY id DESC LIMIT %s",
            conn,
            params=(limit,),
        )
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def get_pending_topups():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM wallet_topups WHERE status = 'pending'")
        rows = c.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

# ==========================================
# Business Records
# ==========================================

def save_business_record(user_type, data):
    conn = get_connection()
    c = conn.cursor()
    try:
        if user_type == "일반사업자":
            c.execute('''
                INSERT INTO records_general (date_time, customer_name, contact, menu_info, head_count, amount, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                data.get('일시'), data.get('고객명'), data.get('연락처'), 
                data.get('메뉴/인원'), data.get('인원'), data.get('결제금액'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        elif user_type == "택배사업자":
             c.execute('''
                INSERT INTO records_delivery (date_time, sender_name, receiver_name, receiver_addr, item_type, fee, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                data.get('접수일시'), data.get('발송인명'), data.get('수령인명'),
                data.get('수령인 주소(AI추출)'), data.get('물품종류'), data.get('수수료'),
                data.get('상태', '접수완료'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        
        conn.commit()
        return True, "저장 성공"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

# ==========================================
# Table & Room Management (Using store_settings)
# ==========================================
def get_store_tables(store_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT value FROM store_settings WHERE store_id = %s AND key = 'tables'", (store_id,))
        row = c.fetchone()
        if row:
            return json.loads(row['value'])
        return []
    except Exception:
        return []
    finally:
        conn.close()

def save_store_tables(store_id, tables_data):
    # tables_data should be a list of dicts
    # We reuse the existing save_setting logic which handles connection
    import json
    json_str = json.dumps(tables_data, ensure_ascii=False)

# ==========================================
# Ledger (Bookkeeping) Management
# ==========================================
def create_ledger_table():
    conn = get_connection()
    if conn is None:
        print("[!] PostgreSQL Connection failed. Skipping ledger table creation.")
        return
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS ledger_records (
            id SERIAL PRIMARY KEY,
            store_id TEXT,
            date TEXT,
            type TEXT,
            category TEXT,
            amount INTEGER,
            memo TEXT,
            proof_path TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Auto-run migration
create_ledger_table()

def save_ledger_record(data):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO ledger_records (store_id, date, type, category, amount, memo, proof_path, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('store_id'),
            data.get('date'),
            data.get('type'),
            data.get('category'),
            data.get('amount'),
            data.get('memo'),
            data.get('proof_path'),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Ledger Save Error: {e}")
        return False
    finally:
        conn.close()

def get_ledger_records(store_id, month_str=None):
    # month_str: '2024-05'
    conn = get_connection()
    try:
        query = "SELECT * FROM ledger_records WHERE store_id = %s"
        params = [store_id]
        
        if month_str:
            query += " AND date LIKE ?"
            params.append(f"{month_str}%")
            
        query += " ORDER BY date DESC, id DESC"
        
        return pd.read_sql(query, conn, params=params)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def delete_ledger_record(record_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM ledger_records WHERE id = %s", (record_id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


# ==========================================
# Parcel Delivery Management
# ==========================================
def create_delivery_table():
    conn = get_connection()
    if conn is None:
        print("[!] PostgreSQL Connection failed. Skipping delivery table creation.")
        return
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS deliveries (
            id SERIAL PRIMARY KEY,
            store_id TEXT,
            sender_name TEXT,
            sender_phone TEXT,
            sender_addr TEXT,
            receiver_name TEXT,
            receiver_phone TEXT,
            receiver_addr TEXT,
            item_name TEXT,
            weight REAL,
            fare INTEGER,
            status TEXT,
            tracking_number TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

create_delivery_table()

def save_delivery(data):
    conn = get_connection()
    if conn is None:
        return False, "Database connection failed"
    try:
        c = conn.cursor()
        try:
            c.execute("ALTER TABLE deliveries ADD COLUMN payment_type TEXT DEFAULT 'prepaid'")
            conn.commit()
        except:
            conn.rollback()

        import random
        tn = data.get('tracking_code', f"TRK{datetime.now().strftime('%Y%m%d')}{random.randint(1000,9999)}")
        c.execute('''
            INSERT INTO deliveries (store_id, sender_name, sender_phone, sender_addr, 
                                    receiver_name, receiver_phone, receiver_addr, 
                                    item_name, weight, fare, status, tracking_number, created_at, payment_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('store_id'),
            data.get('sender_name'),
            data.get('sender_phone'),
            data.get('sender_addr'),
            data.get('receiver_name'),
            data.get('receiver_phone'),
            data.get('receiver_addr'),
            data.get('item_name') or data.get('item_type'),
            data.get('weight', 1),
            data.get('fare') or data.get('fee', 3000),
            data.get('status', '접수완료'),
            tn,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data.get('payment_type', 'prepaid')
        ))
        conn.commit()
        return True, tn
    except Exception as e:
        print(f"Delivery Save Error (Postgres): {e}")
        try:
            conn.rollback()
        except:
            pass
        return False, str(e)
    finally:
        conn.close()

def save_delivery_order(data):
    conn = get_connection()
    if conn is None:
        return False, "Database connection failed"
    try:
        c = conn.cursor()
        
        sender_phone = data.get('sender_phone')
        sender_name = data.get('sender_name')
        sender_postcode = data.get('sender_postcode') or data.get('pickup_zip_code') or ""
        sender_base_address = data.get('sender_base_address') or data.get('pickup_road_address') or ""
        sender_detail_address = data.get('sender_detail_address') or data.get('pickup_detailed_address') or ""
        
        # 1. Update or Insert User in delivery_users
        c.execute("SELECT user_id FROM delivery_users WHERE phone_number = %s", (sender_phone,))
        user_row = c.fetchone()
        
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if user_row:
            user_id = user_row[0]
            c.execute('''
                UPDATE delivery_users 
                SET recent_sender_name = %s, recent_zip_code = %s, recent_road_address = %s, recent_detailed_address = %s, updated_at = %s
                WHERE user_id = %s
            ''', (sender_name, sender_postcode, sender_base_address, sender_detail_address, now_str, user_id))
        else:
            c.execute('''
                INSERT INTO delivery_users (phone_number, recent_sender_name, recent_zip_code, recent_road_address, recent_detailed_address, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING user_id
            ''', (sender_phone, sender_name, sender_postcode, sender_base_address, sender_detail_address, now_str))
            user_id = c.fetchone()[0]
            
        # 2. Insert into delivery_orders
        order_id = data.get('order_id') or data.get('tracking_code') or f"COURIER-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        order_status = data.get('order_status') or data.get('status') or 'REQUESTED'
        payload = data.get('payload')
        c.execute('''
            INSERT INTO delivery_orders (order_id, user_id, sender_name, sender_phone, pickup_zip_code, pickup_road_address, pickup_detailed_address, order_status, created_at, payload)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (order_id, user_id, sender_name, sender_phone, sender_postcode, sender_base_address, sender_detail_address, order_status, now_str, payload))
        
        # 3. Insert into order_recipients
        recipients = data.get('recipients')
        if not recipients:
            # Single recipient fallback
            recipients = [{
                'receiver_name': data.get('receiver_name'),
                'receiver_phone': data.get('receiver_phone'),
                'postcode': data.get('postcode') or data.get('delivery_zip_code') or "",
                'address': data.get('address') or data.get('delivery_road_address') or "",
                'detail_address': data.get('detail_address') or data.get('delivery_detailed_address') or ""
            }]
            
        for rc in recipients:
            c.execute('''
                INSERT INTO order_recipients (order_id, receiver_name, receiver_phone, delivery_zip_code, delivery_road_address, delivery_detailed_address)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (order_id, rc.get('receiver_name'), rc.get('receiver_phone'), rc.get('postcode') or rc.get('delivery_zip_code') or "", rc.get('address') or rc.get('delivery_road_address') or "", rc.get('detail_address') or rc.get('delivery_detailed_address') or ""))
            
        conn.commit()
        return True, order_id
    except Exception as e:
        print(f"Delivery Order Save Error (Postgres): {e}")
        try:
            conn.rollback()
        except:
            pass
        return False, str(e)
    finally:
        conn.close()

def get_delivery_order(order_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM delivery_orders WHERE order_id = %s", (order_id,))
        row = c.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"Error fetching delivery order (Postgres): {e}")
        return None
    finally:
        conn.close()

def acquire_delivery_order_lock(order_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE delivery_orders
            SET order_status = 'PROCESSING'
            WHERE order_id = %s AND (order_status = 'REQUESTED' OR order_status = 'DRAFT' OR order_status = 'FAILED')
        ''', (order_id,))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        print(f"Error acquiring lock (Postgres): {e}")
        return False
    finally:
        conn.close()

def update_delivery_order_status(order_id, status, waybill_number=None, error_message=None):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE delivery_orders
            SET order_status = %s, waybill_number = %s, error_message = %s
            WHERE order_id = %s
        ''', (status, waybill_number, error_message, order_id))
        
        if waybill_number:
            c.execute('''
                UPDATE records_delivery
                SET tracking_code = %s, status = %s
                WHERE tracking_code = %s
            ''', (waybill_number, "접수완료", order_id))
            c.execute('''
                UPDATE deliveries
                SET tracking_number = %s, status = %s
                WHERE tracking_number = %s
            ''', (waybill_number, "접수완료", order_id))
        elif status == 'FAILED':
            c.execute('''
                UPDATE records_delivery
                SET status = %s
                WHERE tracking_code = %s
            ''', ("접수실패", order_id))
            c.execute('''
                UPDATE deliveries
                SET status = %s
                WHERE tracking_number = %s
            ''', ("접수실패", order_id))
        elif status == 'REQUESTED':
            c.execute('''
                UPDATE records_delivery
                SET status = %s
                WHERE tracking_code = %s
            ''', ("접수대기", order_id))
            c.execute('''
                UPDATE deliveries
                SET status = %s
                WHERE tracking_number = %s
            ''', ("접수대기", order_id))
            
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating delivery order status (Postgres): {e}")
        return False
    finally:
        conn.close()

def get_store_deliveries(store_id):
    conn = get_connection()
    try:
        return pd.read_sql("SELECT * FROM deliveries WHERE store_id = %s ORDER BY id DESC", conn, params=(store_id,))
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def get_today_deliveries(store_id):
    conn = get_connection()
    try:
        today_prefix = datetime.now().strftime("%Y-%m-%d") + "%"
        query = "SELECT * FROM deliveries WHERE store_id = %s AND created_at LIKE %s ORDER BY id DESC"
        return pd.read_sql(query, conn, params=(store_id, today_prefix))
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def update_delivery_status(delivery_id, store_id, status):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE deliveries SET status = %s WHERE id = %s AND store_id = %s", (status, delivery_id, store_id))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        print(f"Update Delivery Status Error: {e}")
        return False
    finally:
        conn.close()


# ==========================================
# 💰 Wallet / Virtual Number Utilities
# ==========================================

def get_wallet_balance(store_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT wallet_balance FROM stores WHERE store_id = %s", (store_id,))
    row = c.fetchone()
    conn.close()
    if row and row["wallet_balance"] is not None:
        return int(row["wallet_balance"])
    return 0


def update_wallet_balance(store_id, new_balance):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE stores SET wallet_balance = %s WHERE store_id = %s", (int(new_balance), store_id))
        conn.commit()
        return True
    except Exception as exc:
        print(f"Wallet Update Error: {exc}")
        return False
    finally:
        conn.close()


def get_store_id_by_virtual_number(virtual_number):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT store_id FROM virtual_numbers WHERE virtual_number = %s", (virtual_number,))
    row = c.fetchone()
    conn.close()
    return row["store_id"] if row else None


def save_virtual_number(virtual_number, store_id, label="", status="active"):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            """
            INSERT INTO virtual_numbers (virtual_number, store_id, label, status, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                virtual_number,
                store_id,
                label,
                status,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        return True
    except Exception as exc:
        print(f"Virtual Number Save Error: {exc}")
        return False
    finally:
        conn.close()


def get_all_virtual_numbers():
    conn = get_connection()
    try:
        return pd.read_sql(
            "SELECT * FROM virtual_numbers ORDER BY created_at DESC",
            conn,
        )
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


# ==========================================
# 🚚 Courier / Rider (Normalized Entities)
# ==========================================

def save_courier(data):
    conn = get_connection()
    c = conn.cursor()
    try:
        courier_id = data.get("courier_id")
        c.execute(
            """
            INSERT INTO couriers (courier_id, name, phone, company, vehicle_type, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                courier_id,
                data.get("name"),
                data.get("phone"),
                data.get("company"),
                data.get("vehicle_type"),
                data.get("status", "active"),
                data.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ),
        )
        conn.commit()
        return True
    except Exception as exc:
        print(f"Courier Save Error: {exc}")
        return False
    finally:
        conn.close()


def get_courier(courier_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM couriers WHERE courier_id = %s", (courier_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_couriers():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM couriers ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_rider(data):
    conn = get_connection()
    c = conn.cursor()
    try:
        rider_id = data.get("rider_id")
        c.execute(
            """
            INSERT INTO riders (rider_id, name, phone, area, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                rider_id,
                data.get("name"),
                data.get("phone"),
                data.get("area"),
                data.get("status", "active"),
                data.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ),
        )
        conn.commit()
        return True
    except Exception as exc:
        print(f"Rider Save Error: {exc}")
        return False
    finally:
        conn.close()


def get_rider(rider_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM riders WHERE rider_id = %s", (rider_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_riders():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM riders ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_order_by_id(order_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
        row = c.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def update_order_tracking(order_id, tracking_number):
    conn = get_connection()
    c = conn.cursor()
    try:
        # Try adding column if not present
        try:
            c.execute("ALTER TABLE orders ADD COLUMN tracking_code TEXT")
        except: pass
        
        c.execute("UPDATE orders SET tracking_code = %s WHERE id = %s", (str(tracking_number), order_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Tracking Update Error: {e}")
        return False
    finally:
        conn.close()

def update_order_payment_method(order_id, method):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE orders SET payment_method = %s WHERE id = %s", (method, order_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Payment Method Update Error: {e}")
        return False
    finally:
        conn.close()


def save_product(store_id, name, price, image_path):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO products (store_id, name, price, image_path, created_at, inventory)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (store_id, name, price, image_path, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 100)) # Default 100
        conn.commit()
        return True
    except Exception as e:
        print(f"Product Save Error: {e}")
        return False
    finally:
        conn.close()

def get_all_products():
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM products ORDER BY sort_order ASC")
        rows = c.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Product Fetch Error: {e}")
        return []
    finally:
        conn.close()

def init_expenses_db():
    conn = get_connection()
    if conn is None:
        return
    conn.autocommit = True
    c = conn.cursor()
    # Expenses Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            store_id TEXT,
            card_name TEXT,
            category TEXT,
            amount INTEGER,
            date TEXT,
            approval_no TEXT,
            created_at TEXT
        )
    ''')
    
    # Idempotency: Add approval_no column if not exists
    try:
        c.execute("ALTER TABLE expenses ADD COLUMN approval_no TEXT")
    except: pass
    
    # Idempotency: Unique Index
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_expenses_approval ON expenses(approval_no)")

    # MFA Token Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS card_auth_tokens (
            id SERIAL PRIMARY KEY,
            store_id TEXT,
            card_name TEXT,
            token TEXT,
            expires_at TEXT,
            proxy_ip TEXT,
            created_at TEXT
        )
    ''')
    
    try:
        if not conn.autocommit:
            conn.commit()
    except Exception:
        pass
    conn.close()

init_expenses_db()

def save_expense(store_id, card_name, category, amount, date, approval_no=None):
    # Check Lock
    if is_date_locked(store_id, date):
        print(f"Expense Save Blocked: Date {date} is locked.")
        return False

    conn = get_connection()
    c = conn.cursor()
    try:
        # Generate approval_no if missing (for mock data)
        if not approval_no:
            import hashlib
            raw = f"{store_id}{card_name}{category}{amount}{date}"
            approval_no = hashlib.md5(raw.encode()).hexdigest()[:10]

        c.execute('''
            INSERT INTO expenses (store_id, card_name, category, amount, date, approval_no, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (store_id, card_name, category, amount, date, approval_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        print(f"Skipping Duplicate Expense: {approval_no}")
        return True # Treat as success (Idempotency)
    except Exception as e:
        print(f"Expense Save Error: {e}")
        return False
    finally:
        conn.close()

# Ledger Lock Functions
def init_lock_table():
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            CREATE TABLE IF NOT EXISTS ledger_locks (
                store_id TEXT,
                locked_until TEXT,
                created_at TEXT,
                PRIMARY KEY (store_id)
            )
        ''') 
        conn.commit()
    except Exception as e:
        print(f"Lock Table Init Error: {e}")
    finally:
        conn.close()

def get_ledger_lock_date(store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        init_lock_table() # Ensure table exists
        c.execute("SELECT locked_until FROM ledger_locks WHERE store_id = %s", (store_id,))
        row = c.fetchone()
        if row:
            return row[0]
        return None
    except Exception:
        return None
    finally:
        conn.close()

def lock_ledger(store_id, date):
    # Lock data up to this date (Inclusive)
    conn = get_connection()
    c = conn.cursor()
    try:
        init_lock_table()
        # Only update if new date is later than existing lock
        current_lock = get_ledger_lock_date(store_id)
        if current_lock and current_lock >= date:
            return True # Already locked
            
        c.execute("INSERT INTO ledger_locks (store_id, locked_until, created_at) VALUES (%s, %s, %s)", 
                  (store_id, date, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    except Exception as e:
        print(f"Lock Error: {e}")
        return False
    finally:
        conn.close()

def is_date_locked(store_id, date):
    # date format: YYYY-MM-DD
    if not date: return False
    locked_until = get_ledger_lock_date(store_id)
    if not locked_until:
        return False
    return date <= locked_until

def save_order(store_id, product_id, product_name, price, quantity, buyer_name, buyer_phone, buyer_address):
    # Check Lock
    today = datetime.now().strftime("%Y-%m-%d")
    if is_date_locked(store_id, today):
        print(f"Order Save Blocked: Date {today} is locked.")
        return False
        
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO orders (store_id, product_id, product_name, price, quantity, buyer_name, buyer_phone, buyer_address, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (store_id, product_id, product_name, price, quantity, buyer_name, buyer_phone, buyer_address, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    except Exception as e:
        print(f"Order Save Error: {e}")
        return False
    finally:
        conn.close()

def get_tax_stats(store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        # 1. Total Revenue
        c.execute("SELECT SUM(price * quantity) as total_revenue FROM orders WHERE store_id = %s", (store_id,))
        row = c.fetchone()
        total_revenue = row['total_revenue'] if row and row['total_revenue'] else 0
        
        # 2. Expense Rate (33.47% as per user request example)
        expense_rate = 0.3347
        recognized_expenses = int(total_revenue * expense_rate)
        
        # 3. Tax Base
        # Basic Deduction: 1,500,000
        basic_deduction = 1500000
        tax_base = total_revenue - recognized_expenses - basic_deduction
        if tax_base < 0: tax_base = 0
        
        # 4. Tax (6%)
        predicted_tax = int(tax_base * 0.06)
        
        return {
            "total_revenue": total_revenue,
            "recognized_expenses": recognized_expenses,
            "predicted_tax": predicted_tax
        }
    finally:
        conn.close()

def get_product_detail(product_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM products WHERE id = %s", (product_id,))
        row = c.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()

def save_expense(store_id, card_name, category, amount, date, approval_no=None):
    conn = get_connection()
    c = conn.cursor()
    try:
        # Generate approval_no if missing (for mock data)
        if not approval_no:
            import hashlib
            raw = f"{store_id}{card_name}{category}{amount}{date}"
            approval_no = hashlib.md5(raw.encode()).hexdigest()[:10]

        c.execute('''
            INSERT INTO expenses (store_id, card_name, category, amount, date, approval_no, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (store_id, card_name, category, amount, date, approval_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        print(f"Skipping Duplicate Expense: {approval_no}")
        return True # Treat as success (Idempotency)
    except Exception as e:
        print(f"Expense Save Error: {e}")
        return False
    finally:
        conn.close()

def get_monthly_expenses(store_id, month=None):
    # month format: "YYYY-MM"
    if not month:
        month = datetime.now().strftime("%Y-%m")
        
    conn = get_connection()
    try:
        query = "SELECT * FROM expenses WHERE store_id = %s AND date LIKE %s"
        df = pd.read_sql(query, conn, params=(store_id, f"{month}%"))
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def get_integrated_ledger(store_id):
    conn = get_connection()
    try:
        # 1. Get Expenses (Purchase)
        expenses_query = """
            SELECT 
                date, 
                '매입' as type, 
                category, 
                card_name as client, 
                amount as total,
                '법인카드' as note
            FROM expenses 
            WHERE store_id = %s
        """
        
        # 2. Get Sales (Orders)
        orders_query = """
            SELECT 
                substr(created_at, 1, 10) as date, 
                '매출' as type, 
                '배송매출' as category, 
                buyer_name as client, 
                (price * quantity) as total,
                '카드결제' as note
            FROM orders 
            WHERE store_id = %s
        """
        
        df_expenses = pd.read_sql(expenses_query, conn, params=(store_id,))
        df_orders = pd.read_sql(orders_query, conn, params=(store_id,))
        
        # Merge
        df_all = pd.concat([df_expenses, df_orders], ignore_index=True)
        
        if df_all.empty:
            return []
            
        # Sort by Date
        df_all['date'] = pd.to_datetime(df_all['date'])
        df_all = df_all.sort_values(by='date')
        
        # Process Columns (Supply Value, VAT)
        results = []
        for idx, row in df_all.iterrows():
            total = int(row['total'])
            supply_value = int(total / 1.1)
            vat = total - supply_value
            
            results.append({
                "date": row['date'].strftime("%m-%d"),
                "type": row['type'],
                "category": row['category'],
                "client": row['client'],
                "supply_value": supply_value,
                "vat": vat,
                "total": total,
                "note": row['note']
            })
            
        return results

    except Exception as e:
        print(f"Ledger Error: {e}")
        return []
    finally:
        conn.close()

def get_today_stats(store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute("SELECT SUM(price * quantity) as revenue FROM orders WHERE store_id = %s AND created_at LIKE %s", (store_id, f"{today}%"))
        row = c.fetchone()
        revenue = row['revenue'] if row and row['revenue'] else 0
        
        margin = int(revenue * 0.1) # 10% Margin
        
        return {
            "revenue": revenue,
            "margin": margin
        }
    except Exception as e:
        print(f"Stats Error: {e}")
        return {"revenue": 0, "margin": 0}
    finally:
        conn.close()


def charge_wallet(store_id, amount, bonus, memo):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT wallet_balance FROM stores WHERE store_id = %s", (store_id,))
        row = c.fetchone()
        current = row['wallet_balance'] if row and row['wallet_balance'] else 0

        new_balance = current + amount + bonus

        c.execute("UPDATE stores SET wallet_balance = %s WHERE store_id = %s", (new_balance, store_id))
        c.execute('''
            INSERT INTO wallet_logs (store_id, change_type, amount, balance_after, memo, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (store_id, 'charge', amount + bonus, new_balance, memo, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        conn.commit()
        return new_balance
    except Exception as e:
        print(f"Charge Wallet Error: {e}")
        return None
    finally:
        conn.close()


def decrease_product_inventory(product_id, quantity):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT inventory FROM products WHERE id = %s", (product_id,))
        row = c.fetchone()
        if not row:
            return False, "상품을 찾을 수 없습니다."

        current = row['inventory'] if row['inventory'] else 0
        if current < quantity:
            return False, "재고가 부족합니다."

        c.execute("UPDATE products SET inventory = inventory - %s WHERE id = %s", (quantity, product_id))
        conn.commit()
        return True, "OK"
    except Exception as e:
        print(f"Inventory Error: {e}")
        return False, str(e)
    finally:
        conn.close()


def get_tax_report_data(store_id, start, end):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            SELECT COALESCE(SUM(price * quantity), 0) as total_sales
            FROM orders
            WHERE store_id = %s AND created_at >= %s AND created_at <= %s
        """, (store_id, start, end + " 23:59:59"))
        row = c.fetchone()
        total_sales = row['total_sales'] if row else 0

        total_vat = int(total_sales / 11)
        total_fee = int(total_sales * 0.033)
        net_margin = total_sales - total_vat - total_fee

        return {
            "total_sales": total_sales,
            "total_vat": total_vat,
            "total_fee": total_fee,
            "net_margin": net_margin
        }
    except Exception as e:
        print(f"Tax Report Error: {e}")
        return None
    finally:
        conn.close()


def update_order_status(order_id, status):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE orders SET settlement_status = %s WHERE id = %s", (status, order_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Order Status Update Error: {e}")
        return False
    finally:
        conn.close()


# ==========================================
# 🧠 Customer Memory (CRM)
# ==========================================

def get_customer(customer_id, store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM customers WHERE customer_id = %s AND store_id = %s", (customer_id, store_id))
        row = c.fetchone()
        return dict(row) if row else None
    except Exception:
        return None
    finally:
        conn.close()


def get_customer_by_phone(phone):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM customers WHERE phone = %s ORDER BY last_visit DESC LIMIT 1", (phone,))
        row = c.fetchone()
        return dict(row) if row else None
    except Exception:
        return None
    finally:
        conn.close()


def save_customer(customer_data):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO customers (customer_id, store_id, name, phone, address, preferences, notes, total_orders, last_visit, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            customer_data.get('customer_id'),
            customer_data.get('store_id'),
            customer_data.get('name'),
            customer_data.get('phone'),
            customer_data.get('address'),
            customer_data.get('preferences'),
            customer_data.get('notes'),
            customer_data.get('total_orders', 0),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Customer Save Error: {e}")
        return False
    finally:
        conn.close()


def update_customer_field(customer_id, field, value, store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        allowed_fields = {'name', 'phone', 'address', 'preferences', 'notes'}
        if field not in allowed_fields:
            return False
        c.execute(f"UPDATE customers SET {field} = %s, last_visit = %s WHERE customer_id = %s AND store_id = %s",
                  (value, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), customer_id, store_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Customer Update Error: {e}")
        return False
    finally:
        conn.close()


def increment_customer_order(customer_id, store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            UPDATE customers SET total_orders = total_orders + 1, last_visit = %s
            WHERE customer_id = %s AND store_id = %s
        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), customer_id, store_id))
        conn.commit()
        c.execute("SELECT total_orders FROM customers WHERE customer_id = %s AND store_id = %s", (customer_id, store_id))
        row = c.fetchone()
        return row['total_orders'] if row else 0
    except Exception as e:
        print(f"Customer Order Increment Error: {e}")
        return 0
    finally:
        conn.close()



# ==========================================
# 💰 AI Billing & Quota Management
# ==========================================

def check_ai_limit(store_id):
    """
    Check if the store can use AI services (Daily Limit & Points).
    Returns: (is_allowed, message)
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT daily_token_limit, current_usage, last_usage_date, points, tier FROM stores WHERE store_id = %s", (store_id,))
        row = c.fetchone()
        
        if not row:
            return False, "Store not found"
            
        limit = row['daily_token_limit'] or 10000
        usage = row['current_usage'] or 0
        last_date = row['last_usage_date']
        points = row['points'] or 0
        
        # 1. Daily Reset Check
        today = datetime.now().strftime("%Y-%m-%d")
        if last_date != today:
            # Reset usage for new day
            c.execute("UPDATE stores SET current_usage = 0, last_usage_date = %s WHERE store_id = %s", (today, store_id))
            conn.commit()
            usage = 0
            
        # 2. Check Limit
        if usage >= limit:
            return False, f"Daily limit exceeded ({usage}/{limit})"
            
        # 3. Check Points (Pay-as-you-go)
        # Assuming 10 points minimum required to start a turn
        if points < 10:
             return False, "Insufficient points"
             
        return True, "OK"
        
    except Exception as e:
        print(f"Billing Check Error: {e}")
        # Fail safe: allow if DB error? Or block? Block is safer for billing.
        return False, f"System Error: {e}"
    finally:
        conn.close()

def log_ai_usage(store_id, input_tokens, output_tokens):
    """
    Log AI usage and deduct points.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        pass # Transaction start implicitly
        
        total_tokens = input_tokens + output_tokens
        
        # Cost calculation (Simple model: 1 token = 1 point? Or 1000 tokens = 100 points?)
        # Let's say 1 turn costs 10 points fixed + 1 point per 100 tokens
        # Or just: total_tokens
        
        # Implementation Plan said "10 points per call" as example
        cost = 10 + (total_tokens // 100)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. Log Usage
        c.execute('''
            INSERT INTO ai_usage_logs (store_id, tokens_input, tokens_output, cost, timestamp)
            VALUES (%s, %s, %s, %s, %s)
        ''', (store_id, input_tokens, output_tokens, cost, timestamp))
        
        # 2. Update Store (Deduct Points, Increment Usage)
        c.execute('''
            UPDATE stores 
            SET points = points - %s, 
                current_usage = current_usage + %s
            WHERE store_id = %s
        ''', (cost, total_tokens, store_id))
        
        conn.commit()
        return True, cost
        
    except Exception as e:
        print(f"Logging Error: {e}")
        return False, 0
    finally:
        conn.close()



# ==========================================
# 🚀 AI Caching (Zero-Cost)
# ==========================================

def get_cached_response(store_id, user_message):
    """
    Check if a similar question exists in cache.
    For MVP: Exact match or simple keyword logic.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        # Normalize message (remove spaces, lowercase) for better hit rate
        # core_msg = user_message.replace(" ", "").strip()
        
        c.execute('''
            SELECT answer, hits FROM cached_responses 
            WHERE store_id = %s AND question = %s
        ''', (store_id, user_message))
        
        row = c.fetchone()
        if row:
            # Update hits
            c.execute("UPDATE cached_responses SET hits = hits + 1, last_used = %s WHERE store_id = %s AND question = %s", 
                      (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), store_id, user_message))
            conn.commit()
            return row['answer']
            
        return None
    except Exception as e:
        print(f"Cache Get Error: {e}")
        return None
    finally:
        conn.close()

def save_cached_response(store_id, question, answer):
    """
    Save a Q&A pair to cache.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO cached_responses (store_id, question, answer, last_used, created_at)
            VALUES (%s, %s, %s, %s, %s)
        ''', (
            store_id, 
            question, 
            answer, 
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Cache Save Error: {e}")
        return False
    finally:
        conn.close()


# ==========================================
# 💰 Wallet & Usage (SQLite Stub)
# ==========================================

def get_wallet_details(store_id):
    """
    Get wallet balance and recent logs for a store.
    """
    store = get_store(store_id)
    if not store:
        return {
            "current_points": 0,
            "wallet_logs": [],
            "ai_usage_today": {"tokens": 0, "cost": 0},
            "sms_usage_today": {"count": 0, "cost": 0}
        }
        
    return {
        "current_points": store.get('points', 0),
        "wallet_logs": [], # SQLite version doesn't track detailed logs yet
        "ai_usage_today": {"tokens": 0, "cost": 0},
        "sms_usage_today": {"count": 0, "cost": 0}
    }

def get_daily_usage_stats(store_id):
    return {
        "ai": {"tokens": 0, "cost": 0},
        "sms": {"count": 0, "cost": 0}
    }



def confirm_payment(store_id, amount, order_id, payment_key):
    """
    Simulate payment confirmation for SQLite (Local Dev).
    """
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # 1. Update Points
        c.execute("UPDATE stores SET points = COALESCE(points, 0) + %s WHERE store_id = %s", (amount, store_id))
        
        # 2. Log
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute('''
            INSERT INTO wallet_logs (store_id, change_type, amount, balance_after, memo, created_at)
            VALUES (%s, %s, %s, (SELECT points FROM stores WHERE store_id = %s), %s, %s)
        ''', (store_id, 'CHARGE', amount, store_id, '포인트 충전', now))
        
        print(f"[SQLite] Payment Confirmed: Store {store_id} +{amount}P")
        
        conn.commit()
        return True
    except Exception as e:
        print(f"[!] SQLite Payment Error: {e}")
        return False

# ==========================================
# 🎯 CRM & Target Marketing (SQLite)
# ==========================================

def get_crm_customers(store_id, filter_type="all"):
    """
    Get customers list based on filter for Target Marketing.
    """
    conn = get_connection()
    try:
        # SQLite Query construction
        query = "SELECT * FROM customers WHERE store_id = %s"
        params = [store_id]
        
        if filter_type == "recent":
            # Visit within last 30 days
            query += " AND last_visit >= CURRENT_DATE - INTERVAL '30 days'"
            
        elif filter_type == "regular":
            # 3 or more orders
            query += " AND total_orders >= 3"
            
        elif filter_type == "vip":
            # 10 or more orders
            query += " AND total_orders >= 10"
            
        query += " ORDER BY last_visit DESC LIMIT 100"
        
        # Helper to convert sqlite3.Row to dict
        c = conn.cursor()
        c.execute(query, params)
        rows = c.fetchall()
        return [dict(row) for row in rows]
        
    except Exception as e:
        print(f"CRM Get Error: {e}")
        return []
    finally:
        conn.close()

def deduct_points_for_sms(store_id, total_cost, customer_count):
    """
    Atomic Point Deduction for Batch SMS (SQLite).
    """
    conn = get_connection()
    try:
        c = conn.cursor()
        
        # 1. Check Balance
        c.execute("SELECT points FROM stores WHERE store_id = %s", (store_id,))
        row = c.fetchone()
        current_points = row['points'] if row and row['points'] else 0
        
        if current_points < total_cost:
            return False, "잔액이 부족합니다.", None
        
        # 2. Deduct
        new_balance = current_points - total_cost
        c.execute("UPDATE stores SET points = %s WHERE store_id = %s", (new_balance, store_id))
        
        # 3. Log
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        memo = f"단체 문자 발송 ({customer_count}명)"
        
        c.execute('''
            INSERT INTO wallet_logs (store_id, change_type, amount, balance_after, memo, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (store_id, 'USE', -total_cost, new_balance, memo, now))
        
        # Threshold Alert Check
        try:
            if new_balance < 1000:
                c.execute("SELECT phone, name FROM stores WHERE store_id = %s", (store_id,))
                row = c.fetchone()
                if row:
                    print(f"[Threshold Alert] Store {store_id} points: {new_balance}")
                    import sms_manager
                    phone = row['phone'] or store_id
                    name = row['name'] or "가맹점"
                    clean_phone = phone.replace("-", "").replace(" ", "").strip()
                    msg = f"[동네비서] {name} 사장님, 현재 보유 토큰 잔액이 {new_balance}개로 부족합니다. 원활한 서비스 이용을 위해 즉시 충전해주세요."
                    sms_manager.send_sms(clean_phone, msg, store_id=store_id)
        except Exception as alert_err:
            print(f"Failed to send threshold alert: {alert_err}")

        conn.commit()
        return True, "성공", "TX_" + datetime.now().strftime("%Y%m%d%H%M%S")
        
    except Exception as e:
        print(f"[!] Point Deduction Error: {e}")
        return False, f"시스템 오류: {e}", None
    finally:
        conn.close()

def refund_points(store_id, amount, reason):
    """
    Refund points (e.g., for failed SMS).
    """
    conn = get_connection()
    try:
        if amount <= 0: return True
        c = conn.cursor()
        
        # 1. Refund
        c.execute("UPDATE stores SET points = points + %s WHERE store_id = %s", (amount, store_id))
        
        # 2. Log
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        c.execute('''
            INSERT INTO wallet_logs (store_id, change_type, amount, balance_after, memo, created_at)
            VALUES (%s, %s, %s, (SELECT points FROM stores WHERE store_id = %s), %s, %s)
        ''', (store_id, 'REFUND', amount, store_id, reason, now))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"[!] Refund Error: {e}")
        return False
    finally:
        conn.close()

def deduct_fixed_cost(store_id, amount, reason):
    """
    Deduct fixed amount (SQLite).
    """
    conn = get_connection()
    try:
        c = conn.cursor()
        
        # 1. Check Balance
        c.execute("SELECT points FROM stores WHERE store_id = %s", (store_id,))
        row = c.fetchone()
        current = row['points'] if row and row['points'] else 0
        
        if current < amount:
            return False
        
        # 2. Deduct
        c.execute("UPDATE stores SET points = points - %s WHERE store_id = %s", (amount, store_id))
        
        # 3. Log
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute('''
            INSERT INTO wallet_logs (store_id, change_type, amount, balance_after, memo, created_at)
            VALUES (%s, %s, %s, (SELECT points FROM stores WHERE store_id = %s), %s, %s)
        ''', (store_id, 'USE', -amount, store_id, reason, now))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"[!] Deduct Error: {e}")
        return False
    finally:
        conn.close()

def get_daily_usage_stats(store_id):
    """
    Get daily usage statistics (SQLite Dummy).
    """
    return {
        "ai": {"tokens": 0, "cost": 0},
        "sms": {"count": 0, "cost": 0}
    }

def get_wallet_details(store_id):
    """
    Get wallet balance and logs (SQLite).
    """
    details = {
        "current_points": 0,
        "wallet_logs": [],
        "ai_usage_today": {"tokens": 0, "cost": 0},
        "sms_usage_today": {"count": 0, "cost": 0}
    }
    conn = get_connection()
    try:
        c = conn.cursor()
        
        # 1. Current Points
        c.execute("SELECT points FROM stores WHERE store_id = %s", (store_id,))
        row = c.fetchone()
        details["current_points"] = row['points'] if row and row['points'] else 0
        
        # 2. Recent Wallet Logs
        c.execute('''
            SELECT change_type as type, amount, created_at, memo 
            FROM wallet_logs 
            WHERE store_id = %s 
            ORDER BY id DESC LIMIT 20
        ''', (store_id,))
        rows = c.fetchall()
        details["wallet_logs"] = [dict(row) for row in rows]
        
    except Exception as e:
        print(f"Wallet Details Error: {e}")
    finally:
        conn.close()
        
    # Get Usage Stats
    usage = get_daily_usage_stats(store_id)
    details["ai_usage_today"] = usage.get("ai")
    details["sms_usage_today"] = usage.get("sms")
    return details

def create_db_backup():
    """
    Create a full system backup (JSON Dump of all tables).
    Returns path to backup file.
    """
    try:
        import pandas as pd
        import json
        import os
        from datetime import datetime

        conn = get_connection()
        # List of tables to backup
        tables = ["users", "stores", "couriers", "riders", "wallet_logs", "sms_logs", "ai_usage_logs", "customers"]
        
        backup_data = {}
        
        try:
            for table in tables:
                try:
                    df = pd.read_sql(f"SELECT * FROM {table}", conn)
                    # simplistic approach: use records orientation
                    backup_data[table] = df.to_dict(orient="records")
                except Exception as e:
                    print(f"[Backup] Skipping table {table}: {e}")
        finally:
            conn.close()
                    
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_full_{timestamp}.json"
        
        # Use a localized path or /tmp
        backup_dir = os.path.join(os.getcwd(), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        filepath = os.path.join(backup_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=4, default=str)
            
        return filepath
    except Exception as e:
        print(f"[!] Backup Error: {e}")
        return None

def check_db_integrity():
    """
    Check Database Integrity.
    """
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("PRAGMA integrity_check")
        result = c.fetchone()
        if result and result[0] == "ok":
            return "OK (Verified)"
        return f"Corrupt: {result[0]}" if result else "Unknown"
    except Exception as e:
        return f"Error: {e}"
    finally:
        conn.close()

def save_user(store_id, password, name, phone):
    """
    Save user to 'users' table (Legacy/Admin Management)
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        # Check if exists
        c.execute("SELECT id FROM users WHERE id = %s", (store_id,))
        if c.fetchone():
            c.execute("UPDATE users SET password=%s, name=%s, phone=%s WHERE id=%s", (password, name, phone, store_id))
        else:
            c.execute("INSERT INTO users (id, password, name, phone, joined_at) VALUES (%s, %s, %s, %s, %s)", 
                      (store_id, password, name, phone, datetime.now().isoformat()))
        conn.commit()
        return True
    except Exception as e:
        print(f"[!] SQLite save_user Error: {e}")
        return False
    finally:
        conn.close()

def get_all_users():
    """
    Get all users (for Admin Dashboard)
    """
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users")
        rows = c.fetchall()
        
        # Convert to list of dicts
        users = []
        for row in rows:
            users.append(dict(row))
            
        conn.close()
        return users
    except Exception as e:
        print(f"[!] SQLite get_all_users Error: {e}")
        return []

def get_wallet_topups(store_id):
    """
    Get all topup requests (sqlite)
    """
    try:
        conn = get_connection()
        query = "SELECT * FROM wallet_topups WHERE store_id = %s ORDER BY requested_at DESC"
        df = pd.read_sql_query(query, conn, params=(store_id,))
        conn.close()
        return df
    except Exception as e:
        print(f"[!] SQLite get_wallet_topups Error: {e}")
        return pd.DataFrame()

def update_store_role(store_id, role):
    """
    Update store role (RBAC)
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        # 1. Check store exists
        c.execute("SELECT store_id FROM stores WHERE store_id = %s", (store_id,))
        if not c.fetchone():
            return False

        # 2. Ensure columns exist
        try:
            c.execute("ALTER TABLE stores ADD COLUMN user_role TEXT")
        except:
            pass
        try:
            c.execute("ALTER TABLE stores ADD COLUMN role TEXT")
        except:
            pass

        # 3. Update both columns for compatibility
        c.execute("UPDATE stores SET user_role = %s, role = %s WHERE store_id = %s", (role, role, store_id))

        conn.commit()
        return True
    except Exception as e:
        print(f"[!] SQLite update_store_role Error: {e}")
        try:
            c.execute("ALTER TABLE stores ADD COLUMN user_role TEXT")
        except:
            pass
        try:
            c.execute("ALTER TABLE stores ADD COLUMN role TEXT")
        except:
            pass
        try:
            c.execute("UPDATE stores SET user_role = %s, role = %s WHERE store_id = %s", (role, role, store_id))
            conn.commit()
            return True
        except:
            return False
    finally:
        conn.close()

def save_courier_request(data):
    """
    Save Citizen Courier Request
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO courier_requests (
                citizen_id, sender_name, sender_phone, sender_addr,
                receiver_name, receiver_phone, receiver_addr,
                item_type, weight, status, payment_method, tracking_code, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('citizen_id'), data.get('sender_name'), data.get('sender_phone'), data.get('sender_addr'),
            data.get('receiver_name'), data.get('receiver_phone'), data.get('receiver_addr'),
            data.get('item_type'), data.get('weight'), data.get('status', 'pending'),
            data.get('payment_method'), data.get('tracking_code'), datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        return c.lastrowid
    except Exception as e:
        print(f"[!] SQLite save_courier_request Error: {e}")
        return False
    finally:
        conn.close()

def get_courier_requests(citizen_id=None):
    """
    Get Courier Requests (Filter by citizen_id if provided)
    """
    conn = get_connection()
    try:
        if citizen_id:
            df = pd.read_sql("SELECT * FROM courier_requests WHERE citizen_id = %s ORDER BY created_at DESC", conn, params=(citizen_id,))
        else:
            df = pd.read_sql("SELECT * FROM courier_requests ORDER BY created_at DESC", conn)
        return df
    except Exception as e:
        print(f"[!] SQLite get_courier_requests Error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def deduct_points(store_id, amount):
    """
    Deduct Points from Store
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        # Check current points first to avoid negative? 
        # For now, let's just subtract. verification happened in app.
        c.execute("UPDATE stores SET points = points - %s WHERE store_id = %s", (amount, store_id))
        
        # Threshold Alert Check
        try:
            c.execute("SELECT points, phone, name FROM stores WHERE store_id = %s", (store_id,))
            row = c.fetchone()
            if row:
                pts = row['points'] if row['points'] is not None else 0
                if pts < 1000:
                    print(f"[Threshold Alert] Store {store_id} points: {pts}")
                    import sms_manager
                    phone = row['phone'] or store_id
                    name = row['name'] or "가맹점"
                    clean_phone = phone.replace("-", "").replace(" ", "").strip()
                    msg = f"[동네비서] {name} 사장님, 현재 보유 토큰 잔액이 {pts}개로 부족합니다. 원활한 서비스 이용을 위해 즉시 충전해주세요."
                    sms_manager.send_sms(clean_phone, msg, store_id=store_id)
        except Exception as alert_err:
            print(f"Failed to send threshold alert: {alert_err}")

        conn.commit()
        return True
    except Exception as e:
        print(f"[!] SQLite deduct_points Error: {e}")
        return False
    finally:
        conn.close()

def update_courier_payment_success(tracking_code, method):
    """
    Update Status after Payment Success
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        # Update status from 'payment_pending' to 'pending'
        c.execute("UPDATE courier_requests SET status = 'pending', payment_method = %s WHERE tracking_code = %s", (method, tracking_code))
        conn.commit()
        return True
    except Exception as e:
        print(f"[!] SQLite update_courier_payment_success Error: {e}")
        return False
    finally:
        conn.close()

def check_and_complete_referral_reward(store_id, fee_amount):
    """
    고객의 누적결제액이 일정 조건(예: 10,000원 이상)을 돌파하면 기사님께 리워드 지급
    first_tx_completed 컬럼을 누적 결제액 척도 및 지급 완료 플래그(-1)로 사용
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT referrer_id, first_tx_completed, subscription_tier FROM stores WHERE store_id = %s", (store_id,))
        store = c.fetchone()
        
        if not store:
            return False
            
        referrer_id = store['referrer_id']
        current_amount = store['first_tx_completed']
        tier = store['subscription_tier']
        
        if current_amount == -1 or not referrer_id:
            return False
            
        # 첫 번째 픽업 예약(택배 접수) 시 누적 금액 무관하게 기사님께 리워드 즉시 지급
        reward_amount = 30000 if tier == 'vip' else 15000
        
        c.execute('''
            INSERT INTO rewards (driver_id, store_id, amount, status, created_at)
            VALUES (%s, %s, %s, 'completed', CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Seoul')
        ''', (referrer_id, store_id, reward_amount))
        
        # 기사님(추천인) 지갑에 리워드 포인트 즉시 충전
        c.execute("UPDATE stores SET points = COALESCE(points, 0) + %s WHERE store_id = %s", (reward_amount, referrer_id))
        
        # 사장님 상태 반영 (-1은 발송 및 리워드 지급 완료 상태)
        c.execute("UPDATE stores SET first_tx_completed = -1 WHERE store_id = %s", (store_id,))
        conn.commit()
        
        return {"driver_id": referrer_id, "reward": reward_amount}
            
    except Exception as e:
        print(f"Reward error: {e}")
        return False
    finally:
        conn.close()

# --- SQLAlchemy Async Database Connection ---
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from dotenv import load_dotenv

load_dotenv()

# 1. 환경 변수 안전하게 로드 (실패 시 즉시 에러를 발생시켜 프로세스 중단)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL 환경 변수가 설정되지 않았습니다.")

# 만약 DATABASE_URL이 postgresql:// 로 시작하면 postgresql+asyncpg:// 로 치환
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# 2. 정석적인 비동기 엔진 생성 및 커넥션 풀 옵션 통제
async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # 프로덕션에서는 SQL 로그를 꺼서 오버헤드 방지
    
    # [핵심 설정] 자가 치유 및 풀 고갈 방지 변수 제어
    pool_pre_ping=True,     # 쿼리 실행 직전 연결 유효성 검사 (끊어졌으면 자동 재연결)
    pool_recycle=3600,      # 1시간마다 연결을 강제로 갱신하여 유휴 타임아웃 방지
    pool_size=10,           # 기본으로 유지할 물리적 연결 수
    max_overflow=20,        # 트래픽 폭주 시 최대 추가 허용 연결 수
    pool_timeout=30,        # 풀이 가득 찼을 때 대기할 최대 시간(초)
)

# 3. 세션 팩토리 생성 (개별 트랜잭션을 생성하는 도구)
async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False, # 커밋 후 객체 속성이 만료되는 것을 방지
    autoflush=False,
)

# 4. FastAPI 종속성 주입(Dependency Injection)을 위한 세션 생명주기 관리자
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback() # 에러 발생 시 안전하게 롤백
            raise
        finally:
            await session.close()    # [더 중요] 어떤 상황이든 커넥션 풀에 반납

def log_usage_cost(store_id, service_type, units_used, unit_price, calculated_cost, request_metadata=None, memo=None):
    """
    Log usage cost to usage_costs_log and wallet_transactions, and deduct points (PostgreSQL).
    All timestamps align to Asia/Seoul timezone.
    """
    conn = get_connection()
    if not conn:
        return False, 0
    c = conn.cursor()
    try:
        # 1. Deduct points from store
        c.execute("UPDATE stores SET points = points - %s WHERE store_id = %s", (calculated_cost, store_id))
        
        # 2. Get current balance
        c.execute("SELECT points, phone, name FROM stores WHERE store_id = %s", (store_id,))
        row = c.fetchone()
        points_after = row['points'] if row and row['points'] is not None else 0
        phone = row['phone'] if row and row['phone'] else store_id
        name = row['name'] if row and row['name'] else "가맹점"
        
        # 3. Log to usage_costs_log
        from datetime import datetime, timedelta, timezone
        kst = timezone(timedelta(hours=9))
        now_kst_str = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        
        metadata_str = str(request_metadata) if request_metadata else None
        
        c.execute('''
            INSERT INTO usage_costs_log (store_id, service_type, units_used, unit_price, calculated_cost, request_metadata, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        ''', (store_id, service_type, units_used, unit_price, calculated_cost, metadata_str, 'SUCCESS', now_kst_str))
        
        usage_log_id = c.fetchone()['id']
        
        # 4. Log to wallet_transactions
        memo = memo or f"{service_type} 사용 요금"
        c.execute('''
            INSERT INTO wallet_transactions (store_id, transaction_type, amount, balance_after, reference_table, reference_id, memo, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (store_id, 'USE', -calculated_cost, points_after, 'usage_costs_log', usage_log_id, memo, now_kst_str))
        
        # Threshold Alert check (1,000 points)
        if points_after < 1000:
            try:
                print(f"[Threshold Alert] Store {store_id} points: {points_after}")
                import sms_manager
                clean_phone = phone.replace("-", "").replace(" ", "").strip()
                msg = f"[동네비서] {name} 사장님, 현재 보유 토큰 잔액이 {points_after}개로 부족합니다. 원활한 서비스 이용을 위해 즉시 충전해주세요."
                sms_manager.send_sms(clean_phone, msg, store_id=store_id)
            except Exception as alert_err:
                print(f"Failed to send threshold alert: {alert_err}")
                
        conn.commit()
        return True, points_after
    except Exception as e:
        print(f"[!] log_usage_cost Error: {e}")
        return False, 0
    finally:
        conn.close()


# ==========================================
# AI Manager - Auth & Billing Functions
# ==========================================

def setup_ai_member(user_id, initial_balance=0):
    conn = get_connection()
    c = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        c.execute('''
            INSERT INTO ai_user_credits (user_id, balance, updated_at) 
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
        ''', (user_id, initial_balance, now_str))
        conn.commit()
    except Exception as e:
        print(f"Error setup_ai_member: {e}")
    finally:
        conn.close()

def check_ai_member(user_id):
    """Returns True if user is a registered AI premium member."""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT 1 FROM ai_user_credits WHERE user_id = %s", (user_id,))
        return bool(c.fetchone())
    except Exception as e:
        print(f"Error check_ai_member: {e}")
        return False
    finally:
        conn.close()

def check_and_increment_free_usage(user_id, max_count=3):
    """
    Simple Mode: Checks free usage count and increments if within limit.
    Returns (allowed, current_count).
    """
    conn = get_connection()
    c = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        c.execute("BEGIN;")
        c.execute("SELECT question_count FROM ai_free_usages WHERE user_id = %s FOR UPDATE", (user_id,))
        row = c.fetchone()
        
        if row is None:
            # First time use
            c.execute("INSERT INTO ai_free_usages (user_id, question_count, last_used_at) VALUES (%s, 1, %s)", (user_id, now_str))
            conn.commit()
            return True, 1
            
        current_count = row['question_count']
        if current_count >= max_count:
            c.execute("ROLLBACK;")
            return False, current_count
            
        new_count = current_count + 1
        c.execute("UPDATE ai_free_usages SET question_count = %s, last_used_at = %s WHERE user_id = %s", (new_count, now_str, user_id))
        conn.commit()
        return True, new_count
    except Exception as e:
        c.execute("ROLLBACK;")
        print(f"Error check_and_increment_free_usage: {e}")
        return False, 0
    finally:
        conn.close()

def deduct_credit_atomically(user_id, amount=10):
    """
    Premium Mode: Deducts credits using Row Lock (FOR UPDATE) for concurrency safety.
    Returns (success, message).
    """
    conn = get_connection()
    c = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        c.execute("BEGIN;")
        c.execute("SELECT balance FROM ai_user_credits WHERE user_id = %s FOR UPDATE", (user_id,))
        row = c.fetchone()
        
        if row is None:
            c.execute("ROLLBACK;")
            return False, "회원 정보가 없습니다."
            
        balance = row['balance']
        if balance < amount:
            c.execute("ROLLBACK;")
            return False, f"적립금이 부족합니다. (현재: {balance}, 필요: {amount})"
            
        new_balance = balance - amount
        c.execute("UPDATE ai_user_credits SET balance = %s, updated_at = %s WHERE user_id = %s", (new_balance, now_str, user_id))
        conn.commit()
        return True, f"차감 완료 (잔액: {new_balance})"
    except Exception as e:
        c.execute("ROLLBACK;")
        print(f"Error deduct_credit_atomically: {e}")
        return False, "시스템 오류로 차감에 실패했습니다."
    finally:
        conn.close()

def refund_credit(user_id, amount=10):
    """Refunds credits upon AI failure."""
    conn = get_connection()
    c = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        c.execute("BEGIN;")
        c.execute("SELECT balance FROM ai_user_credits WHERE user_id = %s FOR UPDATE", (user_id,))
        row = c.fetchone()
        if row:
            new_balance = row['balance'] + amount
            c.execute("UPDATE ai_user_credits SET balance = %s, updated_at = %s WHERE user_id = %s", (new_balance, now_str, user_id))
        conn.commit()
    except Exception as e:
        c.execute("ROLLBACK;")
        print(f"Error refund_credit: {e}")
    finally:
        conn.close()


def log_ai_usage_analytics(user_id, intent, cost):
    """Logs the usage of AI for analytics and OS data platform."""
    conn = get_connection()
    c = conn.cursor()
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        c.execute('''
            INSERT INTO ai_usage_logs (user_id, intent, cost, created_at)
            VALUES (%s, %s, %s, %s)
        ''', (user_id, intent, cost, now_str))
        conn.commit()
    except Exception as e:
        print(f"Error log_ai_usage_analytics: {e}")
    finally:
        conn.close()


# ==========================================
# 🏨 Room Reservation Module Helpers (PostgreSQL)
# ==========================================

def check_room_availability(store_id, room_id, check_in, check_out, exclude_reservation_id=None):
    import time
    conn = get_connection()
    c = conn.cursor()
    try:
        now_epoch = int(time.time())
        query = """
            SELECT id FROM reservations 
            WHERE store_id = %s 
              AND room_id = %s 
              AND (status = 'confirmed' OR (status = 'pending' AND expiry_time > %s))
              AND (check_in < %s AND check_out > %s)
        """
        params = [store_id, room_id, now_epoch, check_out, check_in]
        if exclude_reservation_id:
            query += " AND id != %s"
            params.append(exclude_reservation_id)
            
        c.execute(query, params)
        row = c.fetchone()
        return row is None  # True if available
    except Exception as e:
        print(f"[check_room_availability] Error: {e}")
        return False
    finally:
        conn.close()

def hold_room_reservation(store_id, room_id, check_in, check_out, guest_info, hold_duration_seconds=600):
    import time
    import hashlib
    
    # Generate stable bigint key for pg_advisory_xact_lock
    key_str = f"{store_id}:{room_id}"
    hash_bytes = hashlib.sha256(key_str.encode('utf-8')).digest()
    lock_id = int.from_bytes(hash_bytes[:8], byteorder='big', signed=True)
    
    conn = get_connection()
    c = conn.cursor()
    try:
        # Start transaction
        c.execute("BEGIN;")
        
        # Acquire advisory lock for this room during transaction
        c.execute("SELECT pg_advisory_xact_lock(%s)", (lock_id,))
        
        # Now check availability safely inside lock
        now_epoch = int(time.time())
        query = """
            SELECT id FROM reservations 
            WHERE store_id = %s 
              AND room_id = %s 
              AND (status = 'confirmed' OR (status = 'pending' AND expiry_time > %s))
              AND (check_in < %s AND check_out > %s)
        """
        c.execute(query, [store_id, room_id, now_epoch, check_out, check_in])
        row = c.fetchone()
        if row is not None:
            # Already booked, rollback and return None
            c.execute("ROLLBACK;")
            return None
            
        # Hold slot
        expiry_time = now_epoch + hold_duration_seconds
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        guest_name = ""
        guest_phone = ""
        if isinstance(guest_info, dict):
            guest_name = guest_info.get("name", "")
            guest_phone = guest_info.get("phone", "")
            guest_info_str = json.dumps(guest_info, ensure_ascii=False)
        else:
            guest_info_str = str(guest_info)
            guest_name = guest_info_str
            
        c.execute("""
            INSERT INTO reservations (
                store_id, customer_name, contact, status, created_at,
                guest_info, room_id, check_in, check_out, expiry_time
            ) VALUES (%s, %s, %s, 'pending', %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (store_id, guest_name, guest_phone, created_at, guest_info_str, room_id, check_in, check_out, expiry_time))
        
        inserted_row = c.fetchone()
        new_id = inserted_row[0] if inserted_row else None
        
        c.execute("COMMIT;")
        return new_id
    except Exception as e:
        try:
            c.execute("ROLLBACK;")
        except Exception:
            pass
        print(f"[hold_room_reservation] Error: {e}")
        return None
    finally:
        conn.close()

def confirm_room_reservation(reservation_id, store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            UPDATE reservations 
            SET status = 'confirmed' 
            WHERE id = %s AND store_id = %s AND status IN ('pending', 'confirmed')
        """, (reservation_id, store_id))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        print(f"[confirm_room_reservation] Error: {e}")
        return False
    finally:
        conn.close()

def cleanup_expired_holds():
    import time
    conn = get_connection()
    c = conn.cursor()
    try:
        now_epoch = int(time.time())
        c.execute("""
            UPDATE reservations 
            SET status = 'failed' 
            WHERE status = 'pending' AND expiry_time <= %s
        """, (now_epoch,))
        conn.commit()
        return c.rowcount
    except Exception as e:
        print(f"[cleanup_expired_holds] Error: {e}")
        return 0
    finally:
        conn.close()

def get_room_reservation(reservation_id, store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM reservations WHERE id = %s AND store_id = %s", (reservation_id, store_id))
        row = c.fetchone()
        if row:
            return dict(row)
        return None
    except Exception as e:
        print(f"[get_room_reservation] Error: {e}")
        return None
    finally:
        conn.close()

