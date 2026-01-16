import streamlit as st
import streamlit.components.v1 as components

def daum_address_search(key="address_search"):
    """
    Daum 주소 검색 API를 호출하고 결과를 세션 상태에 반영하려고 시도하는 버튼
    """
    # HTML/JS 코드: 팝업을 띄우고 결과를 부모 창에 전달
    html_code = f"""
    <div id="search-container">
        <button id="search-btn" style="
            width: 100%;
            height: 40px;
            background-color: #2E7D32;
            border: none;
            border-radius: 8px;
            color: white;
            font-weight: bold;
            cursor: pointer;
            font-size: 14px;
        ">🔍 주소 검색</button>
    </div>

    <script src="//t1.daumcdn.net/mapjsapi/bundle/postcode/prod/postcode.v2.js"></script>
    <script>
        const btn = document.getElementById('search-btn');
        btn.onclick = function() {{
            new daum.Postcode({{
                oncomplete: function(data) {{
                    const fullAddr = data.roadAddress || data.address;
                    // Streamlit 입력 필드에 직접 값을 넣는 것은 보안상 제한될 수 있으므로
                    // 부모 창으로 메시지를 보냄
                    window.parent.postMessage({{
                        type: 'daum_address',
                        address: fullAddr,
                        key: '{key}'
                    }}, '*');
                    alert('주소가 선택되었습니다: ' + fullAddr + '\\n상세주소 입력창에 붙여넣거나 직접 입력해주세요.');
                }}
            }}).open();
        }};
    </script>
    """
    components.html(html_code, height=45)
