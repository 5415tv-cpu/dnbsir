
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
