# services/crypto_service.py
# AES-256 CBC 모드 암호화 서비스
# 주민등록번호 등 민감 개인정보 저장 전용
#
# ⚠️  보안 개선점 (고정 IV → 무작위 IV):
#   제공된 고정 IV 방식은 동일한 입력이 항상 동일한 암호문을 생성하여
#   패턴 분석 공격(Known-Plaintext Attack)에 취약합니다.
#   이 구현은 암호화할 때마다 무작위 IV(16바이트)를 생성하고,
#   [IV 16바이트 + 암호문]을 Base64로 합쳐 저장합니다.
#   복호화 시 앞 16바이트를 IV로, 나머지를 암호문으로 분리합니다.
#   기존 DB에 고정 IV로 저장된 데이터가 있다면 decrypt_legacy()를 사용하세요.

import os
import base64
import secrets
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

# ── 비밀키: 반드시 .env에 32바이트 이상 설정 ──
_raw_key = os.getenv("ENCRYPTION_KEY", "TantanFabDefaultKey32BytesExactly!")
SECRET_KEY = _raw_key.encode("utf-8")[:32].ljust(32, b"\x00")  # 정확히 32바이트

# 레거시 호환용 고정 IV (기존 저장 데이터 복호화 시 사용)
_LEGACY_IV = b"DongneBiseo16Byt"  # 정확히 16바이트


def _get_padded(plain: str) -> bytes:
    padder = padding.PKCS7(128).padder()
    return padder.update(plain.encode("utf-8")) + padder.finalize()


def _remove_padding(data: bytes) -> str:
    unpadder = padding.PKCS7(128).unpadder()
    return (unpadder.update(data) + unpadder.finalize()).decode("utf-8")


# ══════════════════════════════════════
# 메인 암호화 (무작위 IV — 권장)
# ══════════════════════════════════════
def encrypt(plain_text: str) -> str:
    """
    민감 정보를 AES-256 CBC로 암호화합니다.
    저장 형식: Base64( [랜덤IV 16바이트] + [암호문] )
    """
    try:
        if not plain_text:
            return ""
        iv = secrets.token_bytes(16)           # 암호화마다 다른 IV 생성
        cipher = Cipher(algorithms.AES(SECRET_KEY), modes.CBC(iv), backend=default_backend())
        enc = cipher.encryptor()
        encrypted = enc.update(_get_padded(plain_text)) + enc.finalize()
        return base64.b64encode(iv + encrypted).decode("utf-8")  # IV 앞에 붙여 저장
    except Exception as e:
        from logger import logger
        logger.error(f"[crypto] 암호화 실패: {e}")
        raise ValueError("보안 데이터 처리 실패")


def decrypt(encrypted_text: str) -> str:
    """
    encrypt()로 암호화된 문자열을 복호화합니다.
    저장 형식: Base64( [IV 16바이트] + [암호문] )
    """
    try:
        if not encrypted_text:
            return ""
        raw = base64.b64decode(encrypted_text.encode("utf-8"))
        iv, ciphertext = raw[:16], raw[16:]    # 앞 16바이트 = IV, 나머지 = 암호문
        cipher = Cipher(algorithms.AES(SECRET_KEY), modes.CBC(iv), backend=default_backend())
        dec = cipher.decryptor()
        return _remove_padding(dec.update(ciphertext) + dec.finalize())
    except Exception as e:
        from logger import logger
        logger.error(f"[crypto] 복호화 실패 (키 불일치 확인): {e}")
        return "복호화 실패 (인증 오류)"


# ══════════════════════════════════════
# 레거시 호환 (고정 IV — 기존 데이터 대응)
# ══════════════════════════════════════
def encrypt_legacy(plain_text: str) -> str:
    """고정 IV 방식 (기존 코드 호환용). 신규 저장에는 encrypt() 사용 권장."""
    try:
        if not plain_text:
            return ""
        cipher = Cipher(algorithms.AES(SECRET_KEY), modes.CBC(_LEGACY_IV), backend=default_backend())
        enc = cipher.encryptor()
        encrypted = enc.update(_get_padded(plain_text)) + enc.finalize()
        return base64.b64encode(encrypted).decode("utf-8")
    except Exception as e:
        from logger import logger
        logger.error(f"[crypto] legacy 암호화 실패: {e}")
        raise ValueError("보안 데이터 처리 실패")


def decrypt_legacy(encrypted_text: str) -> str:
    """고정 IV로 저장된 기존 데이터 복호화용."""
    try:
        if not encrypted_text:
            return ""
        raw = base64.b64decode(encrypted_text.encode("utf-8"))
        cipher = Cipher(algorithms.AES(SECRET_KEY), modes.CBC(_LEGACY_IV), backend=default_backend())
        dec = cipher.decryptor()
        return _remove_padding(dec.update(raw) + dec.finalize())
    except Exception as e:
        from logger import logger
        logger.error(f"[crypto] legacy 복호화 실패: {e}")
        return "복호화 실패 (인증 오류)"


# ══════════════════════════════════════
# 편의 별칭 (기존 코드와 이름 호환)
# ══════════════════════════════════════
def encrypt_resident_number(plain_text: str) -> str:
    """주민등록번호 암호화 (encrypt() 별칭)"""
    return encrypt(plain_text)


def decrypt_resident_number(encrypted_text: str) -> str:
    """주민등록번호 복호화 (decrypt() 별칭)"""
    return decrypt(encrypted_text)


# ══════════════════════════════════════
# 자동 판별 복호화 (IV 포함 여부 자동 감지)
# ══════════════════════════════════════
def smart_decrypt(encrypted_text: str) -> str:
    """
    저장된 데이터가 신규 형식(랜덤 IV)인지 레거시(고정 IV)인지 자동 판별하여 복호화.
    Base64 디코딩 후 길이가 16바이트 초과면 신규 형식으로 시도, 실패 시 레거시 시도.
    """
    if not encrypted_text:
        return ""
    try:
        raw = base64.b64decode(encrypted_text.encode("utf-8"))
        if len(raw) > 16:
            result = decrypt(encrypted_text)
            if "복호화 실패" not in result:
                return result
        return decrypt_legacy(encrypted_text)
    except Exception:
        return "복호화 실패 (인증 오류)"
