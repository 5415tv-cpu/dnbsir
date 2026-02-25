
import os

def repair_db_sqlite():
    try:
        # Read the original file in binary to avoid encoding issues initially
        with open('db_sqlite.py', 'rb') as f:
            lines = f.readlines()
        
        print(f"Total lines read: {len(lines)}")
        
        # We know corruption starts after line 1883
        # lines is a list, 0-indexed. Line 1883 is index 1882.
        # So we want lines[0] to lines[1882] inclusive.
        # Slice is [:1883]
        
        clean_lines = lines[:1883]
        
        # Verify the last line looks like "conn.close()" or newline
        print(f"Last clean line: {clean_lines[-1]}")
        
        # Read the new functions
        with open('dashboard_funcs.py', 'rb') as f:
            new_funcs = f.read()
            
        # Write back
        with open('db_sqlite.py', 'wb') as f:
            f.writelines(clean_lines)
            f.write(b'\n\n')
            f.write(new_funcs)
            
        print("db_sqlite.py repaired successfully.")
        
    except Exception as e:
        print(f"Repair failed: {e}")

if __name__ == "__main__":
    repair_db_sqlite()
