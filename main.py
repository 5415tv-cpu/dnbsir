"""
동네비서 (Dongnebiseo) — Docker/Gunicorn 진입점
운영 주체: 탄탄제작소 (Tantan Fabrication)
서비스 브랜드: 동네비서

[구조조정 2026-07-05]
이전: server/webhook_app.py (레거시 경로, 이중 진입점 문제)
현재: app.py (단일 진입점으로 통일)

Docker CMD: gunicorn -k uvicorn.workers.UvicornWorker main:app
"""
from app import app  # 단일 진입점: app.py의 FastAPI 인스턴스

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
