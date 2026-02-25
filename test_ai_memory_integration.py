# import pytest
# Removed dependency on pytest for standalone execution
from server.webhook_app import app
from fastapi.testclient import TestClient
import db_manager as db

client = TestClient(app)

def test_chat_memory_flow():
    # 1. Setup - Ensure clean state for test user
    store_id = "test_store_memory_v1"
    phone = "010-9999-8888"
    
    # Clean up previous test data if exists
    # (Assuming we have a way to clean or we just overwrite)
    # db.delete_customer(phone, store_id) # API might not expose this, but we can ignore for now or mock
    
    print(f"\n[Test] Starting Chat Memory Test for {phone}")

    # 2. First Interaction - Provide Name & Preference
    # "My name is Kim Cheol-su and I don't like spicy food."
    msg1 = "내 이름은 김철수고 매운거 못먹어."
    response1 = client.post("/api/chat", json={
        "message": msg1,
        "phone": phone,
        "store_id": store_id
    })
    
    assert response1.status_code == 200
    data1 = response1.json()
    print(f"\n[User] Message Sent (Length: {len(msg1)})")
    print(f"[AI] Response Received (Length: {len(data1.get('response', ''))})")
    print(f"[Info] Customer Info: {data1.get('customer_info')}")
    
    # Verify Metadata Extraction
    assert data1['success'] is True
    assert data1['customer_info']['name'] == "김철수"
    # Note: 'preferences' might be a string or list depending on implementation
    assert "매운" in data1['customer_info']['preferences'] or "맵지" in data1['customer_info']['preferences']

    # 3. Second Interaction - Verify Memory
    # "What can't I eat?"
    msg2 = "나 뭐 못먹지?"
    response2 = client.post("/api/chat", json={
        "message": msg2,
        "phone": phone,
        "store_id": store_id
    })
    
    assert response2.status_code == 200
    data2 = response2.json()
    print(f"\n[User] Message Sent (Length: {len(msg2)})")
    print(f"[AI] Response Received (Length: {len(data2.get('response', ''))})")
    
    # Verify Response contains memory context
    # AI should mention "spicy" or "매운"
    assert "매운" in data2['response'] or "맵지" in data2['response']
    
    print("\n✅ Chat Memory Test Passed!")

if __name__ == "__main__":
    import sys
    import io
    
    # Redirect stdout/stderr to file with UTF-8 encoding
    with open("test_log.txt", "w", encoding="utf-8") as f:
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = f
        sys.stderr = f
        
        try:
            print("Starting Test...")
            test_chat_memory_flow()
            print("Test Completed Successfully.")
        except AssertionError as e:
            print(f"\n❌ Test Failed: {e}")
            import traceback
            traceback.print_exc()
        except Exception as e:
            print(f"\n❌ System Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            print("Test log written to test_log.txt")
