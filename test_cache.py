import db_sqlite as db
import datetime

STORE_ID = "test_cache_store"
QUESTION = "영업시간이 어떻게 되나요?"
ANSWER = "오전 9시부터 오후 6시까지입니다."

def test_cache():
    print("[*] Starting Cache Logic Test...")
    
    # 1. Clear previous test data
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM cached_responses WHERE store_id = ? AND question = ?", (STORE_ID, QUESTION))
    conn.commit()
    conn.close()
    
    # 2. Test Miss
    print("[-] Testing Cache Miss...")
    cached = db.get_cached_response(STORE_ID, QUESTION)
    if cached is None:
        print("[OK] Cache Miss verified.")
    else:
        print(f"[X] Failed: Should be miss, got '{cached}'")
        
    # 3. Save to Cache
    print("[-] Saving to Cache...")
    db.save_cached_response(STORE_ID, QUESTION, ANSWER)
    
    # 4. Test Hit
    print("[-] Testing Cache Hit...")
    cached = db.get_cached_response(STORE_ID, QUESTION)
    if cached == ANSWER:
        print(f"[OK] Cache Hit verified: '{cached}'")
    else:
        print(f"[X] Failed: Expected '{ANSWER}', got '{cached}'")
        
    # 5. Verify Hits Increment
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT hits FROM cached_responses WHERE store_id = ? AND question = ?", (STORE_ID, QUESTION))
    row = c.fetchone()
    hits = row['hits']
    # Hits increments on get_cached_response if found. We called it once successfully above.
    # Initial insert hits=0. First get -> hits=1.
    print(f"[-] Hit Count: {hits}")
    if hits >= 1:
        print("[OK] Hit counting verified.")
    else:
         print("[X] Failed: Hits not incremented.")
    conn.close()

if __name__ == "__main__":
    test_cache()
