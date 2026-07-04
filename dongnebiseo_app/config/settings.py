"""
dongnebiseo/config/settings.py
================================
동네비서 시스템 설정 — Pydantic BaseSettings 기반

[역할 분리 원칙]
───────────────────────────────────────────────────
탄탄제작소 (TantanFabricationSettings)
  → 인프라 홀더의 시스템 루트 영역
  → DB, 서버 스펙, 클라우드 계정, 네트워크 등
  → 탄탄제작소 운영팀만 변경 가능

동네비서 (DongnebiseoAppSettings)
  → AI 서비스 브랜드 애플리케이션 영역
  → AI 프롬프트, 비즈니스 로직, UI 동작 등
  → 동네비서 개발팀이 변경
───────────────────────────────────────────────────

사용법:
    from dongnebiseo.config.settings import get_settings
    cfg = get_settings()
    db_url = cfg.tantan.database_url
    api_key = cfg.app.gemini_api_key
"""

from __future__ import annotations

import os
import functools
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


# ═══════════════════════════════════════════════════════════════
# 1. 탄탄제작소 영역 (Tantan Fabrication — Infrastructure)
#    시스템 루트 권한에 해당하는 인프라 설정
#    환경변수 prefix: TANTAN_
# ═══════════════════════════════════════════════════════════════
class TantanInfraSettings(BaseSettings):
    """
    탄탄제작소 인프라 설정.
    물리 서버, DB 클러스터, 클라우드 계정 등 루트 권한 영역.
    동네비서 앱 코드에서는 읽기 전용으로만 접근.
    """

    # ── 데이터베이스 클러스터 (한국 서버 기준) ──────────────────
    database_url: str = Field(
        default="sqlite:///./database.db",
        description="PostgreSQL DSN (운영) 또는 SQLite 경로 (로컬)"
    )
    db_host: str = Field(default="localhost", description="DB 호스트")
    db_port: int = Field(default=5432, description="DB 포트")
    db_name: str = Field(default="dnbsir", description="DB 이름")
    db_user: str = Field(default="dnbsir", description="DB 유저")
    db_password: str = Field(default="", description="DB 패스워드")
    db_pool_size: int = Field(default=10, description="커넥션 풀 크기")
    db_max_overflow: int = Field(default=20, description="최대 초과 커넥션")

    # ── 서버 / 네트워크 ──────────────────────────────────────────
    server_region: str = Field(
        default="kr-central1",
        description="서버 리전 (국내 서버 기준: kr-central1)"
    )
    allowed_hosts: list[str] = Field(
        default=["dongnebiseo.com", "api.dnbsir.com", "tantanfab.com"],
        description="허용 도메인 목록"
    )
    port: int = Field(default=8080, description="서버 포트")

    # ── 미디어 워커 연동 (탄탄제작소 GPU 서버) ───────────────────
    tantan_upload_secret: str = Field(
        default="",
        description="동네비서 ↔ 탄탄제작소 미디어 업로드 공유 시크릿"
    )
    tantan_gpu_api_url: str = Field(
        default="http://tantanfab.com/api/gpu",
        description="탄탄제작소 GPU 작업 API URL"
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Celery 태스크 큐 브로커 (탄탄제작소 인프라)"
    )

    # ── GCP / 클라우드 (탄탄제작소 클라우드 계정) ────────────────
    gcp_project_id: str = Field(default="", description="GCP 프로젝트 ID")
    gcp_region: str = Field(default="asia-northeast3", description="GCP 리전 (서울)")

    class Config:
        env_prefix = "TANTAN_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# ═══════════════════════════════════════════════════════════════
# 2. 동네비서 앱 영역 (Dongnebiseo App — Business Logic)
#    AI 서비스 브랜드의 애플리케이션 설정
#    환경변수 prefix: DNBSIR_  (또는 레거시: 직접 키명)
# ═══════════════════════════════════════════════════════════════
class DongnebiseoAppSettings(BaseSettings):
    """
    동네비서 앱 설정.
    AI 프롬프트, 비즈니스 규칙, 외부 API 키, UI 동작 등 앱 레이어 영역.
    탄탄제작소 인프라 설정(TantanInfraSettings)에 의존하지 않음.
    """

    # ── AI / LLM (Google Gemini) ─────────────────────────────────
    gemini_api_key: str = Field(
        default="",
        alias="GOOGLE_API_KEY",           # 레거시 키명 호환
        description="Google Gemini API 키"
    )
    gemini_model_pro: str = Field(
        default="gemini-2.5-pro",
        description="복잡한 쿼리용 Pro 모델"
    )
    gemini_model_flash: str = Field(
        default="gemini-2.5-flash",
        description="단순 쿼리용 Flash 모델 (지연 최소화)"
    )
    ai_max_output_tokens: int = Field(
        default=500,
        description="AI 응답 최대 토큰 수 (비용 제어)"
    )
    ai_temperature: float = Field(
        default=0.7,
        description="AI 응답 창의성 (0=결정론적, 1=창의적)"
    )
    ai_hallucination_guard: bool = Field(
        default=True,
        description="RAG 그라운딩 강제 활성화 (환각 방지 핵심 원칙)"
    )
    ai_timeout_sec: float = Field(
        default=8.0,
        description="외부 LLM API 타임아웃 (초) — 초과 시 즉시 로컬 Fallback"
    )
    ai_fallback_cache_ttl_sec: int = Field(
        default=300,
        description="로컬 Fallback 캐시 유효 시간 (초)"
    )

    # ── SMS / 알림톡 (Solapi) ─────────────────────────────────────
    solapi_api_key: str = Field(default="", alias="SOLAPI_API_KEY")
    solapi_api_secret: str = Field(default="", alias="SOLAPI_API_SECRET")
    solapi_sender_number: str = Field(
        default="",
        alias="SOLAPI_SENDER",
        description="발신 번호 (사전 등록 필요)"
    )

    # ── 결제 (Toss Payments) ──────────────────────────────────────
    toss_client_key: str = Field(default="", alias="TOSS_CLIENT_KEY")
    toss_secret_key: str = Field(default="", alias="TOSS_SECRET_KEY")

    # ── Webhook 보안 토큰 ─────────────────────────────────────────
    webhook_token: str = Field(
        default="",
        alias="WEBHOOK_SECRET_TOKEN",
        description="부재중 전화 웹훅 검증 토큰"
    )

    # ── 앱 동작 설정 ──────────────────────────────────────────────
    app_base_url: str = Field(
        default="https://dongnebiseo.com",
        alias="APP_BASE_URL",
        description="서비스 기본 URL (SMS 링크 생성에 사용)"
    )
    debug_mode: bool = Field(
        default=False,
        description="디버그 모드 (운영 환경에서 반드시 False)"
    )
    kiosk_mode: bool = Field(
        default=True,
        description="키오스크 고정형 UI 모드 (타깃 고객층 접근성 보장)"
    )

    # ── RAG / 그라운딩 설정 ───────────────────────────────────────
    rag_max_context_chars: int = Field(
        default=4000,
        description="RAG 컨텍스트 최대 문자 수 (프롬프트 인젝션 방지)"
    )
    rag_local_fallback_enabled: bool = Field(
        default=True,
        description="로컬 Fallback 활성화 (외부 API 장애 시 즉시 응답)"
    )

    # ── Google 연동 ───────────────────────────────────────────────
    google_sheet_credentials: str = Field(
        default="service_account.json",
        description="GCP 서비스 계정 키 파일 경로"
    )

    @field_validator("ai_timeout_sec")
    @classmethod
    def timeout_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("ai_timeout_sec must be positive")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        populate_by_name = True   # alias와 필드명 모두 허용
        case_sensitive = False
        extra = "ignore"


# ═══════════════════════════════════════════════════════════════
# 3. 통합 설정 객체 (읽기 전용 싱글톤)
# ═══════════════════════════════════════════════════════════════
class AppConfig:
    """
    탄탄제작소 인프라 + 동네비서 앱 설정의 통합 진입점.
    코드 레벨에서 인프라(tantan)와 비즈니스 로직(app)을 명확히 구분.

    사용 예시:
        from dongnebiseo.config.settings import get_settings
        cfg = get_settings()

        # 탄탄제작소 인프라 영역 접근
        db_url = cfg.tantan.database_url

        # 동네비서 앱 영역 접근
        api_key = cfg.app.gemini_api_key
    """
    def __init__(self):
        self.tantan = TantanInfraSettings()
        self.app = DongnebiseoAppSettings()

    def is_production(self) -> bool:
        """운영 환경 여부 (SQLite가 아닌 PostgreSQL 사용 시 운영으로 판단)"""
        return "postgresql" in self.tantan.database_url.lower()

    def get_legacy_secret(self, key: str, default: str = "") -> str:
        """
        레거시 config.get_secret() 호환 인터페이스.
        기존 코드의 점진적 마이그레이션을 지원.
        """
        return os.environ.get(key, default)


# ── 싱글톤 캐싱 (프로세스 당 1회만 설정 로드) ──────────────────
@functools.lru_cache(maxsize=1)
def get_settings() -> AppConfig:
    """
    설정 싱글톤 반환.
    환경변수 또는 .env 파일에서 자동 주입.
    """
    return AppConfig()


# ── 레거시 호환 헬퍼 (기존 config.get_secret 대체) ──────────────
def get_secret(key: str, default: str = "") -> str:
    """
    레거시 config.get_secret() 드롭인 대체 함수.
    기존 코드를 수정하지 않고 점진적으로 settings.py로 마이그레이션 가능.

    마이그레이션 가이드:
        # Before (레거시)
        import config
        key = config.get_secret("GOOGLE_API_KEY")

        # After (신규)
        from dongnebiseo.config.settings import get_settings
        key = get_settings().app.gemini_api_key
    """
    cfg = get_settings()
    return cfg.get_legacy_secret(key, default)
