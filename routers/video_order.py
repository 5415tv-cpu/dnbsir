"""
M6. video_order — 동영상 주문 업로드 토큰 관리
동네비서가 토큰을 발급하고 탄탄제작소 Nginx의 auth_request 검증을 처리합니다.
"""
from fastapi import APIRouter, Request, Header, HTTPException
from fastapi.responses import Response
import secrets, time, os

router = APIRouter()

# 인메모리 토큰 저장소 (운영 확장 시 Redis로 교체)
_UPLOAD_TOKENS: dict[str, float] = {}
SHARED_SECRET = os.environ.get("TANTAN_UPLOAD_SECRET", "dnbsir-tantan-2024")


@router.post("/api/upload-token")
async def issue_upload_token(x_api_key: str = Header(...)):
    """
    앱 → 동네비서: 파일 업로드 일회용 토큰 발급 (5분 유효)
    탄탄제작소로 직접 업로드 시 Authorization 헤더에 담아 보냅니다.
    """
    if not secrets.compare_digest(x_api_key, SHARED_SECRET):
        raise HTTPException(403, "Unauthorized")
    token = secrets.token_urlsafe(32)
    _UPLOAD_TOKENS[token] = time.time()
    # 만료된 토큰 정리
    expired = [k for k, v in _UPLOAD_TOKENS.items() if time.time() - v > 300]
    for k in expired:
        _UPLOAD_TOKENS.pop(k, None)
    return {"token": token, "expires_in": 300}


@router.get("/api/verify-upload-token")
async def verify_upload_token(request: Request):
    """
    탄탄제작소 Nginx auth_request → 동네비서: 토큰 검증
    200 반환 시 Nginx가 업로드 허용, 401 반환 시 즉시 차단합니다.
    """
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "").strip()

    if not token:
        return Response(status_code=401)

    issued_at = _UPLOAD_TOKENS.get(token)
    if not issued_at or time.time() - issued_at > 300:
        _UPLOAD_TOKENS.pop(token, None)
        return Response(status_code=401)

    # 검증 성공 — 토큰 소모 (일회용)
    _UPLOAD_TOKENS.pop(token, None)
    return Response(status_code=200)
