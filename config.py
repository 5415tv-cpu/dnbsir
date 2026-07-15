"""
config.py ???덇굅???명솚 釉뚮┸吏
=================================
[2026-07-05 Phase 2 援ъ“議곗젙]

???뚯씪? 湲곗〈 肄붾뱶??`import config; config.get_secret()` ?몄텧???덈줈??dongnebiseo.config.settings 紐⑤뱢濡??곌껐?섎뒗 釉뚮┸吏?낅땲??

湲곗〈 肄붾뱶瑜??섏젙?섏? ?딄퀬?????ㅼ젙 ?쒖뒪?쒖쓣 ?ъ슜?????덉뒿?덈떎.

[留덉씠洹몃젅?댁뀡 媛?대뱶]
  # ?덇굅??諛⑹떇 (???뚯씪???듯빐 怨꾩냽 ?숈옉)
  import config
  key = config.get_secret("GOOGLE_API_KEY")

  # 신규 권장 방식 (점진적으로 교체)
  from dongnebiseo_app.config.settings import get_settings
  key = get_settings().app.gemini_api_key
"""

# 설정 모듈에서 레거시 호환 함수를 가져옵니다.
from dongnebiseo_app.config.settings import get_secret, get_settings

__all__ = ["get_secret", "get_settings"]
