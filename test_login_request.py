import requests

url = "http://localhost:8080/login"
data = {
    "store_id": "01000000000",
    "password": "valid_password" # DB check will fail or pass, but we want to see if it 500s before that.
}

try:
    print(f"Sending POST to {url}...")
    resp = requests.post(url, data=data, timeout=5)
    print(f"Status: {resp.status_code}")
    print(f"Content: {resp.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
