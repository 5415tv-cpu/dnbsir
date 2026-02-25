
import os

BAD_FILE = "db_sqlite.py"
STUB_FILE = "db_sqlite_payment_stub.py" # Use the NEW stub this time

def fix_file():
    if not os.path.exists(BAD_FILE):
        print(f"[!] {BAD_FILE} not found.")
        return

    print(f"[*] Reading {BAD_FILE} in binary mode...")
    with open(BAD_FILE, "rb") as f:
        content = f.read()

    # Find the *new* null byte.
    # The PREVIOUS fix (wallet stub) added a clean UTF-8 block.
    # The NEW append (payment stub) added corruption.
    # So searching for b'\x00' again should find the start of the NEW corruption.
    idx = content.find(b'\x00')
    
    if idx != -1:
        print(f"[*] Corruption detected at index {idx}. Truncating...")
        valid_part = content[:idx]
    else:
        print("[?] No null bytes found. Assuming file is clean (but maybe check for duplicate stubs?).")
        valid_part = content

    # Clean up trailing whitespace/garbage from the valid part
    try:
        text = valid_part.decode('utf-8', errors='ignore')
        lines = text.splitlines()
        
        # Remove empty lines at end just in case
        while lines and not lines[-1].strip():
            lines.pop()
            
        print("    Last 5 lines of preserved content:")
        for l in lines[-5:]:
            print(f"      {l}")
            
        cleaned_text = "\n".join(lines).strip() + "\n"
        
    except Exception as e:
        print(f"[!] Decode error: {e}")
        return

    # Check if confirm_payment is already present (avoid duplicate append if we run twice)
    if "def confirm_payment" in cleaned_text:
        print("[!] confirm_payment seems to be already present in valid part. Skipping append?")
        # If it's there AND we found null bytes later, maybe it's partially there or duplicates?
        # Let's be safe: if found, don't append. Just save clean text.
        print("[*] Writing repaired file (without re-appending stub)...")
        with open(BAD_FILE, "w", encoding="utf-8") as f:
            f.write(cleaned_text)
        print("[OK] Repair complete (Duplicate removed).")
        return

    # Now append the stub properly
    print(f"[*] Reading stub {STUB_FILE}...")
    with open(STUB_FILE, "r", encoding="utf-8") as f:
        stub_content = f.read()

    print("[*] Writing repaired file...")
    with open(BAD_FILE, "w", encoding="utf-8") as f:
        # separate with newlines
        f.write(cleaned_text + "\n\n" + stub_content)
        
    print("[OK] Repair complete.")

if __name__ == "__main__":
    fix_file()
