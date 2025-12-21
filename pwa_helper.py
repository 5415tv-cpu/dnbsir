"""
📱 PWA (Progressive Web App) 헬퍼 모듈
- 스마트폰 앱처럼 설치 가능하게 해주는 기능
"""

import streamlit as st
import streamlit.components.v1 as components


def inject_pwa_tags():
    """PWA 메타 태그와 manifest 링크를 주입합니다."""
    
    pwa_html = """
    <script>
        // PWA manifest 동적 생성
        const manifest = {
            "name": "동네비서",
            "short_name": "동네비서",
            "description": "동네비서 - 똑똑한 AI 이웃",
            "start_url": window.location.origin,
            "display": "standalone",
            "background_color": "#667eea",
            "theme_color": "#667eea",
            "orientation": "portrait",
            "icons": [
                {
                    "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect fill='%23667eea' width='100' height='100' rx='20'/><text x='50' y='65' font-size='50' text-anchor='middle' fill='white'>🏘️</text></svg>",
                    "sizes": "192x192",
                    "type": "image/svg+xml",
                    "purpose": "any maskable"
                },
                {
                    "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect fill='%23667eea' width='100' height='100' rx='20'/><text x='50' y='65' font-size='50' text-anchor='middle' fill='white'>🏘️</text></svg>",
                    "sizes": "512x512",
                    "type": "image/svg+xml",
                    "purpose": "any maskable"
                }
            ]
        };
        
        // Manifest blob 생성 및 링크 추가
        const manifestBlob = new Blob([JSON.stringify(manifest)], {type: 'application/json'});
        const manifestURL = URL.createObjectURL(manifestBlob);
        
        // 기존 manifest 링크 제거
        const existingManifest = document.querySelector('link[rel="manifest"]');
        if (existingManifest) existingManifest.remove();
        
        // 새 manifest 링크 추가
        const manifestLink = document.createElement('link');
        manifestLink.rel = 'manifest';
        manifestLink.href = manifestURL;
        document.head.appendChild(manifestLink);
        
        // PWA 메타 태그 추가
        const metaTags = [
            { name: 'mobile-web-app-capable', content: 'yes' },
            { name: 'apple-mobile-web-app-capable', content: 'yes' },
            { name: 'apple-mobile-web-app-status-bar-style', content: 'black-translucent' },
            { name: 'apple-mobile-web-app-title', content: 'AI스토어' },
            { name: 'theme-color', content: '#667eea' },
            { name: 'msapplication-TileColor', content: '#667eea' },
            { name: 'viewport', content: 'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no' }
        ];
        
        metaTags.forEach(tag => {
            let meta = document.querySelector(`meta[name="${tag.name}"]`);
            if (!meta) {
                meta = document.createElement('meta');
                meta.name = tag.name;
                document.head.appendChild(meta);
            }
            meta.content = tag.content;
        });
        
        // iOS용 아이콘 추가
        const appleIcon = document.createElement('link');
        appleIcon.rel = 'apple-touch-icon';
        appleIcon.href = "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect fill='%23667eea' width='100' height='100' rx='20'/><text x='50' y='65' font-size='50' text-anchor='middle' fill='white'>🏘️</text></svg>";
        document.head.appendChild(appleIcon);
        
    </script>
    """
    
    components.html(pwa_html, height=0)


def show_install_prompt():
    """앱 설치 안내 배너를 표시합니다."""
    
    st.markdown("""
    <style>
        .pwa-install-banner {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            margin: 1rem 0;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        .pwa-install-banner h4 {
            margin: 0 0 0.5rem 0;
            font-size: 1.1rem;
        }
        .pwa-install-banner p {
            margin: 0;
            font-size: 0.9rem;
            opacity: 0.9;
        }
        .pwa-install-steps {
            background: rgba(255,255,255,0.15);
            padding: 0.8rem;
            border-radius: 8px;
            margin-top: 0.8rem;
            font-size: 0.85rem;
        }
    </style>
    
    <div class="pwa-install-banner">
        <h4>📱 앱처럼 사용하기</h4>
        <p>홈 화면에 추가하면 앱처럼 편리하게 이용할 수 있어요!</p>
        <div class="pwa-install-steps">
            <strong>📲 설치 방법:</strong><br>
            • <b>아이폰:</b> Safari 공유 버튼(□↑) → "홈 화면에 추가"<br>
            • <b>안드로이드:</b> 메뉴(⋮) → "홈 화면에 추가" 또는 "앱 설치"
        </div>
    </div>
    """, unsafe_allow_html=True)


def get_pwa_css():
    """PWA 최적화를 위한 추가 CSS를 반환합니다."""
    
    return """
    <style>
        /* ==========================================
           📱 PWA 최적화 CSS - 모바일 친화적 UI
           ========================================== */
        
        /* 스플래시 화면 스타일 */
        @media (display-mode: standalone) {
            body {
                -webkit-user-select: none;
                -moz-user-select: none;
                -ms-user-select: none;
                user-select: none;
            }
        }
        
        /* ==========================================
           📱 모바일 레이아웃 최적화
           ========================================== */
        @media (max-width: 768px) {
            /* 컨테이너 패딩 */
            .main .block-container {
                padding-left: 0.8rem !important;
                padding-right: 0.8rem !important;
                padding-top: 1.5rem !important;
                max-width: 100% !important;
            }
            
            /* 사이드바 숨김 */
            [data-testid="stSidebar"] {
                display: none;
            }
            
            /* 헤더 여백 조정 */
            header[data-testid="stHeader"] {
                display: none;
            }
            
            /* 탭 버튼 크기 조정 */
            .stTabs [data-baseweb="tab-list"] {
                gap: 3px !important;
            }
            
            .stTabs [data-baseweb="tab-list"] button {
                font-size: 1rem !important;
                padding: 12px 10px !important;
                min-height: 50px !important;
                font-weight: 600 !important;
            }
            
            /* 입력 필드 크기 조정 - iOS 줌 방지 */
            .stTextInput input, 
            .stTextArea textarea,
            .stSelectbox select,
            .stNumberInput input {
                font-size: 16px !important;
                min-height: 50px !important;
                padding: 12px !important;
            }
            
            /* 버튼 터치 영역 확대 */
            .stButton button {
                min-height: 55px !important;
                font-size: 1.1rem !important;
                border-radius: 12px !important;
                font-weight: 600 !important;
            }
            
            /* Primary 버튼 더 크게 */
            .stButton button[kind="primary"] {
                min-height: 65px !important;
                font-size: 1.3rem !important;
            }
            
            /* 컬럼 간격 조정 */
            [data-testid="column"] {
                padding: 0 5px !important;
            }
            
            /* 마크다운 제목 크기 */
            h1 { font-size: 1.8rem !important; }
            h2 { font-size: 1.5rem !important; }
            h3 { font-size: 1.3rem !important; }
            
            /* 구분선 */
            hr {
                margin: 1.5rem 0 !important;
            }
        }
        
        /* ==========================================
           📱 iOS safe area 대응
           ========================================== */
        @supports (padding-top: env(safe-area-inset-top)) {
            .main .block-container {
                padding-top: calc(1.5rem + env(safe-area-inset-top)) !important;
                padding-bottom: calc(2rem + env(safe-area-inset-bottom)) !important;
                padding-left: calc(0.8rem + env(safe-area-inset-left)) !important;
                padding-right: calc(0.8rem + env(safe-area-inset-right)) !important;
            }
        }
        
        /* ==========================================
           ⚡ 성능 및 UX 최적화
           ========================================== */
        
        /* 스크롤 성능 최적화 */
        .main {
            -webkit-overflow-scrolling: touch;
            scroll-behavior: smooth;
        }
        
        /* 터치 하이라이트 제거 */
        * {
            -webkit-tap-highlight-color: transparent;
        }
        
        /* 탭 전환 애니메이션 */
        .stTabs [data-baseweb="tab-panel"] {
            animation: fadeIn 0.25s ease-out;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* 카드 터치 피드백 */
        .store-card, .login-card, .service-card {
            transition: transform 0.15s ease-out, box-shadow 0.15s ease-out;
        }
        
        .store-card:active, .login-card:active, .service-card:active {
            transform: scale(0.97);
        }
        
        /* 버튼 터치 피드백 */
        .stButton button:active {
            transform: scale(0.97) !important;
            opacity: 0.9;
        }
        
        /* 로딩 스피너 색상 */
        .stSpinner > div {
            border-top-color: #667eea !important;
        }
        
        /* ==========================================
           🎨 글로벌 스타일 개선
           ========================================== */
        
        /* 더 나은 포커스 스타일 */
        input:focus, textarea:focus, select:focus {
            outline: 2px solid #667eea !important;
            outline-offset: 2px;
        }
        
        /* 플레이스홀더 스타일 */
        ::placeholder {
            color: #999 !important;
            opacity: 0.8;
        }
        
        /* 스크롤바 숨김 (모바일) */
        @media (max-width: 768px) {
            ::-webkit-scrollbar {
                width: 0;
                height: 0;
                background: transparent;
            }
        }
    </style>
    """

