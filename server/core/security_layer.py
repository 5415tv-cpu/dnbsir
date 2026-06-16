import datetime
from fastapi import Request, HTTPException, status
import logging
import base64
import json

try:
    import jwt
    HAS_JWT = True
except ImportError:
    HAS_JWT = False
    logging.warning("PyJWT is not installed. Using unsafe Base64 Mock for development.")


SECRET_KEY = "DONGNAE_BISEO_SUPER_SECRET_KEY_FOR_DEV_ONLY"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 14

def _mock_encode(payload: dict) -> str:
    return "MockJWT." + base64.b64encode(json.dumps(payload, default=str).encode()).decode() + ".Signature"

def _mock_decode(token: str) -> dict:
    if "MockJWT." not in token:
        raise HTTPException(status_code=401, detail="Invalid token")
    parts = token.split(".")
    return json.loads(base64.b64decode(parts[1]).decode())

def create_access_token(data: dict) -> str:
    """수명 15분짜리 고속 검증용 Access Token 생성"""
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    if HAS_JWT:
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return _mock_encode(to_encode)

def create_refresh_token(data: dict) -> str:
    """수명 14일짜리 Refresh Token 생성 (HttpOnly 쿠키 탑재용)"""
    to_encode = {"sub": data.get("sub")}
    expire = datetime.datetime.utcnow() + datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    if HAS_JWT:
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return _mock_encode(to_encode)

def verify_token(token: str):
    """토큰 무결성 및 만료 시간 검증"""
    if not HAS_JWT:
        return _mock_decode(token)
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logging.warning("[SecurityLayer] Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        logging.error("[SecurityLayer] Invalid token credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user_from_header(request: Request):
    """안드로이드 Webhook 라우터 등에서 사용할 JWT Auth 의존성 방어막"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    return payload
