import requests
import sys

def test_login():
    url = "http://localhost:8080/login"
    print(f"Testing URL: {url}")

    # Test 1: Valid Login
    payload = {"store_id": "teststore", "password": "1234"}
    try:
        # allow_redirects=False to see the 303
        r = requests.post(url, data=payload, allow_redirects=False)
        print(f"Test 1 (teststore): Status={r.status_code}")
        if r.status_code == 303:
            print(f"Redirect Location: {r.headers.get('Location')}")
            # Check Cookie
            if "admin_session" in r.cookies:
                 print("Cookie 'admin_session' FOUND")
            else:
                 print("Cookie 'admin_session' NOT FOUND (Check valid_login logic)")
        else:
            print(f"Response: {r.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_login()
