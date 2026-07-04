"""
dongnebiseo_app/services/ai_service.py
AI service layer - ai_manager.py refactored
"""
from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
from typing import Optional

import google.generativeai as genai
from pydantic import BaseModel, Field

from dongnebiseo_app.config.settings import get_settings

logger = logging.getLogger(__name__)


# Pydantic schema
class CallSummarySchema(BaseModel):
    name: str = Field(description="고객 이름 (모르면 이름 미상)")
    intent: str = Field(description="예약, 주문, 단순문의, 불만접수 중 1개")
    summary: str = Field(description="구체적인 통화 요건 1~2줄 요약")
    event_type: Optional[str] = Field(default=None, description="결혼, 상가, 생일, 방문약속 중 1개")
    event_details: Optional[str] = Field(default=None, description="이벤트 날짜와 상세 내용")


# Role-based tools
def _get_current_time() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _get_store_orders_stat(store_id: str) -> str:
    try:
        import db_manager as db
        days = 7
        df = db.get_orders(store_id, days)
        if df is None or (hasattr(df, "empty") and df.empty):
            return "최근 7일간 주문 내역이 없습니다."
        total_sales = df["amount"].sum()
        order_count = len(df)
        return f"최근 {days}일간 총 {order_count}건의 주문이 있으며, 매출액은 {total_sales:,}원 입니다."
    except Exception as e:
        logger.warning("[AI] get_store_orders_stat failed: %s", e)
        return "주문 통계 조회에 실패했습니다."


def _read_file_content(file_path: str) -> str:
    if ".." in file_path or file_path.startswith("/"):
        return "보안상 허용되지 않는 경로입니다."
    try:
        if not os.path.exists(file_path):
            return "파일을 찾을 수 없습니다."
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"파일 읽기 오류: {e}"


_ADMIN_TOOLS = [_get_current_time, _get_store_orders_stat, _read_file_content]
_CUSTOMER_TOOLS = [_get_current_time]


class AIService:
    """Google Gemini API client service."""

    def __init__(self):
        self._cfg = get_settings()
        self._api_key = self._cfg.app.gemini_api_key
        self._initialized = False
        self._init_client()

    def _init_client(self) -> None:
        if not self._api_key:
            logger.warning("[AI] GOOGLE_API_KEY not set — AI service disabled")
            return
        try:
            genai.configure(api_key=self._api_key)
            self._initialized = True
            logger.info("[AI] Gemini client initialized")
        except Exception as e:
            logger.error("[AI] Gemini init failed: %s", e)

    def _get_model(self, model_name: str, tool_set: str = "customer"):
        if not self._initialized:
            return None
        try:
            tools = _ADMIN_TOOLS if tool_set == "admin" else _CUSTOMER_TOOLS
            return genai.GenerativeModel(model_name, tools=tools)
        except Exception as e:
            logger.error("[AI] Model creation failed: %s", e)
            return None

    def _route_model(self, query: str) -> str:
        cfg = self._cfg.app
        if not query:
            return cfg.gemini_model_pro
        if len(query) > 100:
            return cfg.gemini_model_pro
        complex_kw = ["분석", "비교", "이유", "해결", "기획", "작성", "요약", "설명"]
        if any(kw in query for kw in complex_kw):
            return cfg.gemini_model_pro
        return cfg.gemini_model_flash

    async def generate_grounded(self, grounded_prompt: str) -> str:
        """RAGService interface - grounded generation."""
        if not self._initialized:
            return ""
        try:
            model = genai.GenerativeModel(self._cfg.app.gemini_model_flash)
            gen_cfg = genai.types.GenerationConfig(
                max_output_tokens=self._cfg.app.ai_max_output_tokens,
                temperature=self._cfg.app.ai_temperature,
            )
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: model.generate_content(grounded_prompt, generation_config=gen_cfg),
            )
            return response.text.strip() if response.text else ""
        except Exception as e:
            logger.error("[AI] generate_grounded error: %s", e)
            return ""

    def get_ai_response(self, user_input, chat_history=None, system_prompt=None, tool_set="customer") -> dict:
        """Legacy ai_manager.get_ai_response() compatible."""
        cfg = self._cfg.app
        model_name = self._route_model(user_input)
        model = self._get_model(model_name, tool_set=tool_set)
        if not model:
            return {
                "text": "죄송합니다. 현재 AI 시스템이 오프라인 상태입니다. 잠시 후 다시 시도해 주세요.",
                "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            }
        sp = system_prompt or "당신은 동네비서 AI 상담원입니다."
        full_prompt = f"{sp}\n\n사용자: {user_input}"
        try:
            gen_cfg = genai.types.GenerationConfig(
                max_output_tokens=cfg.ai_max_output_tokens,
                temperature=cfg.ai_temperature,
            )
            chat = model.start_chat(enable_automatic_function_calling=True)
            response = chat.send_message(full_prompt, generation_config=gen_cfg)
            text = response.text.strip()
            try:
                usage = {
                    "input_tokens": response.usage_metadata.prompt_token_count,
                    "output_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count,
                }
            except Exception:
                usage = {
                    "input_tokens": len(full_prompt) // 4,
                    "output_tokens": len(text) // 4,
                    "total_tokens": (len(full_prompt) + len(text)) // 4,
                }
            return {"text": text, "usage": usage}
        except Exception as e:
            logger.error("[AI] get_ai_response error: %s", e)
            return {
                "text": "죄송합니다. 오류가 발생했습니다.",
                "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            }

    def classify_store_type(self, store_name: str) -> str:
        if not self._initialized:
            return "기타 일반사업자"
        try:
            model = genai.GenerativeModel(self._cfg.app.gemini_model_flash)
            prompt = f"상호명 '{store_name}'을 분석하여 '식당', '편의점', '택배/물류', '카페', '미용실', '기타' 중 하나로만 대답해줘."
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            return "기타 일반사업자"

    async def parse_call_audio(self, audio_url: str) -> str:
        await asyncio.sleep(1.5)
        return (
            "AI: 안녕하세요, 동네비서입니다. 사장님이 부재중이시라 AI 비서가 대신 전화를 받았습니다.\n"
            "고객: 다음 주 토요일 피로연 예약 좀 하려고요.\n"
            "AI: 예약 인원과 시간, 성함을 알려주시면 전달해 드리겠습니다."
        )

    async def summarize_call_text(self, transcript: str, store_id: str = "UNKNOWN", customer_phone: str = "UNKNOWN") -> dict:
        prompt = f"다음 통화 스크립트를 분석하여 요약해주세요.\n\n{transcript}"
        try:
            if not self._initialized:
                raise RuntimeError("AI not initialized")
            model = genai.GenerativeModel(self._cfg.app.gemini_model_pro)
            gen_cfg = genai.types.GenerationConfig(
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=CallSummarySchema,
            )
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: model.generate_content(prompt, generation_config=gen_cfg),
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error("[AI] summarize_call_text error: store=%s err=%s", store_id, e)
            return {"name": "이름 미상", "event_details": None}

    async def draft_courier_greeting_message(self, customer_phone: str) -> str:
        cfg = self._cfg.app
        base_url = cfg.app_base_url.rstrip("/")
        booking_link = f"{base_url}/citizen/courier"
        tracking_link = "https://www.ilogen.com/web/personal/tkSearch"
        fallback = f"[동네비서 AI]\n통화량이 많습니다.\n택배예약: {booking_link}\n화물추적: {tracking_link}"

        tracking_info = "최근 택배 예약 이력이 없습니다."
        try:
            import sqlite3, pandas as pd
            conn = sqlite3.connect("database.db", check_same_thread=False)
            df = pd.read_sql(
                "SELECT tracking_code, created_at FROM courier_requests WHERE sender_phone=? ORDER BY created_at DESC LIMIT 1",
                conn, params=(customer_phone,),
            )
            conn.close()
            if not df.empty and pd.notnull(df.iloc[0]["tracking_code"]):
                tracking_info = f"최근 발송 송장번호: {df.iloc[0]['tracking_code']}"
        except Exception as e:
            logger.debug("[AI] courier history fetch failed: %s", e)

        prompt = (
            f"당신은 동네비서 AI 상담사입니다. 고객({customer_phone})이 전화를 걸었습니다.\n"
            f"[과거 기록]\n{tracking_info}\n\n"
            f"친절하고 짧게, 고객이 바로 답변할 수 있는 질문 한 문장을 만드세요.\n"
            f"반드시 링크를 제공하세요: 택배예약={booking_link} / 화물추적={tracking_link}"
        )
        if not self._initialized:
            return fallback
        try:
            model = genai.GenerativeModel(self._cfg.app.gemini_model_flash)
            gen_cfg = genai.types.GenerationConfig(temperature=0.7, max_output_tokens=150)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: model.generate_content(prompt, generation_config=gen_cfg),
            )
            return response.text.strip()
        except Exception as e:
            logger.error("[AI] draft_courier_greeting error: %s", e)
            return fallback


_ai_instance: Optional[AIService] = None


def get_ai_service() -> AIService:
    global _ai_instance
    if _ai_instance is None:
        _ai_instance = AIService()
    return _ai_instance


# Legacy ai_manager.py drop-in adapters
def get_ai_response(user_input, chat_history=None, system_prompt=None, tool_set="customer"):
    return get_ai_service().get_ai_response(user_input, chat_history, system_prompt, tool_set)


def classify_store_type(store_name: str) -> str:
    return get_ai_service().classify_store_type(store_name)


async def parse_call_audio(audio_url: str) -> str:
    return await get_ai_service().parse_call_audio(audio_url)


async def summarize_call_text(transcript: str, store_id: str = "UNKNOWN", customer_phone: str = "UNKNOWN") -> dict:
    return await get_ai_service().summarize_call_text(transcript, store_id, customer_phone)


async def draft_courier_greeting_message(customer_phone: str) -> str:
    return await get_ai_service().draft_courier_greeting_message(customer_phone)