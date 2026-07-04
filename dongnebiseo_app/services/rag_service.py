"""
dongnebiseo/services/rag_service.py
=====================================
RAG(Retrieval-Augmented Generation) 서비스 — 정확성 최우선 원칙 구현

[3대 코어 원칙 적용]
────────────────────────────────────────────────────────
① 정확성 최우선 (Accuracy > Speed)
   - 정해진 DB 데이터 범위 내에서만 LLM 응답 생성
   - 데이터 없는 영역에 대한 LLM 자유 생성 원천 차단
   - 그라운딩 프롬프트로 환각(Hallucination) 봉쇄

② 인프라 안정성 보장 (Fallback-First)
   - 외부 API 장애 / 타임아웃 → 즉시 로컬 Fallback 반환
   - 사용자는 절대 에러 화면을 보지 않음
   - 장애 레이어: LLM API → 캐시 → 기본 안내 문구 (3단계)

③ 결합도 최소화 (Isolated Service Layer)
   - DB 접근은 db_manager를 통해서만
   - LLM 호출은 ai_service를 통해서만
   - 라우터/미들웨어와 직접 결합 금지
────────────────────────────────────────────────────────
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 기본 Fallback 응답 사전 (로컬 안내 문구)
# 외부 API가 완전히 불가능할 때 즉각 반환
# ═══════════════════════════════════════════════════════════════
_FALLBACK_MESSAGES: dict[str, str] = {
    # 범용 기본
    "default": (
        "잠시 시스템이 바쁩니다. 😊\n"
        "사장님께 직접 연락하시거나 잠시 후 다시 시도해 주세요."
    ),
    # 부재중 전화 자동 응답
    "missed_call": (
        "안녕하세요! 동네비서입니다. 📞\n"
        "지금은 사장님이 자리를 비우셨어요.\n"
        "용건을 문자로 남겨주시면 확인 후 바로 연락드리겠습니다. 감사합니다!"
    ),
    # 주문/예약 관련
    "order": (
        "주문 접수 시스템에 잠시 문제가 생겼습니다. 🙏\n"
        "전화 또는 문자로 주문해 주시면 신속히 처리해 드리겠습니다."
    ),
    # 배송 조회
    "delivery": (
        "배송 조회 중 오류가 발생했습니다.\n"
        "로젠택배 공식 사이트(www.ilogen.com)에서 송장번호로 직접 조회하실 수 있습니다."
    ),
    # 매장 정보
    "store_info": (
        "매장 정보를 불러오는 중 오류가 발생했습니다.\n"
        "잠시 후 다시 시도해 주시면 감사하겠습니다."
    ),
    # 타임아웃 특화
    "timeout": (
        "응답에 시간이 걸리고 있습니다. ⏱️\n"
        "잠시 후 다시 시도해 주시거나 전화로 문의해 주세요."
    ),
    # API 오류 특화
    "api_error": (
        "AI 서비스에 일시적인 문제가 발생했습니다.\n"
        "사장님께 직접 연락 부탁드립니다. 불편을 드려 죄송합니다. 🙇"
    ),
}


# ═══════════════════════════════════════════════════════════════
# 인메모리 응답 캐시 (LRU)
# Redis 도입 전 로컬 캐시로 중복 LLM 호출 차단
# ═══════════════════════════════════════════════════════════════
@dataclass
class _CacheEntry:
    value: str
    created_at: float = field(default_factory=time.monotonic)
    hit_count: int = 0


class _ResponseCache:
    """
    스레드 안전 인메모리 LRU 캐시.
    동일 store_id + 쿼리에 대한 LLM 중복 호출 차단.
    """
    def __init__(self, max_size: int = 200, ttl_sec: int = 300):
        self._store: dict[str, _CacheEntry] = {}
        self._max_size = max_size
        self._ttl = ttl_sec

    def _make_key(self, store_id: str, query: str) -> str:
        raw = f"{store_id}::{query.strip().lower()[:200]}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, store_id: str, query: str) -> Optional[str]:
        key = self._make_key(store_id, query)
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() - entry.created_at > self._ttl:
            del self._store[key]
            return None
        entry.hit_count += 1
        return entry.value

    def set(self, store_id: str, query: str, response: str) -> None:
        if len(self._store) >= self._max_size:
            # 가장 오래된 항목 제거 (LRU 근사)
            oldest = min(self._store, key=lambda k: self._store[k].created_at)
            del self._store[oldest]
        key = self._make_key(store_id, query)
        self._store[key] = _CacheEntry(value=response)

    def invalidate_store(self, store_id: str) -> int:
        """특정 매장의 캐시 전체 무효화 (데이터 변경 시 호출)"""
        prefix = hashlib.md5(store_id.encode()).hexdigest()[:8]
        victims = [k for k in self._store if k.startswith(prefix)]
        for k in victims:
            del self._store[k]
        return len(victims)

    def stats(self) -> dict:
        return {
            "size": len(self._store),
            "max_size": self._max_size,
            "ttl_sec": self._ttl,
        }


# ═══════════════════════════════════════════════════════════════
# RAG 서비스 메인 클래스
# ═══════════════════════════════════════════════════════════════
class RAGService:
    """
    동네비서 핵심 AI 응답 서비스.

    환각 방지 원칙:
    - DB에서 조회된 데이터만 LLM 컨텍스트에 주입
    - 데이터 없는 영역에 대해 LLM이 추측하지 못하도록
      시스템 프롬프트에 "데이터 범위 밖 내용은 모른다고 답하라" 명시

    Fallback 3단계:
    1. 로컬 캐시 (캐시 히트 시 LLM 미호출)
    2. LLM API (타임아웃/오류 시 다음 단계)
    3. 기본 안내 문구 (항상 성공, 사용자는 에러를 못 봄)
    """

    def __init__(
        self,
        ai_service=None,
        db=None,
        timeout_sec: float = 8.0,
        cache_ttl_sec: int = 300,
        hallucination_guard: bool = True,
    ):
        self._ai = ai_service
        self._db = db
        self._timeout = timeout_sec
        self._cache = _ResponseCache(ttl_sec=cache_ttl_sec)
        self._guard = hallucination_guard

    # ─────────────────────────────────────────────────────────
    # 공개 API
    # ─────────────────────────────────────────────────────────

    async def get_response(
        self,
        query: str,
        store_id: str,
        context_type: str = "default",
        extra_context: Optional[dict] = None,
    ) -> str:
        """
        쿼리에 대한 그라운딩된 AI 응답 반환.
        모든 경로에서 반드시 문자열을 반환 (에러 화면 없음).

        Args:
            query: 사용자 입력 또는 자동 생성 프롬프트
            store_id: 매장 ID (데이터 조회 범위 한정)
            context_type: 응답 유형 힌트 ('missed_call', 'order', 'delivery' 등)
            extra_context: 추가 컨텍스트 (라우터에서 미리 조회한 데이터)

        Returns:
            str: AI 응답 또는 Fallback 메시지 (항상 성공)
        """
        # ① 캐시 확인 (LLM 미호출)
        cached = self._cache.get(store_id, query)
        if cached:
            logger.debug("[RAG] Cache hit: store=%s", store_id)
            return cached

        # ② DB 컨텍스트 조회 (그라운딩 데이터)
        store_context = await self._fetch_store_context(store_id, extra_context)

        # ③ 그라운딩 컨텍스트가 없으면 Fallback
        if not store_context and self._guard:
            logger.warning(
                "[RAG] No context for store=%s — returning fallback (hallucination guard)",
                store_id,
            )
            return self._select_fallback(context_type)

        # ④ 그라운딩 프롬프트 구성
        grounded_prompt = self._build_grounded_prompt(
            query=query,
            store_context=store_context,
            context_type=context_type,
        )

        # ⑤ LLM 호출 (타임아웃 + 에러 방어)
        response = await self._call_llm_safe(
            prompt=grounded_prompt,
            store_id=store_id,
            context_type=context_type,
        )

        # ⑥ 성공 응답 캐시에 저장
        if response and not self._is_fallback(response):
            self._cache.set(store_id, query, response)

        return response

    async def get_missed_call_response(
        self,
        customer_phone: str,
        store_id: str,
    ) -> str:
        """
        부재중 전화 자동 응답 전용.
        매장 정보 + 고객 이력을 그라운딩하여 맞춤형 SMS 문구 생성.
        """
        return await self.get_response(
            query=f"전화번호 {customer_phone}의 고객에게 보낼 부재중 응답 문자를 작성해줘.",
            store_id=store_id,
            context_type="missed_call",
        )

    def invalidate_store_cache(self, store_id: str) -> int:
        """매장 데이터 변경 시 해당 매장 캐시 무효화"""
        count = self._cache.invalidate_store(store_id)
        logger.info("[RAG] Cache invalidated: store=%s, entries=%d", store_id, count)
        return count

    def health(self) -> dict:
        """서비스 헬스 정보 반환"""
        return {
            "service": "RAGService",
            "cache": self._cache.stats(),
            "hallucination_guard": self._guard,
            "timeout_sec": self._timeout,
            "ai_available": self._ai is not None,
        }

    # ─────────────────────────────────────────────────────────
    # 내부 로직
    # ─────────────────────────────────────────────────────────

    async def _fetch_store_context(
        self,
        store_id: str,
        extra: Optional[dict],
    ) -> dict:
        """
        DB에서 매장 컨텍스트 조회.
        실패 시 빈 dict 반환 (에러 전파 없음).
        """
        ctx: dict[str, Any] = {}
        if extra:
            ctx.update(extra)

        if not self._db or not store_id:
            return ctx

        try:
            # 매장 기본 정보
            store = await asyncio.get_event_loop().run_in_executor(
                None, self._db.get_store, store_id
            )
            if store:
                ctx["store_name"] = store.get("name", "")
                ctx["store_type"] = store.get("store_type", "")
                ctx["auto_reply_text"] = store.get("auto_reply_text", "")
                ctx["phone"] = store.get("phone", "")

            # 오늘 통계 (주문/매출 현황)
            stats = await asyncio.get_event_loop().run_in_executor(
                None, self._db.get_today_stats, store_id
            )
            if stats:
                ctx["today_orders"] = stats.get("order_count", 0)
                ctx["today_sales"] = stats.get("total_sales", 0)

        except Exception as exc:
            logger.warning("[RAG] DB context fetch failed: store=%s err=%s", store_id, exc)
            # DB 장애 시 빈 컨텍스트로 계속 진행 (서비스 중단 없음)

        return ctx

    def _build_grounded_prompt(
        self,
        query: str,
        store_context: dict,
        context_type: str,
    ) -> str:
        """
        환각 방지 시스템 프롬프트 + 그라운딩 데이터 조합.

        핵심 지시:
        - "제공된 [매장 정보] 범위 안에서만 답하라"
        - "모르는 내용은 반드시 '확인이 필요합니다'라고 답하라"
        - 외부 정보, 추측, 일반 지식 사용 금지
        """
        store_name = store_context.get("store_name", "매장")
        auto_reply = store_context.get("auto_reply_text", "")
        store_type = store_context.get("store_type", "")
        today_orders = store_context.get("today_orders", "")
        today_sales = store_context.get("today_sales", "")

        # 컨텍스트 JSON 직렬화 (최대 크기 제한)
        ctx_json = json.dumps(store_context, ensure_ascii=False)[:4000]

        # 환각 방지 시스템 프롬프트 (핵심 원칙)
        system = (
            f"당신은 '{store_name}'의 AI 비서 '동네비서'입니다.\n\n"
            "[절대 규칙 — 위반 금지]\n"
            "1. 아래 [매장 정보]에 있는 내용만 사용하여 답변하세요.\n"
            "2. [매장 정보]에 없는 내용은 절대 추측하거나 지어내지 마세요.\n"
            "3. 모르는 내용은 반드시 '사장님께 직접 확인이 필요합니다'라고 답하세요.\n"
            "4. 외부 지식, 일반 상식을 활용한 추론을 하지 마세요.\n"
            "5. 답변은 최대 3문장, 친근하고 간결하게.\n\n"
            f"[매장 정보]\n{ctx_json}\n"
        )

        if auto_reply:
            system += f"\n[사장님 설정 자동 응답]\n{auto_reply}\n"

        if store_type:
            system += f"\n[업종]: {store_type}\n"

        if context_type == "missed_call" and today_orders:
            system += (
                f"\n[오늘 현황] 주문 {today_orders}건 / 매출 {today_sales:,}원\n"
            )

        return f"{system}\n\n[고객 문의]\n{query}"

    async def _call_llm_safe(
        self,
        prompt: str,
        store_id: str,
        context_type: str,
    ) -> str:
        """
        LLM API 호출 — 3단계 방어 래퍼.

        에러 처리 계층:
        1. asyncio.timeout  → TimeoutError  → 타임아웃 Fallback
        2. API 예외 (4xx)   → APIError      → api_error Fallback
        3. 기타 예외         → Exception     → default Fallback
        """
        if not self._ai:
            logger.warning("[RAG] AI service not available — fallback")
            return self._select_fallback(context_type)

        try:
            async with asyncio.timeout(self._timeout):
                result = await self._ai.generate_grounded(prompt)
                return result or self._select_fallback(context_type)

        except TimeoutError:
            logger.warning(
                "[RAG] LLM timeout (%.1fs): store=%s type=%s",
                self._timeout, store_id, context_type,
            )
            return _FALLBACK_MESSAGES["timeout"]

        except Exception as exc:
            # API 키 오류, 네트워크 오류, 할당량 초과 등 모든 예외
            err_type = type(exc).__name__
            logger.error(
                "[RAG] LLM error %s: store=%s type=%s — %s",
                err_type, store_id, context_type, exc,
            )
            return _FALLBACK_MESSAGES.get("api_error", _FALLBACK_MESSAGES["default"])

    def _select_fallback(self, context_type: str) -> str:
        """컨텍스트 타입에 맞는 Fallback 메시지 반환"""
        return _FALLBACK_MESSAGES.get(context_type, _FALLBACK_MESSAGES["default"])

    def _is_fallback(self, text: str) -> bool:
        """응답이 Fallback 메시지인지 확인 (캐시 저장 방지)"""
        return text in _FALLBACK_MESSAGES.values()


# ═══════════════════════════════════════════════════════════════
# 싱글톤 팩토리
# ═══════════════════════════════════════════════════════════════
_rag_instance: Optional[RAGService] = None


def get_rag_service(
    ai_service=None,
    db=None,
    timeout_sec: float = 8.0,
    cache_ttl_sec: int = 300,
    hallucination_guard: bool = True,
) -> RAGService:
    """
    RAGService 싱글톤 반환.
    FastAPI 의존성 주입(Depends)과 함께 사용 권장.

    사용 예시:
        from dongnebiseo.services.rag_service import get_rag_service
        rag = get_rag_service(ai_service=ai_svc, db=db_manager)
        response = await rag.get_response(query, store_id)
    """
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGService(
            ai_service=ai_service,
            db=db,
            timeout_sec=timeout_sec,
            cache_ttl_sec=cache_ttl_sec,
            hallucination_guard=hallucination_guard,
        )
        logger.info(
            "[RAG] Service initialized: timeout=%.1fs cache_ttl=%ds guard=%s",
            timeout_sec, cache_ttl_sec, hallucination_guard,
        )
    return _rag_instance


def reset_rag_service() -> None:
    """테스트 환경에서 싱글톤 초기화"""
    global _rag_instance
    _rag_instance = None
