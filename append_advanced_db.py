
import os

new_code = """

# ==========================================
# Advanced Dashboard Analytics (Appended)
# ==========================================

def get_tax_estimates(store_id):
    conn = get_connection()
    try:
        # Calculate Monthly Sales first
        import datetime
        now = datetime.datetime.now()
        start_date = now.strftime("%Y-%m-01")
        
        query = "SELECT SUM(amount) FROM orders WHERE store_id = ? AND created_at >= ?"
        c = conn.cursor()
        c.execute(query, (store_id, start_date))
        result = c.fetchone()
        total_sales = result[0] if result and result[0] else 0
        
        # Simple KR Tax logic (Estimates)
        # VAT: 10% of Sales (roughly)
        # Income Tax: 3.3% (Freestyler/Simple) or progressive. Let's use 3% as safe estimate for 'General'
        vat = int(total_sales * 0.1)
        income_tax = int(total_sales * 0.033) 
        
        return {
            "month": now.month,
            "total_sales": total_sales,
            "vat": vat,
            "income_tax": income_tax
        }
    except Exception as e:
        print(f"Tax Est Error: {e}")
        return {"month": 0, "total_sales": 0, "vat": 0, "income_tax": 0}
    finally:
        conn.close()

def get_customer_revisit_rate(store_id):
    conn = get_connection()
    try:
        import datetime
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Who bought today?
        # Assuming 'customer_phone' or 'sender_phone' or 'buyer_phone' - existing schema uses 'sender_phone' in save_order usually or just 'phone' params
        # Let's check get_orders schema... actually safely use 'sender_phone' (from courier context) or need to check `orders` schema.
        # save_order uses `sender_phone`
        
        query_today = "SELECT DISTINCT sender_phone FROM orders WHERE store_id = ? AND date(created_at) = date('now')"
        c = conn.cursor()
        c.execute(query_today, (store_id,))
        today_customers = [row[0] for row in c.fetchall() if row[0]]
        
        if not today_customers:
            return {"total_today": 0, "revisit_count": 0, "rate": 0}
            
        revisit_count = 0
        for phone in today_customers:
            # Check if they appeared BEFORE today
            query_past = "SELECT 1 FROM orders WHERE store_id = ? AND sender_phone = ? AND date(created_at) < date('now') LIMIT 1"
            c.execute(query_past, (store_id, phone))
            if c.fetchone():
                revisit_count += 1
                
        rate = int((revisit_count / len(today_customers)) * 100)
        return {"total_today": len(today_customers), "revisit_count": revisit_count, "rate": rate}
        
    except Exception as e:
        print(f"Revisit Rate Error: {e}")
        return {"total_today": 0, "revisit_count": 0, "rate": 0}
    finally:
        conn.close()

def get_net_profit_analysis(store_id):
    conn = get_connection()
    try:
        # Mocking Platform breakdown since we don't have 'platform' column in basic schema yet.
        # We will assume all are 'Direct' or simulate distribution.
        
        # Real logic: Total Sales - (Agency Fees + Card Fees)
        # Agency Fee ~ 1000 won per order (delivery) or %? 
        # Card Fee ~ 2.2%
        
        stats = get_sales_stats(store_id) # Reuse existing if available or calc fresh
        total_sales = stats.get('total_period', 0) if isinstance(stats, dict) else 0
        
        # Use calc from tax est if 0 (as get_sales_stats defaults to 0 on error)
        if total_sales == 0:
            tax = get_tax_estimates(store_id)
            total_sales = tax['total_sales']
            
        # Estimated Fees
        card_fee = int(total_sales * 0.022)
        platform_fee = int(total_sales * 0.06) # Average 6% for Baemin/Yogiyo mix
        
        net_profit = total_sales - card_fee - platform_fee
        
        return {
            "total_sales": total_sales,
            "net_profit": net_profit,
            "fees": card_fee + platform_fee
        }
    except Exception as e:
        print(f"Net Profit Error: {e}")
        return {"total_sales": 0, "net_profit": 0, "fees": 0}
    finally:
        conn.close()
"""

with open("db_sqlite.py", "a", encoding="utf-8") as f:
    f.write(new_code)

print("Successfully appended advanced analytics to db_sqlite.py")
