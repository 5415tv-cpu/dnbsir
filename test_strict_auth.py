
import urllib.request
import urllib.parse
import json
import time

BASE_URL = "https://dnbsir-api-ap33e42daq-uc.a.run.app"
# BASE_URL = "http://localhost:8080"

def test_auth(store_id, password, mode, expected_code):
    url = f"{BASE_URL}/login"
    data = urllib.parse.urlencode({
        "store_id": store_id,
        "password": password,
        "mode": mode
    }).encode()
    
    print(f"Testing {mode.upper()} for {store_id}...", end=" ")
    
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req) as response:
            print(f"Success ({response.getcode()})")
            if expected_code not in [200, 303]:
                print(f"  [FAIL] Expected {expected_code}, got {response.getcode()}")
            else:
                print("  [PASS]")
                
    except urllib.error.HTTPError as e:
        print(f"Got {e.code}")
        if e.code == expected_code:
            print("  [PASS]")
        else:
            print(f"  [FAIL] Expected {expected_code}, got {e.code}")
    except Exception as e:
        print(f"Error: {e}")

# Generate random ID for new user
new_user_id = f"0109999{int(time.time())}"[-11:]
password = "123456"

print("=== Starting Auth Logic Verification ===")

# 1. Login with unknown user (Should fail 404)
test_auth(new_user_id, password, "login", 404)

# 2. Signup with new user (Should succeed 200/303)
# Note: urllib follows redirects automatically, so 303 becomes 200 (dashboard) or 303 (if manual).
# Default urllib follows. Admin dashboard returns 200.
test_auth(new_user_id, password, "signup", 200)

# 3. Signup AGAIN with same user (Should fail 409)
test_auth(new_user_id, password, "signup", 409)

# 4. Login with now existing user (Should succeed 200)
test_auth(new_user_id, password, "login", 200)

# 5. Login with wrong password (Should fail 401)
test_auth(new_user_id, "wrongpw", "login", 401)
