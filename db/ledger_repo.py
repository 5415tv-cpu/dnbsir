import sqlite3
import pandas as pd
from datetime import datetime
from .core import get_connection

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
    except Exception:
        return {
            "total_revenue": 0,
            "recognized_expenses": 0,
            "predicted_tax": 0
        }
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
