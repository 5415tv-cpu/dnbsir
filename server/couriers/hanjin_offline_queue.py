import sqlite3
import json
import logging
from typing import List, Dict, Any

QUEUE_DB_PATH = "hanjin_offline_queue.db"

def init_queue_db():
    conn = sqlite3.connect(QUEUE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS offline_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            payload JSON,
            status TEXT DEFAULT 'FAILED_WAITING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            retry_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def push_to_queue(order_id: str, payload_dict: dict):
    """
    503 에러나 서버 점검 등으로 접수에 실패했을 때,
    오프라인 큐에 요청사항을 JSON으로 덤프해둡니다.
    """
    try:
        conn = sqlite3.connect(QUEUE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO offline_requests (order_id, payload) VALUES (?, ?)",
            (order_id, json.dumps(payload_dict, ensure_ascii=False))
        )
        conn.commit()
        conn.close()
        logging.info(f"[Hanjin Queue] Offline queue appended for order: {order_id}")
    except Exception as e:
        logging.error(f"[Hanjin Queue] Failed to push to offline queue: {e}")

def get_pending_requests() -> List[Dict[str, Any]]:
    try:
        conn = sqlite3.connect(QUEUE_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM offline_requests WHERE status = 'FAILED_WAITING'")
        rows = cursor.fetchall()
        
        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "order_id": r["order_id"],
                "payload": json.loads(r["payload"]),
                "retry_count": r["retry_count"]
            })
        conn.close()
        return results
    except Exception as e:
        logging.error(f"[Hanjin Queue] db read error: {e}")
        return []

def mark_success(req_id: int):
    try:
        conn = sqlite3.connect(QUEUE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE offline_requests SET status = 'SUCCESS' WHERE id = ?", (req_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        pass

def increment_retry(req_id: int):
    try:
        conn = sqlite3.connect(QUEUE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE offline_requests SET retry_count = retry_count + 1 WHERE id = ?", (req_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        pass

# 초기화 실행
init_queue_db()
