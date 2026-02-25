import os

path = r"c:\Users\A\Desktop\AI_Store\ui\general_home.py"
print(f"Reading {path}...")
with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

output = []
skip_count = 0

# Scan to replace the multiline st.markdown blocks for buttons
for i, line in enumerate(lines):
    if skip_count > 0:
        skip_count -= 1
        continue
        
    # Match Start of Call Agent Block
    if 'st.markdown("""' in line and '<a href="tel:' in lines[i+1]:
        # We found the block:
        # line i: st.markdown("""
        # line i+1: <a href="tel:...
        # ...
        # line i+6: """, unsafe...
        
        # We will replace this entire multi-line block with a single-line version (or dedented)
        # Construct the HTML manually
        indent = line[:line.find("st.markdown")]
        
        call_html = '<a href="tel:01030695810" class="custom-card-btn" target="_self"><div class="card-icon">📞</div><div class="card-title">상담원 연결</div><div class="card-desc">(전화 걸기)</div></a>'
        new_line = f'{indent}st.markdown(\'{call_html}\', unsafe_allow_html=True)\n'
        output.append(new_line)
        
        # Skip original lines. 
        # Check how many lines to skip.
        # We assume it goes until """, unsafe...
        # Look ahead
        cursor = i + 1
        while cursor < len(lines):
            if '""", unsafe_allow_html=True)' in lines[cursor] or 'st.markdown' in lines[cursor]:
                # Found end or next commands
                # If unsafe_allow_html is on the closing line
                 if '""", unsafe_allow_html=True)' in lines[cursor]:
                     skip_count = cursor - i # Skip to this line
                     break
            cursor += 1
        print("Fixed Call Agent Button")
        
    # Match Start of Tracking Block
    elif 'st.markdown("""' in line and '<a href="https://www.ilogen.com' in lines[i+1]:
        indent = line[:line.find("st.markdown")]
        track_html = '<a href="https://www.ilogen.com/web/personal/trace" class="custom-card-btn" target="_blank"><div class="card-icon">🚚</div><div class="card-title">화물 추적</div><div class="card-desc">(배송 조회)</div></a>'
        new_line = f'{indent}st.markdown(\'{track_html}\', unsafe_allow_html=True)\n'
        output.append(new_line)
        
        cursor = i + 1
        while cursor < len(lines):
            if '""", unsafe_allow_html=True)' in lines[cursor]:
                 skip_count = cursor - i
                 break
            cursor += 1
        print("Fixed Tracking Button")

    # Match Location Block
    elif 'st.markdown(f"""' in line and '<a href="{map_url}"' in lines[i+1]:
        indent = line[:line.find("st.markdown")]
        # For f-string, use f'...'
        loc_html = '<a href="{map_url}" class="custom-card-btn" target="_blank"><div class="card-icon">🗺️</div><div class="card-title">지점 위치</div><div class="card-desc">(지도 보기)</div></a>'
        new_line = f'{indent}st.markdown(f\'{loc_html}\', unsafe_allow_html=True)\n'
        output.append(new_line)
        
        cursor = i + 1
        while cursor < len(lines):
            if '""", unsafe_allow_html=True)' in lines[cursor]:
                 skip_count = cursor - i
                 break
            cursor += 1
        print("Fixed Location Button")

    else:
        output.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(output)
print("Fix v2 done.")
