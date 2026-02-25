
import os

BAD_FILE = "db_sqlite.py"
STUB_FILE = "db_sqlite_wallet_stub.py"

def fix_file():
    if not os.path.exists(BAD_FILE):
        print(f"[!] {BAD_FILE} not found.")
        return

    print(f"[*] Reading {BAD_FILE} in binary mode...")
    with open(BAD_FILE, "rb") as f:
        content = f.read()

    # Find the first null byte which indicates UTF-16 corruption start
    # normal python file shouldn't have null bytes
    idx = content.find(b'\x00')
    
    if idx != -1:
        print(f"[*] Corruption detected at index {idx}. Truncating...")
        # Check a few bytes before to ensure we don't cut mid-word? 
        # Actually UTF-16 LE appends `\r\n` as `\r\x00\n\x00`.
        # The first `\x00` is likely part of the first new line or character of the appended text.
        # We need to find the specific start of the appended block.
        # The append command was `type stub >> db_sqlite.py`.
        # PowerShell might have also added a BOM `\xff\xfe`.
        
        # Let's search backwards from the first null byte to find the last valid newline?
        # Or just truncate at `idx`.
        # But wait, if the original file didn't end with a newline, truncating at first `\x00` (which is high byte of a char) 
        # effectively cuts the char.
        # E.g. appended `A` -> `A\x00`. First `\x00` is index 1 of the new content.
        # So we should valid content up to `idx`? No, if `idx` is executing `A\x00`, then content[idx-1] is `A`.
        # So truncating at `idx-1` keeps `A`.
        # But `type` command might have started with BOM.
        
        # Safer bet: Truncate at `idx` is definitely safe for removing the nulls, 
        # but we might leave a stray byte or half-char.
        
        # Let's try to decode the valid part as utf-8 and see if it ends clean.
        valid_part = content[:idx]
        
        # If the corruption was appended, valid_part should be the original file content (plus maybe one byte of the new char).
        # Actually, if the first `\x00` is from the new content `C\x00`, then `C` is at `idx-1`.
        # Effectively we are cutting off the high byte of the first new char. The low byte remains.
        # That single low byte is likely garbage too if it wasn't meant to be there, or it's the start of the new content.
        # Since we want to remove the *appended* content entirely and re-append correctly,
        # we probably want to remove that stray byte too.
        
        # But wait! If the original file ended with `\r\n` (0D 0A), and we appended `\xff\xfe...`
        # `\x00` won't appear until after BOM.
        
        # Let's just find the last valid UTF-8 sequence before the first null? 
        # Actually, let's keep it simple: truncate at `idx`. If there is 1 byte garbage at end, python will complain about syntax error on the last line.
        # We can then check the last line and strip it if incomplete.
        
        # But `db_sqlite.py` ends with a function close usually.
        # Let's look at the byte before `idx`.
        last_byte = valid_part[-1]
        print(f"    Last byte value: {last_byte}")
        
    else:
        print("[?] No null bytes found. Maybe not UTF-16 corruption?")
        valid_part = content

    # Clean up trailing whitespace/garbage from the valid part
    # Convert to string to clean
    try:
        text = valid_part.decode('utf-8', errors='ignore')
        # Remove lines that look truncated or suspicious at the end?
        lines = text.splitlines()
        # The last line might be the start of the appended text (e.g. 'i' from 'import').
        # If the original file ended cleanly, the last line should be empty or valid code.
        
        # The original `db_sqlite.py` ended with `get_all_riders()` function or similar.
        print("    Last 5 lines of preserved content:")
        for l in lines[-5:]:
            print(f"      {l}")
            
        cleaned_text = "\n".join(lines).strip() + "\n"
        
    except Exception as e:
        print(f"[!] Decode error: {e}")
        return

    # Now append the stub properly
    print(f"[*] Reading stub {STUB_FILE}...")
    with open(STUB_FILE, "r", encoding="utf-8") as f:
        stub_content = f.read()

    print("[*] Writing repaired file...")
    with open(BAD_FILE, "w", encoding="utf-8") as f:
        f.write(cleaned_text + "\n" + stub_content)
        
    print("[OK] Repair complete.")

if __name__ == "__main__":
    fix_file()
