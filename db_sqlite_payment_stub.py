
def confirm_payment(store_id, amount, order_id, payment_key):
    """
    Simulate payment confirmation for SQLite (Local Dev).
    """
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # 1. Update Points
        c.execute("UPDATE stores SET points = COALESCE(points, 0) + ? WHERE store_id = ?", (amount, store_id))
        
        # 2. Log (Simulated - No table yet locally, just print)
        print(f"[SQLite] Payment Confirmed: Store {store_id} +{amount}P (Order: {order_id})")
        
        conn.commit()
        return True
    except Exception as e:
        print(f"[!] SQLite Payment Error: {e}")
        return False
