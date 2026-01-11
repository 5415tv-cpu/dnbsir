"""
📱 PWA (Progressive Web App) 헬퍼 모듈
"""
import streamlit as st
import streamlit.components.v1 as components

def inject_pwa_tags():
    """PWA 메타 태그와 manifest 링크 주입"""
    pwa_html = """
    <script>
        const metaTags = [
            { name: 'mobile-web-app-capable', content: 'yes' },
            { name: 'apple-mobile-web-app-capable', content: 'yes' },
            { name: 'apple-mobile-web-app-status-bar-style', content: 'black-translucent' },
            { name: 'theme-color', content: '#000000' }
        ];
        metaTags.forEach(tag => {
            let meta = document.createElement('meta');
            meta.name = tag.name;
            meta.content = tag.content;
            document.head.appendChild(meta);
        });
    </script>
    """
    components.html(pwa_html, height=0)

def get_pwa_css():
    """PWA 기본 앱 스타일만 반환 (레이아웃 간섭 제거)"""
    return """
    <style>
        [data-testid="stHeader"], [data-testid="stToolbar"] { display: none !important; }
        .stApp { background-color: #000000 !important; }
    </style>
    """
