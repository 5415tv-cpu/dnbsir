"""
Google Gemini Vision — 택배 송장 OCR 프록시
POST /api/ocr/kakao

2단계 방어 미들웨어 (process_and_sanitize_ocr_data):
  1차) 단골 주소록 (customer_address_book) — 전화번호 히트 시 덮어쓰기 + 즉시 반환
  2차) 오답 노트 (address_correction_log)  — frequency >= 2 반복 오답만 치환

UI 연동:
  - is_auto_corrected: True  → 프론트엔드 자동완성 토스트 표시
  - correction_message       → 토스트 메시지 내용
"""
import os, base64, json, re, sqlite3
import httpx
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Body
from fastapi.responses import JSONResponse

router = APIRouter()

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta"
    "/models/gemini-2.5-flash:generateContent"
)

# ──────────────────────────────────────────────────────────────
# 시스템 프롬프트
# ──────────────────────────────────────────────────────────────
SYSTEM_INSTRUCTION = """[역할]
너는 '동네비서' 택배 접수 시스템의 엄격한 광학 판독기(OCR)다. 대화나 설명은 일절 하지 않는다.

[작업]
첨부된 택배 송장 또는 수기 메모 사진을 분석하여 아래 JSON 스키마에 맞춰 데이터를 추출하라.

[한국 택배 송장 구조 이해]
한국 로젠/CJ/한진 송장에는 다음 구역이 있다:
- '받는 분' 칸: 배송 목적지 수령인 → receiver 필드
- '보내는 분' 칸 또는 좌측 스티커에 인쇄된 이름·전화번호·주소: 발송인 → sender 필드
- '집하자:' 레이블 바로 옆의 이름, '담당기사:' 레이블 옆 이름: 택배 직원 → sender 필드에 포함 금지
- W1-710 같은 영숫자 지점코드, '단성지점', 'XX택배지점': 지점 정보 → sender_address 포함 금지

[핵심 규칙]
보내는 분 정보는 인쇄(타이핑)되어 있을 수도, 손글씨일 수도 있다.
좌측 스티커 영역에 인쇄된 사람 이름과 전화번호가 있으면 sender_name, sender_phone으로 읽어라.
단, '집하자:' 또는 '담당기사:' 레이블에 명시적으로 연결된 이름만 제외한다.

[엄격한 제약 조건]
1. 절대 추측 금지: 흐릿한 글자는 빈 문자열("") 또는 null로 반환하라.
2. 형식 통일: 전화번호는 하이픈·괄호 제거 후 숫자만. (예: "01012345678")
3. 출력 제한: 오직 JSON만 출력. 마크다운이나 설명 절대 금지.

[출력 JSON 스키마]
{
  "sender_name": "보내는 사람 이름 (없으면 \"\")",
  "sender_phone": "보내는 사람 연락처 (숫자만, 없으면 \"\")",
  "sender_address": "보내는 사람 주소 (지점코드 제외, 없으면 \"\")",
  "receiver_name": "받는 사람 이름",
  "receiver_phone": "받는 사람 연락처 (숫자만)",
  "receiver_address": "받는 사람 주소",
  "item_name": "품명 (없으면 null)"
}"""

# ──────────────────────────────────────────────────────────────
# DB 경로 (ai_store.db)
# ──────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent.parent / "ai_store.db"


def _get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ──────────────────────────────────────────────────────────────
# 헬퍼: 전화번호 정규화
# ──────────────────────────────────────────────────────────────
def sanitize_phone_number(phone_str: str) -> str:
    """전화번호에서 하이픈 및 특수문자를 제거하고 숫자만 추출"""
    if not phone_str:
        return ""
    return re.sub(r'[^0-9]', '', phone_str)


# ──────────────────────────────────────────────────────────────
# 핵심 미들웨어: Gemini raw 데이터 → DB 교정
# ──────────────────────────────────────────────────────────────
def process_and_sanitize_ocr_data(raw_ai_data: dict) -> dict:
    """
    Gemini가 추출한 raw JSON 데이터를 DB와 대조하여 교정하는 미들웨어 함수
    """
    conn = _get_db()
    cursor = conn.cursor()

    sanitized_data = dict(raw_ai_data)
    sanitized_data['is_auto_corrected'] = False
    sanitized_data['correction_message'] = ""
    sanitized_data['receiver_postcode'] = ""
    sanitized_data['is_address_verified'] = None  # None = 아직 카카오 검증 전

    phone_number = sanitize_phone_number(sanitized_data.get('receiver_phone', ''))

    # ==========================================
    # [1차 방어선] 단골 주소록 (전화번호 기준)
    # ==========================================
    if phone_number:
        cursor.execute("""
            SELECT receiver_name, receiver_address
            FROM customer_address_book
            WHERE phone_number = ?
        """, (phone_number,))
        customer_row = cursor.fetchone()

        if customer_row:
            sanitized_data['receiver_name']    = customer_row['receiver_name']
            sanitized_data['receiver_address'] = customer_row['receiver_address']
            sanitized_data['is_auto_corrected']  = True
            sanitized_data['is_address_verified'] = True   # DB 저장된 주소는 신뢰함
            sanitized_data['correction_message'] = "과거 배송 이력을 바탕으로 주소를 자동 완성했습니다."

            cursor.execute("""
                UPDATE customer_address_book
                SET last_used_at = CURRENT_TIMESTAMP
                WHERE phone_number = ?
            """, (phone_number,))
            conn.commit()
            conn.close()
            return sanitized_data  # 1차 방어 성공 → 즉시 반환

    # ==========================================
    # [2차 방어선] 오답 노트 (frequency >= 2)
    # ==========================================
    raw_address = sanitized_data.get('receiver_address', '')
    if raw_address:
        cursor.execute("""
            SELECT corrected_text
            FROM address_correction_log
            WHERE ai_raw_text = ? AND frequency >= 2
        """, (raw_address,))
        correction_row = cursor.fetchone()

        if correction_row:
            sanitized_data['receiver_address']   = correction_row['corrected_text']
            sanitized_data['is_auto_corrected']  = True
            sanitized_data['correction_message'] = "AI 오독 패턴이 감지되어 올바른 주소로 자동 교정되었습니다."

    conn.close()
    # 3차 방어(카카오 주소 정제)는 엔드포인트에서 await로 호출
    return sanitized_data


# ──────────────────────────────────────────────────────────────
# 오답 노트 기록 함수
# ──────────────────────────────────────────────────────────────
def _record_correction(ai_text: str, corrected: str):
    """오답-정답 쌍 기록. 중복이면 frequency++."""
    if not ai_text or not corrected or ai_text == corrected:
        return
    try:
        conn = _get_db()
        conn.execute("""
            INSERT INTO address_correction_log (ai_raw_text, corrected_text, frequency)
            VALUES (?, ?, 1)
            ON CONFLICT(ai_raw_text, corrected_text) DO UPDATE SET
                frequency    = frequency + 1,
                last_seen_at = CURRENT_TIMESTAMP
        """, (ai_text.strip(), corrected.strip()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[correction_log] 기록 오류: {e}")


# ──────────────────────────────────────────────────────────────
# [3차 방어선] 카카오 Local API 주소 정제
# 판독: Gemini (있는 그대로 읽기)
# 교정: 카카오 주소검색 API (100% 존재하는 공식 도로명으로 교체)
# ──────────────────────────────────────────────────────────────
async def _normalize_address_via_kakao(address: str) -> dict:
    """
    3단계 루프로 AI 판독 주소를 공식 도로명으로 정제.

    Step A: 원본 전체 검색
    Step B: '동+숫자+길' → '로+숫자+길' 패턴 교정 후 검색
    Step C: 공백 기준으로 뒤 단어를 하나씩 제거하며 반복 검색
             → 히트 시 제거된 단어들을 detail(상세주소)로 반환

    반환: {success, road_address, postcode, jibun_address, detail}
    """
    if not address or len(address.strip()) < 4:
        return {"success": False, "road_address": address, "postcode": "", "jibun_address": address, "detail": ""}

    kakao_key = os.getenv("KAKAO_REST_API_KEY", "")
    if not kakao_key:
        print("[kakao_addr] KAKAO_REST_API_KEY 미설정 — 주소 정제 건너뜀")
        return {"success": False, "road_address": address, "postcode": "", "jibun_address": address, "detail": ""}

    def _build_result(docs: list, detail: str) -> dict:
        """카카오 API 결과 doc → 최종 딕셔너리"""
        doc  = docs[0]
        road  = doc.get("road_address") or {}
        jibun = doc.get("address")       or {}
        road_name  = road.get("address_name",  "").strip()
        postcode   = road.get("zone_no",        "").strip()
        jibun_name = jibun.get("address_name", "").strip()
        final = road_name or jibun_name or address
        print(f"[kakao_addr] ✅ '{address}' → '{final}' ({postcode}) | detail='{detail}'")
        return {
            "success":       True,
            "road_address":  final,
            "postcode":      postcode,
            "jibun_address": jibun_name,
            "detail":        detail,
        }

    try:
        async with httpx.AsyncClient(
            timeout=6.0,
            headers={"Authorization": f"KakaoAK {kakao_key}"}
        ) as client:

            async def _search(query: str) -> list:
                try:
                    r = await client.get(
                        "https://dapi.kakao.com/v2/local/search/address.json",
                        params={"query": query, "analyze_type": "similar", "size": 1}
                    )
                    if r.status_code == 200:
                        return r.json().get("documents", [])
                    print(f"[kakao_addr] HTTP {r.status_code}")
                except Exception as e:
                    print(f"[kakao_addr] 검색 오류: {e}")
                return []

            # ── Step A: 원본 전체 검색 ─────────────────────────
            docs = await _search(address)
            if docs:
                return _build_result(docs, detail="")

            # ── Step B: '동+숫자+길' → '로+숫자+길' 패턴 교정 ──
            # 예) "봉곡동 15길" → "봉곡로 15길"
            corrected = re.sub(r'(\S+)동(\s*\d+\s*길)', r'\1로\2', address)
            if corrected != address:
                docs = await _search(corrected)
                if docs:
                    return _build_result(docs, detail="")
            else:
                corrected = address  # 교정 없음 → 원본으로 Step C 진행

            # ── Step C: 점진적 단어 박리 루프 ────────────────────
            # 교정된 문자열을 공백 기준으로 분리
            words = corrected.split()
            for i in range(len(words) - 1, 0, -1):
                query = " ".join(words[:i])
                if len(query.strip()) < 4:
                    break
                docs = await _search(query)
                if docs:
                    # 박리된 뒷부분 = 상세주소 힌트 (건물명, 동·호수 등)
                    detail = " ".join(words[i:])
                    return _build_result(docs, detail=detail)

            # 모든 시도 실패
            print(f"[kakao_addr] ❌ 검색 실패: '{address}'")
            return {"success": False, "road_address": address, "postcode": "", "jibun_address": address, "detail": ""}

    except Exception as e:
        print(f"[kakao_addr] 전체 오류: {e}")
        return {"success": False, "road_address": address, "postcode": "", "jibun_address": address, "detail": ""}


def _upsert_address_book(phone: str, name: str, address: str):
    """단골 주소록 저장/갱신."""
    if not phone or not address:
        return
    clean = sanitize_phone_number(phone)
    try:
        conn = _get_db()
        conn.execute("""
            INSERT INTO customer_address_book (phone_number, receiver_name, receiver_address)
            VALUES (?, ?, ?)
            ON CONFLICT(phone_number) DO UPDATE SET
                receiver_name    = excluded.receiver_name,
                receiver_address = excluded.receiver_address,
                last_used_at     = CURRENT_TIMESTAMP
        """, (clean, name, address))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[address_book] 저장 오류: {e}")


# ──────────────────────────────────────────────────────────────
# OCR 메인 엔드포인트
# ──────────────────────────────────────────────────────────────
@router.post("/api/ocr/kakao")
async def gemini_ocr(image: UploadFile = File(...)):
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        return JSONResponse(content={"parsed": {}, "error": "GEMINI_API_KEY 미설정"})

    img_bytes = await image.read()
    b64_image = base64.b64encode(img_bytes).decode("utf-8")

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [{"parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": b64_image}}
        ]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{GEMINI_URL}?key={api_key}",
                headers={"Content-Type": "application/json"},
                json=payload
            )

        if resp.status_code != 200:
            return JSONResponse(content={
                "parsed": {},
                "error": f"Gemini API HTTP {resp.status_code}: {resp.text[:400]}"
            })

        data     = resp.json()
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

        # 마크다운 방어
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        gemini_result = json.loads(raw_text)

        # Gemini 필드명 → 내부 키 매핑
        raw_ai_data = {
            "receiver_name":    gemini_result.get("receiver_name", "") or "",
            "receiver_phone":   gemini_result.get("receiver_phone", "") or "",
            "receiver_address": gemini_result.get("receiver_address", "") or "",
            "sender_name":      gemini_result.get("sender_name", "") or "",
            "sender_phone":     gemini_result.get("sender_phone", "") or "",
            "sender_address":   gemini_result.get("sender_address", "") or "",
            "item_name":        gemini_result.get("item_name") or "",
        }

        # ── 2단계 방어 미들웨어 통과 (DB 1차+2차)
        sanitized = process_and_sanitize_ocr_data(raw_ai_data)

        # ── 3차 방어선: 카카오 Local API 주소 정제 (3단계 루프)
        # 1·2차에서 이미 검증된 주소(is_address_verified=True)는 건너뜀
        ai_raw_address = sanitized.get("receiver_address", "")
        kakao_detail   = ""   # Step C에서 박리된 상세주소 힌트
        if sanitized.get("is_address_verified") is not True and ai_raw_address:
            kakao_result = await _normalize_address_via_kakao(ai_raw_address)
            if kakao_result["success"]:
                sanitized["receiver_address"]   = kakao_result["road_address"]
                sanitized["receiver_postcode"]  = kakao_result["postcode"]
                sanitized["is_address_verified"] = True
                kakao_detail = kakao_result.get("detail", "")
                if ai_raw_address != kakao_result["road_address"]:
                    sanitized["is_auto_corrected"]  = True
                    sanitized["correction_message"] = (
                        f"'{ai_raw_address}' → 공식 도로명 주소로 자동 정제되었습니다."
                    )
                    # 오답 노트에도 학습
                    _record_correction(ai_raw_address, kakao_result["road_address"])
            else:
                sanitized["is_address_verified"] = False  # 검증 실패 → 빨간 테두리

        # 프론트엔드 폼 ID에 맞는 키로 변환
        # receiver_detail: Step C 박리값 우선, 없으면 Gemini 원본 detail
        parsed = {
            "receiver_name":     sanitized["receiver_name"],
            "receiver_phone":    sanitized["receiver_phone"],
            "receiver_addr":     sanitized["receiver_address"],
            "receiver_postcode": sanitized.get("receiver_postcode", ""),
            "receiver_detail":   kakao_detail,   # ← 박리된 상세주소 자동 채움
            "sender_name":       sanitized["sender_name"],
            "sender_phone":      sanitized["sender_phone"],
            "sender_addr":       sanitized["sender_address"],
            "sender_detail":     "",
            "item_name":         sanitized["item_name"],
        }

        if sanitized["is_auto_corrected"]:
            print(f"[OCR] ✅ 자동 교정: {sanitized['correction_message']}")

        return JSONResponse(content={
            "parsed":             parsed,
            "ai_raw_address":     ai_raw_address,   # 프론트 오답노트용
            "full_text":          raw_text,
            "template_ok":        True,
            "is_auto_corrected":  sanitized["is_auto_corrected"],
            "is_address_verified": sanitized.get("is_address_verified", None),
            "correction_message": sanitized["correction_message"],
        })

    except json.JSONDecodeError as e:
        return JSONResponse(content={
            "parsed":    {},
            "full_text": raw_text if 'raw_text' in dir() else "",
            "error":     f"JSON 파싱 실패: {str(e)}"
        })
    except Exception as e:
        return JSONResponse(content={"parsed": {}, "error": str(e)})


# ──────────────────────────────────────────────────────────────
# 피드백 엔드포인트 — Step 3 [다음] 클릭 시 호출
# POST /api/ocr/correction
# ──────────────────────────────────────────────────────────────
@router.post("/api/ocr/correction")
async def save_correction(
    ai_text: str = Body(""),
    corrected: str = Body(""),
    phone: str = Body(""),
    receiver_name: str = Body(""),
    receiver_address: str = Body("")
):
    """
    사용자가 Step 3에서 주소를 수정하면 호출.
    오답 노트 학습 + 단골 주소록 저장.
    """
    _record_correction(ai_text, corrected)
    if phone and receiver_address:
        _upsert_address_book(phone, receiver_name, receiver_address)
    return JSONResponse(content={"ok": True})
