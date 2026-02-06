import os

path = r"c:\Users\A\Desktop\AI_Store\ui\general_home.py"
print(f"Reading {path}...")
with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

output = []
for i, line in enumerate(lines):
    if 'st.link_button' in line and 'tel:' in line:
        # Replace Call Agent
        indent = " " * 12
        output.append(indent + 'st.markdown("""\n')
        output.append(indent + '<a href="tel:01030695810" class="custom-card-btn" target="_self">\n')
        output.append(indent + '    <div class="card-icon">📞</div>\n')
        output.append(indent + '    <div class="card-title">상담원 연결</div>\n')
        output.append(indent + '    <div class="card-desc">(전화 걸기)</div>\n')
        output.append(indent + '</a>\n')
        output.append(indent + '""", unsafe_allow_html=True)\n')
        print("Replaced Call Agent")
        
    elif 'st.link_button' in line and 'trace' in line:
        # Replace Tracking
        indent = " " * 12
        output.append(indent + 'st.markdown("""\n')
        output.append(indent + '<a href="https://www.ilogen.com/web/personal/trace" class="custom-card-btn" target="_blank">\n')
        output.append(indent + '    <div class="card-icon">🚚</div>\n')
        output.append(indent + '    <div class="card-title">화물 추적</div>\n')
        output.append(indent + '    <div class="card-desc">(배송 조회)</div>\n')
        output.append(indent + '</a>\n')
        output.append(indent + '""", unsafe_allow_html=True)\n')
        print("Replaced Tracking")
        
    elif 'st.link_button' in line and ('map.naver' in line or '지점 위치' in line):
        # Replace Location
        indent = " " * 12
        output.append(indent + 'st.markdown(f"""\n')
        output.append(indent + '<a href="{map_url}" class="custom-card-btn" target="_blank">\n')
        output.append(indent + '    <div class="card-icon">🗺️</div>\n')
        output.append(indent + '    <div class="card-title">지점 위치</div>\n')
        output.append(indent + '    <div class="card-desc">(지도 보기)</div>\n')
        output.append(indent + '</a>\n')
        output.append(indent + '""", unsafe_allow_html=True)\n')
        print("Replaced Location")
        
    else:
        output.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(output)
print("Files fixed successfully.")
