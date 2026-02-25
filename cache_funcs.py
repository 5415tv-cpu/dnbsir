
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
