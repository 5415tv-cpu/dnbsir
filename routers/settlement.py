# routers/settlement.py
# 정산 API 라우터 - 마스터/매장 관리자용
from fastapi import APIRouter, Request, HTTPException, Cookie
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from typing import Optional, Union
from logger import logger
import settlement_db as sdb

router = APIRouter(prefix="/api/settlement", tags=["Settlement"])

MASTER_IDS = {"master", "010-2384-7447", "01023847447"}


def _get_session(cookie_store_id: str) -> str:
    if not cookie_store_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    return cookie_store_id


# ── 요청 스키마 ──
class SettlementCreateRequest(BaseModel):
    order_id:     str
    store_id:     str
    role_type:    str = "BUSINESS"   # BUSINESS / FARMER / CITIZEN
    total_amount: int
    platform_fee: int = 0
    service_fee:  int = 0
    memo:         str = ""

    @field_validator("total_amount", "platform_fee", "service_fee")
    @classmethod
    def must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError("금액은 음수일 수 없습니다.")
        return v

    @field_validator("role_type")
    @classmethod
    def valid_role(cls, v):
        if v not in {"BUSINESS", "FARMER", "CITIZEN"}:
            raise ValueError("role_type은 BUSINESS, FARMER, CITIZEN 중 하나여야 합니다.")
        return v


class StatusTransitionRequest(BaseModel):
    new_status: str   # APPROVED / COMPLETED / FAILED

    @field_validator("new_status")
    @classmethod
    def valid_status(cls, v):
        if v not in {"APPROVED", "COMPLETED", "FAILED"}:
            raise ValueError("new_status는 APPROVED, COMPLETED, FAILED 중 하나여야 합니다.")
        return v


class AdjustmentRequest(BaseModel):
    adj_amount: int    # 양수=추가, 음수=차감
    reason: str

    @field_validator("reason")
    @classmethod
    def reason_required(cls, v):
        if not v.strip():
            raise ValueError("조정 사유는 필수입니다.")
        return v


# ══════════════════════════════════════
# 정산 생성 (마스터 전용)
# ══════════════════════════════════════
@router.post("/create")
async def create_settlement(
    data: SettlementCreateRequest,
    cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")
):
    """새 정산 레코드 생성 (마스터 전용)"""
    if cookie_store_id not in MASTER_IDS:
        raise HTTPException(status_code=403, detail="마스터 권한이 필요합니다.")

    result = sdb.create_settlement(
        order_id=data.order_id,
        store_id=data.store_id,
        role_type=data.role_type,
        total_amount=data.total_amount,
        platform_fee=data.platform_fee,
        service_fee=data.service_fee,
        memo=data.memo,
    )
    if not result:
        raise HTTPException(status_code=400, detail="정산 생성 실패 (net_amount 음수 또는 무결성 오류)")

    logger.info(f"정산 생성 API | by={cookie_store_id} | settle={result['settlement_id']}")
    return {"success": True, "settlement": result}


# ══════════════════════════════════════
# 상태 전이 (마스터 전용)
# ══════════════════════════════════════
@router.post("/{settlement_id}/status")
async def change_settlement_status(
    settlement_id: int,
    data: StatusTransitionRequest,
    cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")
):
    """
    정산 상태 변경 (State Machine).
    READY→APPROVED→COMPLETED 또는 →FAILED
    """
    if cookie_store_id not in MASTER_IDS:
        raise HTTPException(status_code=403, detail="마스터 권한이 필요합니다.")

    ok, msg = sdb.transition_settlement(
        settlement_id=settlement_id,
        new_status=data.new_status,
        processed_by=cookie_store_id
    )
    if not ok:
        raise HTTPException(status_code=409, detail=msg)

    return {"success": True, "message": msg}


# ══════════════════════════════════════
# 금액 조정 내역 추가 (마스터 전용)
# ══════════════════════════════════════
@router.post("/{settlement_id}/adjust")
async def adjust_settlement(
    settlement_id: int,
    data: AdjustmentRequest,
    cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")
):
    """
    정산 금액 조정 (불변성: 기존 행 UPDATE 금지 → 새 행 INSERT).
    세무 감사 대비 모든 조정 내역 영구 보관.
    """
    if cookie_store_id not in MASTER_IDS:
        raise HTTPException(status_code=403, detail="마스터 권한이 필요합니다.")

    ok = sdb.add_settlement_adjustment(
        settlement_id=settlement_id,
        store_id=cookie_store_id,
        adj_amount=data.adj_amount,
        reason=data.reason,
        created_by=cookie_store_id
    )
    if not ok:
        raise HTTPException(status_code=400, detail="조정 내역 저장 실패")

    return {"success": True, "message": f"{data.adj_amount:+,}원 조정 완료"}


# ══════════════════════════════════════
# 조회 API
# ══════════════════════════════════════
@router.get("/my")
async def get_my_settlements(
    status: Optional[str] = None,
    cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")
):
    """내 매장 정산 목록 조회 (로그인한 사장님/농어민)"""
    _get_session(cookie_store_id)
    result = sdb.get_store_settlements(cookie_store_id, status=status)
    return {"settlements": result, "count": len(result)}


@router.get("/my/summary")
async def get_my_summary(
    cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")
):
    """내 매장 정산 현황 요약"""
    _get_session(cookie_store_id)
    return sdb.get_settlement_summary(cookie_store_id)


@router.get("/admin/all")
async def get_all_settlements(
    status: Optional[str] = None,
    role_type: Optional[str] = None,
    limit: int = 100,
    cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")
):
    """전체 정산 목록 (마스터 전용)"""
    if cookie_store_id not in MASTER_IDS:
        raise HTTPException(status_code=403, detail="마스터 권한이 필요합니다.")
    result = sdb.get_all_settlements_admin(status=status, role_type=role_type, limit=limit)
    return {"settlements": result, "count": len(result)}


@router.get("/{settlement_id}")
async def get_settlement_detail(
    settlement_id: int,
    cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")
):
    """정산 단건 + 조정 이력 조회"""
    _get_session(cookie_store_id)
    s = sdb.get_settlement(settlement_id)
    if not s:
        raise HTTPException(status_code=404, detail="정산 정보를 찾을 수 없습니다.")
    # 마스터 또는 본인 매장만 조회 가능
    if cookie_store_id not in MASTER_IDS and s["store_id"] != cookie_store_id:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")
    adjustments = sdb.get_settlement_adjustments(settlement_id)
    return {"settlement": s, "adjustments": adjustments}
