
# ==========================================
# Dashboard Analytics & CRUD Support
# ==========================================

def delete_product(product_id, store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        # Verify ownership
        c.execute("DELETE FROM products WHERE id = ? AND store_id = ?", (product_id, store_id))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        print(f"Delete Product Error: {e}")
        return False
    finally:
        conn.close()

def update_order_status(order_id, status, store_id=None):
    conn = get_connection()
    c = conn.cursor()
    try:
        if store_id:
            c.execute("UPDATE orders SET settlement_status = ? WHERE id = ? AND store_id = ?", (status, order_id, store_id))
        else:
            c.execute("UPDATE orders SET settlement_status = ? WHERE id = ?", (status, order_id))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        print(f"Update Order Error: {e}")
        return False
    finally:
        conn.close()

def get_sales_stats(store_id, days=30):
    conn = get_connection()
    try:
        # Daily Sales
        query = f"""
            SELECT date(created_at) as date, SUM(amount) as total 
            FROM orders 
            WHERE store_id = ? AND created_at >= date('now', '-{days} days')
            GROUP BY date(created_at)
            ORDER BY date(created_at)
        """
        df = pd.read_sql(query, conn, params=(store_id,))
        stats = df.to_dict(orient='records')
        
        # Total Sales (Period)
        total_sales = df['total'].sum() if not df.empty else 0
        
        return {"daily": stats, "total_period": int(total_sales)}
    except Exception:
        return {"daily": [], "total_period": 0}
    finally:
        conn.close()

def get_top_products(store_id, limit=5):
    conn = get_connection()
    try:
        query = """
            SELECT item_name, SUM(amount) as total_sales, COUNT(*) as count
            FROM orders
            WHERE store_id = ?
            GROUP BY item_name
            ORDER BY total_sales DESC
            LIMIT ?
        """
        df = pd.read_sql(query, conn, params=(store_id, limit))
        return df.to_dict(orient='records')
    except Exception:
        return []
    finally:
        conn.close()
