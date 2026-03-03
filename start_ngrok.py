import time
from pyngrok import ngrok
# Try to connect to port 8000
try:
    public_url = ngrok.connect(8000)
    print(f"SUCCESS_URL: {public_url.public_url}")
    # Keep the process alive so the tunnel stays open
    while True:
        time.sleep(10)
except Exception as e:
    print(f"FAILED: {e}")
