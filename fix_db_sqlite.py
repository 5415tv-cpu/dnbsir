
import os

try:
    with open('db_sqlite.py', 'rb') as f:
        content = f.read()
        
    term = "def check_ai_limit"
    term_bytes = term.encode('utf-8')
    
    # Check if content seems to be UTF-16 (has null bytes)
    if b'\x00' in content:
        print("[-] Detected null bytes (likely UTF-16). Attempting conversion...")
        try:
            # Try decoding as utf-16
            text = content.decode('utf-16')
        except:
             # Fallback: ignore errors or try utf-16-le
             text = content.decode('utf-16-le', errors='ignore')
    else:
        text = content.decode('utf-8', errors='ignore')

    # Remove strict null bytes just in case
    text = text.replace('\x00', '')
    
    with open('db_sqlite.py', 'w', encoding='utf-8') as f:
        f.write(text)
        
    print("[OK] db_sqlite.py fixed.")
except Exception as e:
    print(f"[X] Failed to fix: {e}")
