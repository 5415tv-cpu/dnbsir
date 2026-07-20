import sqlite3
import threading
import os

_sqlite_lock = threading.Lock()
from datetime import datetime
import json
import pandas as pd

DB_FILE = "database.db"

def get_connection():
    """Create a thread-safe connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

get_db_session = get_connection  # 👈 14번째 빈 줄에, 왼쪽 끝에 딱 붙여서 추가합니다.

def init_db():
    """Initialize the database tables."""
    conn = get_connection()

   
    conn = get_connection()
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
            plan_status TEXT
        )
    ''')
    
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

    # Migration for stores table business_type
    try:
        c.execute("ALTER TABLE stores ADD COLUMN business_type TEXT DEFAULT 'hotel'")
    except Exception:
        pass


    # 2-0. Driver Rewards
    c.execute('''
        CREATE TABLE IF NOT EXISTS rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    # Migration for existing databases
    for col, col_type in [("guest_info", "TEXT"), ("room_id", "TEXT"), ("check_in", "TEXT"), ("check_out", "TEXT"), ("expiry_time", "INTEGER")]:
        try:
            c.execute(f"ALTER TABLE reservations ADD COLUMN {col} {col_type}")
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    except: pass
        
    try:
        c.execute('''
            CREATE TABLE IF NOT EXISTS payment_transactions (
                order_id TEXT PRIMARY KEY,
                tid TEXT NOT NULL,
                payment_method TEXT DEFAULT 'KAKAOPAY',
                status TEXT DEFAULT 'READY',
                created_at TEXT
            )
        ''')
    except Exception as e:
        print(f"Error creating payment_transactions table: {e}")
    conn.commit()
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

    # Product Inventory
    try:
        c.execute("ALTER TABLE products ADD COLUMN inventory INTEGER DEFAULT 100")
    except: pass

    # Customers (CRM / Memory)
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT,
            store_id TEXT,
            name TEXT,
            phone TEXT,
            address TEXT,
            preferences TEXT,
            notes TEXT,
            tags TEXT DEFAULT '',
            total_orders INTEGER DEFAULT 0,
            last_visit TEXT,
            created_at TEXT,
            UNIQUE(customer_id, store_id)
        )
    ''')
    try:
        c.execute("ALTER TABLE customers ADD COLUMN tags TEXT DEFAULT ''")
    except: pass

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
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            customer_phone TEXT,
            event_type TEXT,
            payload TEXT,
            created_at TEXT
        )
    ''')

    # 6. Communication Logs (App-Centric)
    c.execute('''
        CREATE TABLE IF NOT EXISTS call_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_phone TEXT,
            my_number TEXT,
            call_type TEXT,
            status TEXT,
            received_at TEXT
        )
    ''')

    # 7. SMS 수신거부 블랙리스트 (KISA 방통위 규정 준수)
    c.execute('''
        CREATE TABLE IF NOT EXISTS sms_blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_hash TEXT UNIQUE NOT NULL,   -- SHA-256 해시 (원본 미보관)
            store_id TEXT,                     -- 특정 매장 opt-out, NULL=전체 적용
            reason TEXT DEFAULT '080수신거부', -- 등록 사유
            registered_at TEXT NOT NULL
        )
    ''')

    # 8. 광고문자 발송 설정 (관리자 페이지 동적 변경용)
    c.execute('''
        CREATE TABLE IF NOT EXISTS ad_config (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    ''')

    # 9. 보내는 사람 기본 마스터 테이블 (어르신 택배 전용)
    c.execute('''
        CREATE TABLE IF NOT EXISTS delivery_users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT UNIQUE NOT NULL,
            recent_sender_name TEXT,
            recent_zip_code TEXT,
            recent_road_address TEXT,
            recent_detailed_address TEXT,
            updated_at TEXT
        )
    ''')

    # 10. 실제 택배 주문 마스터 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS delivery_orders (
            order_id TEXT PRIMARY KEY,
            user_id INTEGER,
            sender_name TEXT NOT NULL,
            sender_phone TEXT NOT NULL,
            pickup_zip_code TEXT NOT NULL,
            pickup_road_address TEXT NOT NULL,
            pickup_detailed_address TEXT NOT NULL,
            order_status TEXT DEFAULT 'DRAFT',
            created_at TEXT,
            waybill_number TEXT,
            error_message TEXT,
            payload TEXT,
            FOREIGN KEY(user_id) REFERENCES delivery_users(user_id)
        )
    ''')

    # 11. 받는 사람들 테이블 (1:N 배송 연계)
    c.execute('''
        CREATE TABLE IF NOT EXISTS order_recipients (
            recipient_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            receiver_name TEXT NOT NULL,
            receiver_phone TEXT NOT NULL,
            delivery_zip_code TEXT NOT NULL,
            delivery_road_address TEXT NOT NULL,
            delivery_detailed_address TEXT NOT NULL,
            FOREIGN KEY(order_id) REFERENCES delivery_orders(order_id) ON DELETE CASCADE
        )
    ''')

    # 12. Unified Cost Logging, Activity, Wallet, and Settlements (Zero UI & Soft Delete)
    c.execute('''
        CREATE TABLE IF NOT EXISTS usage_costs_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT NOT NULL,
            service_type TEXT NOT NULL,
            units_used INTEGER NOT NULL DEFAULT 0,
            unit_price INTEGER NOT NULL DEFAULT 0,
            calculated_cost INTEGER NOT NULL,
            request_metadata TEXT,
            status TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            deleted_at TEXT DEFAULT NULL
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_usage_costs_store ON usage_costs_log(store_id, created_at) WHERE deleted_at IS NULL')

    c.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            store_id TEXT NOT NULL,
            activity_type TEXT NOT NULL,
            rider_id TEXT DEFAULT NULL,
            delivery_fee INTEGER NOT NULL DEFAULT 0,
            rider_payout INTEGER NOT NULL DEFAULT 0,
            platform_fee INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            deleted_at TEXT DEFAULT NULL
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_activity_order ON activity_logs(order_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_activity_rider ON activity_logs(rider_id, created_at) WHERE deleted_at IS NULL')

    c.execute('''
        CREATE TABLE IF NOT EXISTS wallet_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            balance_after INTEGER NOT NULL,
            reference_table TEXT NOT NULL,
            reference_id INTEGER NOT NULL,
            memo TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            deleted_at TEXT DEFAULT NULL
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_wallet_store_history ON wallet_transactions(store_id, created_at) WHERE deleted_at IS NULL')

    try:
        c.execute("ALTER TABLE customers ADD COLUMN tags TEXT DEFAULT ''")
    except: pass

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
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            customer_phone TEXT,
            event_type TEXT,
            payload TEXT,
            created_at TEXT
        )
    ''')

    # 6. Communication Logs (App-Centric)
    c.execute('''
        CREATE TABLE IF NOT EXISTS call_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_phone TEXT,
            my_number TEXT,
            call_type TEXT,
            status TEXT,
            received_at TEXT
        )
    ''')

    # 7. SMS 수신거부 블랙리스트 (KISA 방통위 규정 준수)
    c.execute('''
        CREATE TABLE IF NOT EXISTS sms_blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_hash TEXT UNIQUE NOT NULL,   -- SHA-256 해시 (원본 미보관)
            store_id TEXT,                     -- 특정 매장 opt-out, NULL=전체 적용
            reason TEXT DEFAULT '080수신거부', -- 등록 사유
            registered_at TEXT NOT NULL
        )
    ''')

    # 8. 광고문자 발송 설정 (관리자 페이지 동적 변경용)
    c.execute('''
        CREATE TABLE IF NOT EXISTS ad_config (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    ''')

    # 9. 보내는 사람 기본 마스터 테이블 (어르신 택배 전용)
    c.execute('''
        CREATE TABLE IF NOT EXISTS delivery_users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT UNIQUE NOT NULL,
            recent_sender_name TEXT,
            recent_zip_code TEXT,
            recent_road_address TEXT,
            recent_detailed_address TEXT,
            updated_at TEXT
        )
    ''')

    # 10. 실제 택배 주문 마스터 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS delivery_orders (
            order_id TEXT PRIMARY KEY,
            user_id INTEGER,
            sender_name TEXT NOT NULL,
            sender_phone TEXT NOT NULL,
            pickup_zip_code TEXT NOT NULL,
            pickup_road_address TEXT NOT NULL,
            pickup_detailed_address TEXT NOT NULL,
            order_status TEXT DEFAULT 'DRAFT',
            created_at TEXT,
            waybill_number TEXT,
            error_message TEXT,
            payload TEXT,
            FOREIGN KEY(user_id) REFERENCES delivery_users(user_id)
        )
    ''')

    # 11. 받는 사람들 테이블 (1:N 배송 연계)
    c.execute('''
        CREATE TABLE IF NOT EXISTS order_recipients (
            recipient_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            receiver_name TEXT NOT NULL,
            receiver_phone TEXT NOT NULL,
            delivery_zip_code TEXT NOT NULL,
            delivery_road_address TEXT NOT NULL,
            delivery_detailed_address TEXT NOT NULL,
            FOREIGN KEY(order_id) REFERENCES delivery_orders(order_id) ON DELETE CASCADE
        )
    ''')

    # 12. Unified Cost Logging, Activity, Wallet, and Settlements (Zero UI & Soft Delete)
    c.execute('''
        CREATE TABLE IF NOT EXISTS usage_costs_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT NOT NULL,
            service_type TEXT NOT NULL,
            units_used INTEGER NOT NULL DEFAULT 0,
            unit_price INTEGER NOT NULL DEFAULT 0,
            calculated_cost INTEGER NOT NULL,
            request_metadata TEXT,
            status TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            deleted_at TEXT DEFAULT NULL
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_usage_costs_store ON usage_costs_log(store_id, created_at) WHERE deleted_at IS NULL')

    c.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            store_id TEXT NOT NULL,
            activity_type TEXT NOT NULL,
            rider_id TEXT DEFAULT NULL,
            delivery_fee INTEGER NOT NULL DEFAULT 0,
            rider_payout INTEGER NOT NULL DEFAULT 0,
            platform_fee INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            deleted_at TEXT DEFAULT NULL
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_activity_order ON activity_logs(order_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_activity_rider ON activity_logs(rider_id, created_at) WHERE deleted_at IS NULL')

    c.execute('''
        CREATE TABLE IF NOT EXISTS wallet_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            balance_after INTEGER NOT NULL,
            reference_table TEXT NOT NULL,
            reference_id INTEGER NOT NULL,
            memo TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            deleted_at TEXT DEFAULT NULL
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_wallet_store_history ON wallet_transactions(store_id, created_at) WHERE deleted_at IS NULL')

    c.execute('''
        CREATE TABLE IF NOT EXISTS settlement_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT NOT NULL,
            settlement_date TEXT NOT NULL,
            gross_sales INTEGER NOT NULL DEFAULT 0,
            total_fees INTEGER NOT NULL DEFAULT 0,
            net_payout INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL,
            processed_at TEXT DEFAULT NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            deleted_at TEXT DEFAULT NULL
        )
    ''')
    c.execute('CREATE UNIQUE INDEX IF NOT EXISTS uidx_settlement_store_date ON settlement_records(store_id, settlement_date) WHERE deleted_at IS NULL')

    # ★ stores.url_slug — 콜백 링크용 가게명 슬러그 (전화번호 노출 방지)
    try:
        c.execute("ALTER TABLE stores ADD COLUMN url_slug TEXT DEFAULT ''")
    except Exception:
        pass  # 이미 존재하면 무시

    # ★ stores.my_referral_code — DNBXK7A2 형식 고유 추천인 코드
    try:
        c.execute("ALTER TABLE stores ADD COLUMN my_referral_code TEXT DEFAULT ''")
    except Exception:
        pass
    try:
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS uidx_stores_referral_code ON stores(my_referral_code) WHERE my_referral_code != ''")
    except Exception:
        pass

    # ★ callback_funnel — 콜백 SMS 퍼널 추적 (발송→클릭→가입→구매)
    c.execute('''
        CREATE TABLE IF NOT EXISTS callback_funnel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_phone_masked TEXT,
            store_id TEXT,
            sms_sent_at TEXT,
            link_clicked_at TEXT,
            registered_at TEXT,
            purchased_at TEXT,
            source_ip TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_funnel_store ON callback_funnel(store_id, link_clicked_at)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_funnel_phone ON callback_funnel(customer_phone_masked)')

    # ★ callback_templates — 업종별 콜백 SMS 템플릿
    c.execute('''
        CREATE TABLE IF NOT EXISTS callback_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT UNIQUE NOT NULL,
            display_name TEXT,
            message_template TEXT NOT NULL,
            redirect_path TEXT NOT NULL DEFAULT '/market',
            is_active INTEGER DEFAULT 1,
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    ''')
    _tpls = [
        ('택배', '택배/물류', '[{store_name}] 전화 감사합니다.\n택배 접수를 바로 해드립니다 ▶ {link}', '/delivery/request'),
        ('식당', '식당/분식', '[{store_name}] 전화 주셔서 감사합니다.\n메뉴 확인 및 주문 ▶ {link}', '/market?focus={slug}'),
        ('카페', '카페/음료', '[{store_name}] 전화 감사합니다.\n음료 미리 주문하고 편하게 픽업하세요 ▶ {link}', '/market?focus={slug}'),
        ('미용', '미용/네일', '[{store_name}] 전화 주셔서 감사합니다.\n예약 문의는 링크에서 편하게 해주세요 ▶ {link}', '/market?focus={slug}'),
        ('병원', '병원/약국', '[{store_name}] 전화 주셔서 감사합니다.\n진료 예약을 링크에서 남겨주세요 ▶ {link}', '/market?focus={slug}'),
        ('마트', '소매/마트', '[{store_name}] 전화 감사합니다.\n상품 확인 및 주문 ▶ {link}', '/market?focus={slug}'),
        ('기타', '기타/일반', '[{store_name}] 전화 주셔서 감사합니다.\n아래 링크에서 바로 문의하실 수 있습니다 ▶ {link}', '/market?focus={slug}'),
    ]
    for _c2, _d, _m, _r in _tpls:
        c.execute('INSERT OR IGNORE INTO callback_templates (category, display_name, message_template, redirect_path) VALUES (?,?,?,?)', (_c2, _d, _m, _r))

    conn.commit()
    conn.close()


# ==========================================
# SMS 수신거부 블랙리스트 (KISA 방통위 규정)
# ==========================================
import hashlib as _hashlib

def _hash_phone(phone: str) -> str:
    """전화번호를 SHA-256 해시로 변환 (원본 번호 미보관 원칙)"""
    clean = phone.replace('-', '').replace(' ', '').strip()
    return _hashlib.sha256(clean.encode('utf-8')).hexdigest()


def add_to_blacklist(phone: str, store_id: str = None, reason: str = '080수신거부') -> bool:
    """
    수신거부 블랙리스트에 번호 등록.
    동일 해시가 이미 있으면 IGNORE(중복 방지).
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        phone_hash = _hash_phone(phone)
        c.execute('''
            INSERT OR IGNORE INTO sms_blacklist (phone_hash, store_id, reason, registered_at)
            VALUES (?, ?, ?, ?)
        ''', (phone_hash, store_id, reason, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return c.rowcount > 0  # True = 신규 등록, False = 이미 존재
    except Exception as e:
        print(f"[Blacklist Add Error] {e}")
        return False
    finally:
        conn.close()


def is_blacklisted(phone: str, store_id: str = None) -> bool:
    """
    발송 전 블랙리스트 확인.
    store_id 지정 시: 해당 매장 OR 전체(NULL) 블랙리스트 모두 체크.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        phone_hash = _hash_phone(phone)
        if store_id:
            c.execute(
                "SELECT 1 FROM sms_blacklist WHERE phone_hash = ? AND (store_id = ? OR store_id IS NULL) LIMIT 1",
                (phone_hash, store_id)
            )
        else:
            c.execute(
                "SELECT 1 FROM sms_blacklist WHERE phone_hash = ? LIMIT 1",
                (phone_hash,)
            )
        return c.fetchone() is not None
    except Exception as e:
        print(f"[Blacklist Check Error] {e}")
        return False  # 오류 시 안전하게 False (발송 허용 방향)
    finally:
        conn.close()


def remove_from_blacklist(phone: str, store_id: str = None) -> bool:
    """블랙리스트에서 번호 제거 (관리자 수동 해제용)"""
    conn = get_connection()
    c = conn.cursor()
    try:
        phone_hash = _hash_phone(phone)
        if store_id:
            c.execute(
                "DELETE FROM sms_blacklist WHERE phone_hash = ? AND store_id = ?",
                (phone_hash, store_id)
            )
        else:
            c.execute("DELETE FROM sms_blacklist WHERE phone_hash = ?", (phone_hash,))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        print(f"[Blacklist Remove Error] {e}")
        return False
    finally:
        conn.close()


def get_blacklist_count(store_id: str = None) -> int:
    """블랙리스트 등록 건수 조회"""
    conn = get_connection()
    c = conn.cursor()
    try:
        if store_id:
            c.execute(
                "SELECT COUNT(*) FROM sms_blacklist WHERE store_id = ? OR store_id IS NULL",
                (store_id,)
            )
        else:
            c.execute("SELECT COUNT(*) FROM sms_blacklist")
        row = c.fetchone()
        return row[0] if row else 0
    except Exception:
        return 0
    finally:
        conn.close()


# ==========================================
# 광고문자 설정 KV 스토어 (ad_config)
# ==========================================

def get_ad_config() -> dict:
    """광고문자 발송 설정 전체 조회 (DB 우선, 환경변수 폴백)"""
    import os
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT key, value FROM ad_config")
        rows = c.fetchall()
        cfg = {row['key']: row['value'] for row in rows}
    except Exception:
        cfg = {}
    finally:
        conn.close()

    return {
        'store_name':    cfg.get('ad_store_name')    or os.environ.get('AD_STORE_NAME', '탄탄제작소'),
        'biz_no':        cfg.get('ad_biz_no')         or os.environ.get('AD_BIZ_NO', ''),
        'store_phone':   cfg.get('ad_store_phone')   or os.environ.get('AD_STORE_PHONE', ''),
        'opt_out_number':cfg.get('ad_opt_out_number')or os.environ.get('AD_OPT_OUT_NUMBER', '080-000-0000'),
    }


def save_ad_config(store_name: str = None, biz_no: str = None,
                   store_phone: str = None, opt_out_number: str = None) -> bool:
    """광고문자 설정 저장 (None 값은 업데이트 제외)"""
    conn = get_connection()
    c = conn.cursor()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updates = [
            ('ad_store_name', store_name),
            ('ad_biz_no', biz_no),
            ('ad_store_phone', store_phone),
            ('ad_opt_out_number', opt_out_number),
        ]
        for key, val in updates:
            if val is not None:
                c.execute(
                    "INSERT OR REPLACE INTO ad_config (key, value, updated_at) VALUES (?, ?, ?)",
                    (key, val, now)
                )
        conn.commit()
        return True
    except Exception as e:
        print(f"[AdConfig Save Error] {e}")
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
        c.execute("INSERT INTO sms_logs (store_id, phone, category, message, status, response, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
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
            query = "SELECT * FROM sms_logs WHERE store_id = ? ORDER BY id DESC LIMIT ?"
            return pd.read_sql_query(query, conn, params=(store_id, limit))
        else:
            query = "SELECT * FROM sms_logs ORDER BY id DESC LIMIT ?"
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
            VALUES (?, ?, ?, ?, ?)
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        query = "SELECT * FROM ai_call_logs WHERE store_id = ? ORDER BY id DESC LIMIT ?"
        return pd.read_sql_query(query, conn, params=(store_id, limit))
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def mark_ai_call_read(log_id, store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE ai_call_logs SET is_read = 1 WHERE id = ? AND store_id = ?", (log_id, store_id))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

# ==========================================
# ★ Webhook Blackbox Logging
# 모든 웹훅 요청을 처리 결과와 관계없이 날것으로 기록
# ==========================================

def _ensure_webhook_logs_table(conn):
    """webhook_logs 테이블이 없으면 자동 생성"""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS webhook_logs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            received_at   TEXT NOT NULL,
            source_ip     TEXT DEFAULT '',
            method        TEXT DEFAULT 'POST',
            path          TEXT DEFAULT '/webhook',
            auth_ok       INTEGER DEFAULT 0,
            customer_phone TEXT DEFAULT '',
            call_state    TEXT DEFAULT '',
            call_type     TEXT DEFAULT '',
            raw_payload   TEXT DEFAULT '',
            stage         TEXT DEFAULT 'RECEIVED',
            http_status   INTEGER DEFAULT 200,
            result_msg    TEXT DEFAULT '',
            sms_sent      INTEGER DEFAULT 0
        )
    ''')
    conn.commit()

def save_webhook_log(source_ip='', method='POST', path='/webhook',
                     auth_ok=0, customer_phone='', call_state='', call_type='',
                     raw_payload='', stage='RECEIVED', http_status=200,
                     result_msg='', sms_sent=0):
    """웹훅 수신 즉시 블랙박스에 기록. 반환값: 생성된 log_id (update_webhook_log에 사용)"""
    import pytz
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(pytz.utc).astimezone(kst).strftime('%Y-%m-%d %H:%M:%S')
    conn = get_connection()
    c = conn.cursor()
    try:
        _ensure_webhook_logs_table(conn)
        c.execute('''
            INSERT INTO webhook_logs
              (received_at, source_ip, method, path, auth_ok, customer_phone,
               call_state, call_type, raw_payload, stage, http_status, result_msg, sms_sent)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            now_kst,  # ★ KST 명시 저장
            source_ip, method, path, auth_ok, customer_phone,
            call_state, call_type, raw_payload, stage,
            http_status, result_msg, sms_sent
        ))
        conn.commit()
        return c.lastrowid
    except Exception as e:
        print(f"[webhook_log] 저장 실패: {e}")
        return None
    finally:
        conn.close()

def update_webhook_log(log_id, **kwargs):
    """처리 단계가 바뀔 때 해당 row를 업데이트 (stage, result_msg, sms_sent 등)"""
    if not log_id:
        return False
    allowed = {'stage', 'http_status', 'result_msg', 'sms_sent', 'auth_ok',
               'customer_phone', 'call_state', 'call_type'}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return False
    conn = get_connection()
    c = conn.cursor()
    try:
        _ensure_webhook_logs_table(conn)
        set_clause = ', '.join(f'{k}=?' for k in updates)
        values = list(updates.values()) + [log_id]
        c.execute(f'UPDATE webhook_logs SET {set_clause} WHERE id=?', values)
        conn.commit()
        return True
    except Exception as e:
        print(f"[webhook_log] 업데이트 실패: {e}")
        return False
    finally:
        conn.close()

def get_webhook_logs(date_from=None, date_to=None, stage=None,
                     customer_phone=None, limit=200):
    """날짜·단계·번호 필터로 webhook_logs 조회. 최신순 반환."""
    conn = get_connection()
    try:
        _ensure_webhook_logs_table(conn)
        conditions = []
        params = []
        if date_from:
            conditions.append("received_at >= ?")
            params.append(f"{date_from} 00:00:00")
        if date_to:
            conditions.append("received_at <= ?")
            params.append(f"{date_to} 23:59:59")
        if stage:
            conditions.append("stage = ?")
            params.append(stage)
        if customer_phone:
            conditions.append("customer_phone LIKE ?")
            params.append(f"%{customer_phone}%")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(limit)
        rows = conn.execute(
            f"SELECT * FROM webhook_logs {where} ORDER BY id DESC LIMIT ?",
            params
        ).fetchall()
        cols = [d[0] for d in conn.execute(f"SELECT * FROM webhook_logs LIMIT 0").description]
        return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        print(f"[webhook_log] 조회 실패: {e}")
        return []
    finally:
        conn.close()

def get_webhook_stats(date_from=None, date_to=None):
    """날짜 범위별 단계 집계 통계"""
    conn = get_connection()
    try:
        _ensure_webhook_logs_table(conn)
        conditions = []
        params = []
        if date_from:
            conditions.append("received_at >= ?")
            params.append(f"{date_from} 00:00:00")
        if date_to:
            conditions.append("received_at <= ?")
            params.append(f"{date_to} 23:59:59")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = conn.execute(
            f"SELECT stage, COUNT(*) as cnt FROM webhook_logs {where} GROUP BY stage",
            params
        ).fetchall()
        stats = {r[0]: r[1] for r in rows}
        total = sum(stats.values())
        return {
            "total": total,
            "sms_ok":        stats.get("SMS_OK", 0),
            "sms_fail":      stats.get("SMS_FAIL", 0),
            "sms_queued":    stats.get("SMS_QUEUED", 0),
            "cooldown":      stats.get("COOLDOWN", 0),
            "auth_fail":     stats.get("AUTH_FAIL", 0),
            "phone_invalid": stats.get("PHONE_INVALID", 0),
            "outgoing":      stats.get("OUTGOING_SKIP", 0),
            "state_cached":  stats.get("STATE_CACHED", 0),
            "by_stage":      stats,
        }
    except Exception as e:
        print(f"[webhook_stats] 조회 실패: {e}")
        return {"total": 0}
    finally:
        conn.close()

def purge_old_webhook_logs(keep_days=30):
    """
    ★ 자동 정리: 30일 이상 지난 성공 로그 삭제 (DB 비대화 방지)
    - SMS_OK: 30일 보관
    - SMS_FAIL / AUTH_FAIL: 90일 보관 (실패 분석용)
    - 나머지(캐싱/쿨다운 등): 7일 보관
    cron_jobs.py 에서 주기적으로 호출
    """
    conn = get_connection()
    try:
        _ensure_webhook_logs_table(conn)
        deleted = 0
        # 성공 로그: 30일
        r = conn.execute(
            "DELETE FROM webhook_logs WHERE stage='SMS_OK' "
            "AND received_at < datetime('now', 'localtime', '-30 days')"
        )
        deleted += r.rowcount
        # 실패 로그: 90일
        for s in ('SMS_FAIL', 'AUTH_FAIL', 'PHONE_INVALID'):
            r = conn.execute(
                f"DELETE FROM webhook_logs WHERE stage=? "
                "AND received_at < datetime('now', 'localtime', '-90 days')", (s,)
            )
            deleted += r.rowcount
        # 캐싱/쿨다운 등 중간 로그: 7일
        r = conn.execute(
            "DELETE FROM webhook_logs WHERE stage NOT IN "
            "('SMS_OK','SMS_FAIL','AUTH_FAIL','PHONE_INVALID') "
            "AND received_at < datetime('now', 'localtime', '-7 days')"
        )
        deleted += r.rowcount
        conn.commit()
        if deleted:
            print(f"[webhook_purge] {deleted}건 삭제 완료 (보관 정책 적용)")
        return deleted
    except Exception as e:
        print(f"[webhook_purge] 실패: {e}")
        return 0
    finally:
        conn.close()



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
        c.execute("SELECT fee_rate FROM stores WHERE store_id = ?", (store_id,))
        row = c.fetchone()
        rate = row['fee_rate'] if row and row['fee_rate'] is not None else 0.033
        
        fee = int(amount * rate)
        net = amount - fee
        
        c.execute('''
            INSERT INTO orders (store_id, type, item_name, amount, fee_amount, net_amount, settlement_status, customer_phone, payment_method, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        query = f"SELECT * FROM orders WHERE store_id = ? AND created_at >= date('now', '-{days} days')"
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
            WHERE store_id = ? AND customer_phone = ?
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
            INSERT OR REPLACE INTO store_settings (store_id, key, value)
            VALUES (?, ?, ?)
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
        c.execute("SELECT key, value FROM store_settings WHERE store_id = ?", (store_id,))
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
            VALUES (?, ?, ?, ?, ?, ?)
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
        df = pd.read_sql("SELECT * FROM products WHERE store_id = ? AND is_active = 1 ORDER BY sort_order ASC", conn, params=(store_id,))
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
        c.execute("UPDATE reservations SET status = ? WHERE id = ?", (status, reservation_id))
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
        df = pd.read_sql("SELECT * FROM reservations WHERE store_id = ? ORDER BY res_date, res_time", conn, params=(store_id,))
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


# ==========================================
# User Management
# ==========================================

def save_user(user_data):
    conn = get_connection()
    c = conn.cursor()
    try:
        # user_data expects keys: '아이디', '상호명', etc. mapping to DB columns
        c.execute('''
            INSERT OR REPLACE INTO users (id, name, level, phone, joined_at)
            VALUES (?, ?, ?, ?, ?)
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
            SET auto_reply_msg = ?, 
                auto_reply_missed = ?, 
                auto_reply_end = ?,
                auto_refill_on = ?,
                auto_refill_amount = ?
            WHERE store_id = ?
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
            "UPDATE stores SET is_signed = 1, owner_name = ?, signed_at = ? WHERE store_id = ?",
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
        c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
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
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
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
        c.execute("SELECT * FROM stores WHERE store_id = ?", (store_id,))
        row = c.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()

def delete_store(store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM stores WHERE store_id = ?", (store_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Store Delete Error: {e}")
        return False
    finally:
        conn.close()

def get_store_virtual_number(store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM virtual_numbers WHERE store_id = ?", (store_id,))
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
    DNBXK7A2 형식의 고유 추천인 코드를 생성합니다.
    prefix(DNB) + 대문자+숫자 5자리 조합 = 총 8자리.
    충돌 시 최대 10회 재시도.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        chars = _string.ascii_uppercase + _string.digits
        for _ in range(10):
            suffix = ''.join(_random.choices(chars, k=5))
            code = prefix + suffix
            c.execute("SELECT 1 FROM stores WHERE my_referral_code = ?", (code,))
            if not c.fetchone():
                return code
        # 극히 드문 충돌 — 길이를 9자리로 늘려 재시도
        suffix = ''.join(_random.choices(chars, k=6))
        return prefix + suffix
    finally:
        conn.close()


def get_store_by_referral_code(code: str):
    """추천인 코드로 가게 정보를 조회합니다."""
    if not code:
        return None
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM stores WHERE my_referral_code = ?", (code.strip().upper(),))
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
        
        c.execute('''
            INSERT OR REPLACE INTO stores (
                store_id, password, name, owner_name, phone, category,
                info, menu_text, printer_ip, table_count, seats_per_table,
                points, membership, is_signed, signed_at, role, user_role, created_at, business_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        return pd.read_sql("SELECT * FROM stores ORDER BY created_at DESC", conn)
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
            VALUES (?, ?, ?, ?, ?, ?)
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
            VALUES (?, ?, ?, ?, ?)
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
                "SELECT * FROM wallet_logs WHERE store_id = ? ORDER BY id DESC LIMIT ?",
                conn,
                params=(store_id, limit),
            )
        return pd.read_sql(
            "SELECT * FROM wallet_logs ORDER BY id DESC LIMIT ?",
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
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('일시'), data.get('고객명'), data.get('연락처'), 
                data.get('메뉴/인원'), data.get('인원'), data.get('결제금액'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        elif user_type == "택배사업자":
             c.execute('''
                INSERT INTO records_delivery (date_time, sender_name, receiver_name, receiver_addr, item_type, fee, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
        c.execute("SELECT value FROM store_settings WHERE store_id = ? AND key = 'tables'", (store_id,))
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
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS ledger_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
        query = "SELECT * FROM ledger_records WHERE store_id = ?"
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

def get_all_ledger_records(record_type=None, limit=50):
    conn = get_connection()
    try:
        query = "SELECT * FROM ledger_records"
        params = []
        if record_type:
            query += " WHERE type = ?"
            params.append(record_type)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return pd.read_sql(query, conn, params=params)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def delete_ledger_record(record_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM ledger_records WHERE id = ?", (record_id,))
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
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    try:
        c = conn.cursor()
        try:
            c.execute("ALTER TABLE deliveries ADD COLUMN payment_type TEXT DEFAULT 'prepaid'")
        except:
            pass

        import random
        tn = data.get('tracking_code', f"TRK{datetime.now().strftime('%Y%m%d')}{random.randint(1000,9999)}")
        c.execute('''
            INSERT INTO deliveries (store_id, sender_name, sender_phone, sender_addr, 
                                    receiver_name, receiver_phone, receiver_addr, 
                                    item_name, weight, fare, status, tracking_number, created_at, payment_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        print(f"Delivery Save Error: {e}")
        return False, str(e)
    finally:
        conn.close()

def save_delivery_order(data):
    conn = get_connection()
    try:
        c = conn.cursor()
        
        sender_phone = data.get('sender_phone')
        sender_name = data.get('sender_name')
        sender_postcode = data.get('sender_postcode') or data.get('pickup_zip_code') or ""
        sender_base_address = data.get('sender_base_address') or data.get('pickup_road_address') or ""
        sender_detail_address = data.get('sender_detail_address') or data.get('pickup_detailed_address') or ""
        
        # 1. Update or Insert User in delivery_users
        c.execute("SELECT user_id FROM delivery_users WHERE phone_number = ?", (sender_phone,))
        user_row = c.fetchone()
        
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if user_row:
            user_id = user_row[0]
            c.execute('''
                UPDATE delivery_users 
                SET recent_sender_name = ?, recent_zip_code = ?, recent_road_address = ?, recent_detailed_address = ?, updated_at = ?
                WHERE user_id = ?
            ''', (sender_name, sender_postcode, sender_base_address, sender_detail_address, now_str, user_id))
        else:
            c.execute('''
                INSERT INTO delivery_users (phone_number, recent_sender_name, recent_zip_code, recent_road_address, recent_detailed_address, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (sender_phone, sender_name, sender_postcode, sender_base_address, sender_detail_address, now_str))
            user_id = c.lastrowid
            
        # 2. Insert into delivery_orders
        order_id = data.get('order_id') or data.get('tracking_code') or f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}"
        order_status = data.get('order_status') or data.get('status') or 'REQUESTED'
        payload = data.get('payload')
        c.execute('''
            INSERT INTO delivery_orders (order_id, user_id, sender_name, sender_phone, pickup_zip_code, pickup_road_address, pickup_detailed_address, order_status, created_at, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (order_id, rc.get('receiver_name'), rc.get('receiver_phone'), rc.get('postcode') or rc.get('delivery_zip_code') or "", rc.get('address') or rc.get('delivery_road_address') or "", rc.get('detail_address') or rc.get('delivery_detailed_address') or ""))
            
        conn.commit()
        return True, order_id
    except Exception as e:
        print(f"Delivery Order Save Error: {e}")
        return False, str(e)
    finally:
        conn.close()

def get_delivery_order(order_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM delivery_orders WHERE order_id = ?", (order_id,))
        row = c.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"Error fetching delivery order: {e}")
        return None
    finally:
        conn.close()

def acquire_delivery_order_lock(order_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('''
            UPDATE delivery_orders
            SET order_status = 'PROCESSING'
            WHERE order_id = ? AND (order_status = 'REQUESTED' OR order_status = 'DRAFT' OR order_status = 'FAILED')
        ''', (order_id,))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        print(f"Error acquiring lock: {e}")
        return False
    finally:
        conn.close()

def update_delivery_order_status(order_id, status, waybill_number=None, error_message=None):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('''
            UPDATE delivery_orders
            SET order_status = ?, waybill_number = ?, error_message = ?
            WHERE order_id = ?
        ''', (status, waybill_number, error_message, order_id))
        
        if waybill_number:
            c.execute('''
                UPDATE records_delivery
                SET tracking_code = ?, status = ?
                WHERE tracking_code = ?
            ''', (waybill_number, "접수완료", order_id))
            c.execute('''
                UPDATE deliveries
                SET tracking_number = ?, status = ?
                WHERE tracking_number = ?
            ''', (waybill_number, "접수완료", order_id))
        elif status == 'FAILED':
            c.execute('''
                UPDATE records_delivery
                SET status = ?
                WHERE tracking_code = ?
            ''', ("접수실패", order_id))
            c.execute('''
                UPDATE deliveries
                SET status = ?
                WHERE tracking_number = ?
            ''', ("접수실패", order_id))
        elif status == 'REQUESTED':
            c.execute('''
                UPDATE records_delivery
                SET status = ?
                WHERE tracking_code = ?
            ''', ("접수대기", order_id))
            c.execute('''
                UPDATE deliveries
                SET status = ?
                WHERE tracking_number = ?
            ''', ("접수대기", order_id))
            
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating delivery order status: {e}")
        return False
    finally:
        conn.close()

def get_store_deliveries(store_id):
    conn = get_connection()
    try:
        return pd.read_sql("SELECT * FROM deliveries WHERE store_id = ? ORDER BY id DESC", conn, params=(store_id,))
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def get_today_deliveries(store_id):
    conn = get_connection()
    try:
        today_prefix = datetime.now().strftime("%Y-%m-%d") + "%"
        query = "SELECT * FROM deliveries WHERE store_id = ? AND created_at LIKE ? ORDER BY id DESC"
        return pd.read_sql(query, conn, params=(store_id, today_prefix))
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def update_delivery_status(delivery_id, store_id, status):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE deliveries SET status = ? WHERE id = ? AND store_id = ?", (status, delivery_id, store_id))
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
    c.execute("SELECT wallet_balance FROM stores WHERE store_id = ?", (store_id,))
    row = c.fetchone()
    conn.close()
    if row and row["wallet_balance"] is not None:
        return int(row["wallet_balance"])
    return 0


def update_wallet_balance(store_id, new_balance):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE stores SET wallet_balance = ? WHERE store_id = ?", (int(new_balance), store_id))
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
    c.execute("SELECT store_id FROM virtual_numbers WHERE virtual_number = ?", (virtual_number,))
    row = c.fetchone()
    conn.close()
    return row["store_id"] if row else None


def save_virtual_number(virtual_number, store_id, label="", status="active"):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            """
            INSERT OR REPLACE INTO virtual_numbers (virtual_number, store_id, label, status, created_at)
            VALUES (?, ?, ?, ?, ?)
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
            INSERT OR REPLACE INTO couriers (courier_id, name, phone, company, vehicle_type, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
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
    c.execute("SELECT * FROM couriers WHERE courier_id = ?", (courier_id,))
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
            INSERT OR REPLACE INTO riders (rider_id, name, phone, area, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
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
    c.execute("SELECT * FROM riders WHERE rider_id = ?", (rider_id,))
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
            INSERT OR REPLACE INTO couriers (courier_id, name, phone, company, vehicle_type, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
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
    c.execute("SELECT * FROM couriers WHERE courier_id = ?", (courier_id,))
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
            INSERT OR REPLACE INTO riders (rider_id, name, phone, area, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
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
    c.execute("SELECT * FROM riders WHERE rider_id = ?", (rider_id,))
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
        c.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
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
        
        c.execute("UPDATE orders SET tracking_code = ? WHERE id = ?", (str(tracking_number), order_id))
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
        c.execute("UPDATE orders SET payment_method = ? WHERE id = ?", (method, order_id))
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
            VALUES (?, ?, ?, ?, ?, ?)
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
    c = conn.cursor()
    # Expenses Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            card_name TEXT,
            token TEXT,
            expires_at TEXT,
            proxy_ip TEXT,
            created_at TEXT
        )
    ''')
    
    conn.commit()
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
            VALUES (?, ?, ?, ?, ?, ?, ?)
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
        c.execute("SELECT locked_until FROM ledger_locks WHERE store_id = ?", (store_id,))
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
            
        c.execute("INSERT OR REPLACE INTO ledger_locks (store_id, locked_until, created_at) VALUES (?, ?, ?)", 
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        c.execute("SELECT SUM(price * quantity) as total_revenue FROM orders WHERE store_id = ?", (store_id,))
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
        c.execute("SELECT * FROM products WHERE id = ?", (product_id,))
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
            VALUES (?, ?, ?, ?, ?, ?, ?)
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
        query = "SELECT * FROM expenses WHERE store_id = ? AND date LIKE ?"
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
            WHERE store_id = ?
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
            WHERE store_id = ?
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
        c.execute("SELECT SUM(price * quantity) as revenue FROM orders WHERE store_id = ? AND created_at LIKE ?", (store_id, f"{today}%"))
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
        c.execute("SELECT wallet_balance FROM stores WHERE store_id = ?", (store_id,))
        row = c.fetchone()
        current = row['wallet_balance'] if row and row['wallet_balance'] else 0

        new_balance = current + amount + bonus

        c.execute("UPDATE stores SET wallet_balance = ? WHERE store_id = ?", (new_balance, store_id))
        c.execute('''
            INSERT INTO wallet_logs (store_id, change_type, amount, balance_after, memo, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
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
        c.execute("SELECT inventory FROM products WHERE id = ?", (product_id,))
        row = c.fetchone()
        if not row:
            return False, "상품을 찾을 수 없습니다."

        current = row['inventory'] if row['inventory'] else 0
        if current < quantity:
            return False, "재고가 부족합니다."

        c.execute("UPDATE products SET inventory = inventory - ? WHERE id = ?", (quantity, product_id))
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
            WHERE store_id = ? AND created_at >= ? AND created_at <= ?
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
        c.execute("UPDATE orders SET settlement_status = ? WHERE id = ?", (status, order_id))
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
        c.execute("SELECT * FROM customers WHERE customer_id = ? AND store_id = ?", (customer_id, store_id))
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
        c.execute("SELECT * FROM customers WHERE phone = ? ORDER BY last_visit DESC LIMIT 1", (phone,))
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
            INSERT OR REPLACE INTO customers (customer_id, store_id, name, phone, address, preferences, notes, total_orders, last_visit, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        c.execute(f"UPDATE customers SET {field} = ?, last_visit = ? WHERE customer_id = ? AND store_id = ?",
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
            UPDATE customers SET total_orders = total_orders + 1, last_visit = ?
            WHERE customer_id = ? AND store_id = ?
        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), customer_id, store_id))
        conn.commit()
        c.execute("SELECT total_orders FROM customers WHERE customer_id = ? AND store_id = ?", (customer_id, store_id))
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
        c.execute("SELECT daily_token_limit, current_usage, last_usage_date, points, tier FROM stores WHERE store_id = ?", (store_id,))
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
            c.execute("UPDATE stores SET current_usage = 0, last_usage_date = ? WHERE store_id = ?", (today, store_id))
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
            VALUES (?, ?, ?, ?, ?)
        ''', (store_id, input_tokens, output_tokens, cost, timestamp))
        
        # 2. Update Store (Deduct Points, Increment Usage)
        c.execute('''
            UPDATE stores 
            SET points = points - ?, 
                current_usage = current_usage + ?
            WHERE store_id = ?
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
            WHERE store_id = ? AND question = ?
        ''', (store_id, user_message))
        
        row = c.fetchone()
        if row:
            # Update hits
            c.execute("UPDATE cached_responses SET hits = hits + 1, last_used = ? WHERE store_id = ? AND question = ?", 
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
            INSERT OR REPLACE INTO cached_responses (store_id, question, answer, last_used, created_at)
            VALUES (?, ?, ?, ?, ?)
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
        c.execute("UPDATE stores SET points = COALESCE(points, 0) + ? WHERE store_id = ?", (amount, store_id))
        
        # 2. Log
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute('''
            INSERT INTO wallet_logs (store_id, change_type, amount, balance_after, memo, created_at)
            VALUES (?, ?, ?, (SELECT points FROM stores WHERE store_id = ?), ?, ?)
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
        query = "SELECT * FROM customers WHERE store_id = ?"
        params = [store_id]
        
        if filter_type == "recent":
            # Visit within last 30 days
            query += " AND last_visit >= date('now', '-30 days')"
            
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
        c.execute("SELECT points FROM stores WHERE store_id = ?", (store_id,))
        row = c.fetchone()
        current_points = row['points'] if row and row['points'] else 0
        
        if current_points < total_cost:
            return False, "잔액이 부족합니다.", None
        
        # 2. Deduct
        new_balance = current_points - total_cost
        c.execute("UPDATE stores SET points = ? WHERE store_id = ?", (new_balance, store_id))
        
        # 3. Log
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        memo = f"단체 문자 발송 ({customer_count}명)"
        
        c.execute('''
            INSERT INTO wallet_logs (store_id, change_type, amount, balance_after, memo, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (store_id, 'USE', -total_cost, new_balance, memo, now))
        
        # Threshold Alert Check
        try:
            if new_balance < 1000:
                c.execute("SELECT phone, name FROM stores WHERE store_id = ?", (store_id,))
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
        c.execute("UPDATE stores SET points = points + ? WHERE store_id = ?", (amount, store_id))
        
        # 2. Log
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        c.execute('''
            INSERT INTO wallet_logs (store_id, change_type, amount, balance_after, memo, created_at)
            VALUES (?, ?, ?, (SELECT points FROM stores WHERE store_id = ?), ?, ?)
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
        c.execute("SELECT points FROM stores WHERE store_id = ?", (store_id,))
        row = c.fetchone()
        current = row['points'] if row and row['points'] else 0
        
        if current < amount:
            return False
        
        # 2. Deduct
        c.execute("UPDATE stores SET points = points - ? WHERE store_id = ?", (amount, store_id))
        
        # 3. Log
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute('''
            INSERT INTO wallet_logs (store_id, change_type, amount, balance_after, memo, created_at)
            VALUES (?, ?, ?, (SELECT points FROM stores WHERE store_id = ?), ?, ?)
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
        c.execute("SELECT points FROM stores WHERE store_id = ?", (store_id,))
        row = c.fetchone()
        details["current_points"] = row['points'] if row and row['points'] else 0
        
        # 2. Recent Wallet Logs
        c.execute('''
            SELECT change_type as type, amount, created_at, memo 
            FROM wallet_logs 
            WHERE store_id = ? 
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
        c.execute("SELECT id FROM users WHERE id = ?", (store_id,))
        if c.fetchone():
            c.execute("UPDATE users SET password=?, name=?, phone=? WHERE id=?", (password, name, phone, store_id))
        else:
            c.execute("INSERT INTO users (id, password, name, phone, joined_at) VALUES (?, ?, ?, ?, ?)", 
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
        query = "SELECT * FROM wallet_topups WHERE store_id = ? ORDER BY requested_at DESC"
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
        c.execute("SELECT store_id FROM stores WHERE store_id = ?", (store_id,))
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
        c.execute("UPDATE stores SET user_role = ?, role = ? WHERE store_id = ?", (role, role, store_id))

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
            c.execute("UPDATE stores SET user_role = ?, role = ? WHERE store_id = ?", (role, role, store_id))
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
        # Check table exists (Safety)
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='courier_requests'")
        if not c.fetchone():
            # Create if missing (Migration)
            c.execute('''
                CREATE TABLE IF NOT EXISTS courier_requests (
                    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    created_at TEXT
                )
            ''')
            
        c.execute('''
            INSERT INTO courier_requests (
                citizen_id, sender_name, sender_phone, sender_addr,
                receiver_name, receiver_phone, receiver_addr,
                item_type, weight, status, payment_method, tracking_code, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            df = pd.read_sql("SELECT * FROM courier_requests WHERE citizen_id = ? ORDER BY created_at DESC", conn, params=(citizen_id,))
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
        c.execute("UPDATE stores SET points = points - ? WHERE store_id = ?", (amount, store_id))
        
        # Threshold Alert Check
        try:
            c.execute("SELECT points, phone, name FROM stores WHERE store_id = ?", (store_id,))
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
        c.execute("UPDATE courier_requests SET status = 'pending', payment_method = ? WHERE tracking_code = ?", (method, tracking_code))
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
        c.execute("SELECT referrer_id, first_tx_completed, subscription_tier FROM stores WHERE store_id = ?", (store_id,))
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
            VALUES (?, ?, ?, 'completed', datetime('now', 'localtime'))
        ''', (referrer_id, store_id, reward_amount))
        
        # 기사님(추천인) 지갑에 리워드 포인트 즉시 충전
        c.execute("UPDATE stores SET points = COALESCE(points, 0) + ? WHERE store_id = ?", (reward_amount, referrer_id))
        
        # 사장님 상태 반영 (-1은 발송 및 리워드 지급 완료 상태)
        c.execute("UPDATE stores SET first_tx_completed = -1 WHERE store_id = ?", (store_id,))
        conn.commit()
        
        return {"driver_id": referrer_id, "reward": reward_amount}
            
    except Exception as e:
        print(f"Reward error: {e}")
        return False
    finally:
        conn.close()

def get_crm_customers_by_tag(store_id, tag):
    """
    태그를 기준으로 CRM 고객 리스트를 조회합니다.
    """
    conn = get_connection()
    try:
        query = "SELECT * FROM customers WHERE store_id = ? AND tags LIKE ?"
        df = pd.read_sql(query, conn, params=(store_id, f'%{tag}%'))
        return df
    except Exception as e:
        print(f"CRM Fetch Error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def log_usage_cost(store_id, service_type, units_used, unit_price, calculated_cost, request_metadata=None, memo=None):
    """
    Log usage cost to usage_costs_log and wallet_transactions, and deduct points.
    All timestamps align to Asia/Seoul timezone.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        # 1. Deduct points from store
        c.execute("UPDATE stores SET points = points - ? WHERE store_id = ?", (calculated_cost, store_id))
        
        # 2. Get current balance
        c.execute("SELECT points, phone, name FROM stores WHERE store_id = ?", (store_id,))
        row = c.fetchone()
        points_after = row['points'] if row and row['points'] is not None else 0
        
        # 3. Log to usage_costs_log
        from datetime import datetime, timedelta, timezone
        kst = timezone(timedelta(hours=9))
        now_kst_str = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        
        metadata_str = str(request_metadata) if request_metadata else None
        
        c.execute('''
            INSERT INTO usage_costs_log (store_id, service_type, units_used, unit_price, calculated_cost, request_metadata, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (store_id, service_type, units_used, unit_price, calculated_cost, metadata_str, 'SUCCESS', now_kst_str))
        
        usage_log_id = c.lastrowid
        
        # 4. Log to wallet_transactions
        memo = memo or f"{service_type} 사용 요금"
        c.execute('''
            INSERT INTO wallet_transactions (store_id, transaction_type, amount, balance_after, reference_table, reference_id, memo, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (store_id, 'USE', -calculated_cost, points_after, 'usage_costs_log', usage_log_id, memo, now_kst_str))
        
        # Threshold Alert check (1,000 points)
        if points_after < 1000:
            try:
                print(f"[Threshold Alert] Store {store_id} points: {points_after}")
                import sms_manager
                phone = row['phone'] or store_id
                name = row['name'] or "가맹점"
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



# ============================================================
# ★ 콜백 퍼널 추적 함수 (URL 슬러그 + 클릭 추적 + 통계)
# ============================================================

def mask_phone(phone: str) -> str:
    """전화번호 마스킹: 01012341234 → 010****1234"""
    p = phone.replace('-', '').replace(' ', '').strip()
    if len(p) >= 10:
        return p[:3] + '****' + p[-4:]
    return '****'


def get_store_by_slug(slug: str) -> dict:
    """url_slug 또는 store_id로 가게 조회 (하위호환)"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM stores WHERE url_slug = ? LIMIT 1", (slug,))
        row = c.fetchone()
        if row:
            return dict(row)
        c.execute("SELECT * FROM stores WHERE store_id = ? LIMIT 1", (slug,))
        row = c.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"[get_store_by_slug] {e}")
        return None
    finally:
        conn.close()


def ensure_store_slug(store_id: str) -> str:
    """
    가게의 url_slug 반환.
    없으면 name에서 자동 생성 후 저장.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT url_slug, name FROM stores WHERE store_id = ?", (store_id,))
        row = c.fetchone()
        if not row:
            return store_id
        slug = row['url_slug']
        if slug:
            return slug
        name = row['name'] or store_id
        slug = name.replace(' ', '').replace('\t', '').strip()
        if not slug:
            slug = store_id
        c.execute("UPDATE stores SET url_slug = ? WHERE store_id = ?", (slug, store_id))
        conn.commit()
        return slug
    except Exception as e:
        print(f"[ensure_store_slug] {e}")
        return store_id
    finally:
        conn.close()


def log_callback_click(customer_phone: str, store_id: str,
                       source_ip: str = '', sms_sent_at: str = None) -> int:
    """콜백 링크 클릭 기록. 반환값: 생성된 funnel record id"""
    conn = get_connection()
    c = conn.cursor()
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        masked = mask_phone(customer_phone)
        c.execute('''
            INSERT INTO callback_funnel
                (customer_phone_masked, store_id, sms_sent_at, link_clicked_at, source_ip)
            VALUES (?, ?, ?, ?, ?)
        ''', (masked, store_id, sms_sent_at, now, source_ip))
        conn.commit()
        return c.lastrowid
    except Exception as e:
        print(f"[log_callback_click] {e}")
        return 0
    finally:
        conn.close()


def get_funnel_stats(date_from: str = None, date_to: str = None, store_id: str = None) -> dict:
    """퍼널 통계: SMS 발송 → 클릭 → 가입 → 구매 전환율"""
    conn = get_connection()
    c = conn.cursor()
    try:
        where, params = [], []
        if date_from:
            where.append("DATE(link_clicked_at) >= ?")
            params.append(date_from)
        if date_to:
            where.append("DATE(link_clicked_at) <= ?")
            params.append(date_to)
        if store_id:
            where.append("store_id = ?")
            params.append(store_id)
        clause = ("WHERE " + " AND ".join(where)) if where else ""

        def cnt(extra_cond=None):
            sql = f"SELECT COUNT(*) FROM callback_funnel {clause}"
            p = list(params)
            if extra_cond:
                sql += (" AND " if clause else " WHERE ") + extra_cond
            c.execute(sql, p)
            return c.fetchone()[0]

        wh_where = ["stage='SMS_OK'"]
        wh_params = []
        if date_from:
            wh_where.append("DATE(received_at) >= ?")
            wh_params.append(date_from)
        if date_to:
            wh_where.append("DATE(received_at) <= ?")
            wh_params.append(date_to)
        if store_id:
            wh_where.append("store_id = ?")
            wh_params.append(store_id)
        c.execute(f"SELECT COUNT(*) FROM webhook_logs WHERE {' AND '.join(wh_where)}", wh_params)
        sms_sent = c.fetchone()[0]

        clicks     = cnt()
        registered = cnt("registered_at IS NOT NULL")
        purchased  = cnt("purchased_at IS NOT NULL")

        def pct(n, total):
            return round(n / total * 100, 1) if total else 0

        return {
            "sms_sent":      sms_sent,
            "clicks":        clicks,
            "registered":    registered,
            "purchased":     purchased,
            "click_rate":    pct(clicks, sms_sent),
            "register_rate": pct(registered, sms_sent),
            "purchase_rate": pct(purchased, sms_sent),
        }
    except Exception as e:
        print(f"[get_funnel_stats] {e}")
        return {"error": str(e)}
    finally:
        conn.close()


# ============================================================
# ★ 업종별 콜백 템플릿 함수
# ============================================================

def get_callback_template(category: str) -> dict:
    """
    업종(category)에 맞는 콜백 SMS 템플릿 반환.
    매칭 우선순위:
      1) 정확히 일치 (예: '택배')
      2) 포함 여부 (예: '택배기사' → '택배')
      3) 기타 fallback
    반환: {message_template, redirect_path, display_name}
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        # 1) 정확 일치
        c.execute(
            "SELECT * FROM callback_templates WHERE category=? AND is_active=1 LIMIT 1",
            (category,)
        )
        row = c.fetchone()
        if row:
            return dict(row)

        # 2) 포함 관계 (category가 키워드를 포함하거나, 키워드가 category에 포함)
        c.execute(
            "SELECT * FROM callback_templates WHERE is_active=1"
        )
        rows = c.fetchall()
        for r in rows:
            key = r['category']
            if key in (category or '') or (category or '') in key:
                return dict(r)

        # 3) '기타' fallback
        c.execute(
            "SELECT * FROM callback_templates WHERE category='기타' AND is_active=1 LIMIT 1"
        )
        row = c.fetchone()
        return dict(row) if row else {
            'message_template': '[{store_name}] 전화 주셔서 감사합니다.\n아래 링크에서 문의해주세요 ▶ {link}',
            'redirect_path': '/market',
            'display_name': '기타',
        }
    except Exception as e:
        print(f"[get_callback_template] {e}")
        return {
            'message_template': '[{store_name}] 전화 주셔서 감사합니다 ▶ {link}',
            'redirect_path': '/market',
        }
    finally:
        conn.close()


def get_all_callback_templates() -> list:
    """관리자용: 모든 업종 템플릿 목록"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM callback_templates ORDER BY id")
        return [dict(r) for r in c.fetchall()]
    except Exception as e:
        print(f"[get_all_callback_templates] {e}")
        return []
    finally:
        conn.close()


def upsert_callback_template(category: str, display_name: str,
                              message_template: str, redirect_path: str) -> bool:
    """업종 템플릿 추가/수정 (관리자용)"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO callback_templates (category, display_name, message_template, redirect_path)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(category) DO UPDATE SET
                display_name=excluded.display_name,
                message_template=excluded.message_template,
                redirect_path=excluded.redirect_path,
                updated_at=datetime('now','localtime')
        ''', (category, display_name, message_template, redirect_path))
        conn.commit()
        return True
    except Exception as e:
        print(f"[upsert_callback_template] {e}")
        return False
    finally:
        conn.close()


# ==========================================
# 💳 KakaoPay Transactions
# ==========================================
def save_payment_tid(order_id, tid, method='KAKAOPAY'):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO payment_transactions (order_id, tid, payment_method, status, created_at)
            VALUES (?, ?, ?, 'READY', datetime('now','localtime'))
            ON CONFLICT(order_id) DO UPDATE SET
                tid=excluded.tid,
                payment_method=excluded.payment_method,
                status='READY',
                created_at=datetime('now','localtime')
        ''', (order_id, tid, method))
        conn.commit()
        return True
    except Exception as e:
        print(f"[save_payment_tid] Error: {e}")
        return False
    finally:
        conn.close()

def get_payment_tid(order_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT tid FROM payment_transactions WHERE order_id = ?", (order_id,))
        row = c.fetchone()
        return row['tid'] if row else None
    except Exception as e:
        print(f"[get_payment_tid] Error: {e}")
        return None
    finally:
        conn.close()

def update_payment_status(order_id, status):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE payment_transactions SET status = ? WHERE order_id = ?", (status, order_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"[update_payment_status] Error: {e}")
        return False
    finally:
        conn.close()


# ==========================================
# 🏨 Room Reservation Module Helpers
# ==========================================

def check_room_availability(store_id, room_id, check_in, check_out, exclude_reservation_id=None):
    import time
    conn = get_connection()
    c = conn.cursor()
    try:
        now_epoch = int(time.time())
        query = """
            SELECT id FROM reservations 
            WHERE store_id = ? 
              AND room_id = ? 
              AND (status = 'confirmed' OR (status = 'pending' AND expiry_time > ?))
              AND (check_in < ? AND check_out > ?)
        """
        params = [store_id, room_id, now_epoch, check_out, check_in]
        if exclude_reservation_id:
            query += " AND id != ?"
            params.append(exclude_reservation_id)
            
        c.execute(query, params)
        row = c.fetchone()
        return row is None  # True if available (no conflict)
    except Exception as e:
        print(f"[check_room_availability] Error: {e}")
        return False
    finally:
        conn.close()

def hold_room_reservation(store_id, room_id, check_in, check_out, guest_info, hold_duration_seconds=600):
    import time
    with _sqlite_lock:
        if not check_room_availability(store_id, room_id, check_in, check_out):
            return None
        
        conn = get_connection()
        c = conn.cursor()
        try:
            now_epoch = int(time.time())
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
                ) VALUES (?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?)
            """, (store_id, guest_name, guest_phone, created_at, guest_info_str, room_id, check_in, check_out, expiry_time))
            conn.commit()
            return c.lastrowid
        except Exception as e:
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
            WHERE id = ? AND store_id = ? AND status IN ('pending', 'confirmed')
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
            WHERE status = 'pending' AND expiry_time <= ?
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
        c.execute("SELECT * FROM reservations WHERE id = ? AND store_id = ?", (reservation_id, store_id))
        row = c.fetchone()
        if row:
            return dict(row)
        return None
    except Exception as e:
        print(f"[get_room_reservation] Error: {e}")
        return None
    finally:
        conn.close()

