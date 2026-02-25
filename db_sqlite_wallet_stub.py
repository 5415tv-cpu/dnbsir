
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
