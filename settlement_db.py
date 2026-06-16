# settlement_db.py
# 동네비서 정산 시스템 전용 DB 모듈
# 원칙: 원자성(트랜잭션) / 정수형 금액 / 상태 머신 / 동시성 락
#
# 상태 흐름: READY → APPROVED → COMPLETED
#                         └──→ FAILED

import sqlite3
import os
import threading
from datetime import datetime
from logger import logger

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db", "settlements.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ── 동시성 보호: 프로세스 수준 Lock (SQLite 전체 락 보완) ──
_settlement_lock = threading.Lock()

# ── 허용된 상태 전이 (State Machine) ──
VALID_TRANSITIONS = {
    "READY":     {"APPROVED", "FAILED"},
    "APPROVED":  {"COMPLETED", "FAILED"},
    "COMPLETED": set(),   # 완료 후 변경 불가 (불변성)
    "FAILED":    set(),   # 실패 후 변경 불가
}


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # WAL 모드: 읽기/쓰기 동시 지원
    conn.execute("PRAGMA foreign_keys=ON")    # 외래 키 무결성 활성화
    return conn


# ══════════════════════════════════════════
# 1. 테이블 초기화
# ══════════════════════════════════════════
def init_settlement_tables():
    """정산 관련 테이블 생성 (서버 시작 시 1회 실행)"""
    conn = get_conn()
    try:
        conn.executescript("""
        -- 정산 마스터 테이블
        CREATE TABLE IF NOT EXISTS settlements (
            settlement_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id        TEXT NOT NULL,
            store_id        TEXT NOT NULL,                  -- 기존 stores 테이블의 store_id
            role_type       TEXT NOT NULL DEFAULT 'BUSINESS',  -- BUSINESS / FARMER / CITIZEN
            total_amount    INTEGER NOT NULL,               -- 원천 판매 금액 (원화 정수)
            platform_fee    INTEGER NOT NULL DEFAULT 0,     -- 외부 플랫폼 수수료 (네이버 등)
            service_fee     INTEGER NOT NULL DEFAULT 0,     -- 동네비서 자체 수수료
            net_amount      INTEGER NOT NULL,               -- 최종 정산액 = total - platform_fee - service_fee
            status          TEXT NOT NULL DEFAULT 'READY',  -- READY / APPROVED / COMPLETED / FAILED
            memo            TEXT DEFAULT '',               -- 메모 (관리자용)
            created_at      TEXT DEFAULT (datetime('now','localtime')),
            approved_at     TEXT,                          -- APPROVED 전환 일시
            completed_at    TEXT,                          -- COMPLETED 전환 일시
            processed_by    TEXT DEFAULT '',               -- 처리한 관리자 store_id
            CONSTRAINT valid_status CHECK (status IN ('READY','APPROVED','COMPLETED','FAILED')),
            CONSTRAINT positive_net CHECK (net_amount >= 0),
            CONSTRAINT positive_total CHECK (total_amount > 0)
        );

        -- 정산 이력 테이블 (불변성 보장: 금액 수정 시 새 행 INSERT)
        CREATE TABLE IF NOT EXISTS settlement_adjustments (
            adj_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            settlement_id   INTEGER NOT NULL,
            store_id        TEXT NOT NULL,
            adj_amount      INTEGER NOT NULL,              -- 음수(-) = 차감, 양수(+) = 추가
            reason          TEXT NOT NULL,                 -- 조정 사유 (세무 감사 대비)
            created_at      TEXT DEFAULT (datetime('now','localtime')),
            created_by      TEXT DEFAULT '',
            FOREIGN KEY (settlement_id) REFERENCES settlements(settlement_id)
        );

        -- 인덱스 (조회 성능)
        CREATE INDEX IF NOT EXISTS idx_settlements_store   ON settlements(store_id);
        CREATE INDEX IF NOT EXISTS idx_settlements_status  ON settlements(status);
        CREATE INDEX IF NOT EXISTS idx_settlements_order   ON settlements(order_id);
        CREATE INDEX IF NOT EXISTS idx_adj_settlement      ON settlement_adjustments(settlement_id);
        """)
        conn.commit()
        logger.info("정산 테이블 초기화 완료")
    except Exception as e:
        logger.error(f"정산 테이블 초기화 실패: {e}")
        raise
    finally:
        conn.close()


# ══════════════════════════════════════════
# 2. 정산 생성 (트랜잭션 보장)
# ══════════════════════════════════════════
def create_settlement(
    order_id: str,
    store_id: str,
    role_type: str,
    total_amount: int,
    platform_fee: int = 0,
    service_fee: int = 0,
    memo: str = ""
) -> dict | None:
    """
    새 정산 레코드 생성.
    - 원자성: 단일 트랜잭션 내에서 처리
    - 정수형: 모든 금액 파라미터는 int (원화)
    - net_amount는 서버에서 계산하여 고정 저장 (Snapshot)
    """
    net_amount = total_amount - platform_fee - service_fee
    if net_amount < 0:
        logger.warning(f"정산 생성 거부: net_amount 음수 | order={order_id} store={store_id}")
        return None

    conn = get_conn()
    try:
        with conn:  # context manager → 예외 시 자동 ROLLBACK
            cur = conn.execute("""
                INSERT INTO settlements
                    (order_id, store_id, role_type, total_amount,
                     platform_fee, service_fee, net_amount, memo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (order_id, store_id, role_type,
                  total_amount, platform_fee, service_fee, net_amount, memo))
            settlement_id = cur.lastrowid
            logger.info(
                f"정산 생성 | id={settlement_id} order={order_id} "
                f"store={store_id} net={net_amount:,}원"
            )
            return get_settlement(settlement_id, _conn=conn)
    except sqlite3.IntegrityError as e:
        logger.error(f"정산 생성 무결성 오류 | order={order_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"정산 생성 실패 | order={order_id}: {e}")
        return None
    finally:
        conn.close()


# ══════════════════════════════════════════
# 3. 상태 전이 (State Machine + 동시성 락)
# ══════════════════════════════════════════
def transition_settlement(
    settlement_id: int,
    new_status: str,
    processed_by: str = ""
) -> tuple[bool, str]:
    """
    정산 상태 변경.
    - State Machine: 허용된 전이만 실행
    - 동시성: threading.Lock + SQLite timeout으로 이중 차단
    - 불변성: COMPLETED/FAILED 상태는 변경 불가
    """
    with _settlement_lock:  # 스레드 수준 동시성 보호
        conn = get_conn()
        try:
            with conn:
                # 현재 상태 조회 (FOR UPDATE 역할: Lock 내에서 조회)
                row = conn.execute(
                    "SELECT status FROM settlements WHERE settlement_id = ?",
                    (settlement_id,)
                ).fetchone()

                if not row:
                    return False, "정산 레코드를 찾을 수 없습니다."

                current = row["status"]
                if new_status not in VALID_TRANSITIONS.get(current, set()):
                    return False, (
                        f"허용되지 않은 상태 전이: {current} → {new_status}. "
                        f"가능한 전이: {VALID_TRANSITIONS.get(current, set())}"
                    )

                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                time_field = ""
                if new_status == "APPROVED":
                    time_field = ", approved_at = ?"
                elif new_status == "COMPLETED":
                    time_field = ", completed_at = ?"

                sql = f"""
                    UPDATE settlements
                    SET status = ?, processed_by = ? {time_field}
                    WHERE settlement_id = ? AND status = ?
                """
                params = [new_status, processed_by]
                if time_field:
                    params.append(now)
                params += [settlement_id, current]

                affected = conn.execute(sql, params).rowcount
                if affected == 0:
                    # 다른 요청이 먼저 변경한 경우 (Race Condition 방어)
                    return False, "동시 처리 감지: 다른 요청이 이미 상태를 변경했습니다."

                logger.info(
                    f"정산 상태 전이 | id={settlement_id} "
                    f"{current} → {new_status} | by={processed_by}"
                )
                return True, f"{current} → {new_status} 전환 완료"

        except Exception as e:
            logger.error(f"정산 상태 전이 실패 | id={settlement_id}: {e}")
            return False, f"시스템 오류: {str(e)}"
        finally:
            conn.close()


# ══════════════════════════════════════════
# 4. 금액 조정 (불변성: INSERT 방식)
# ══════════════════════════════════════════
def add_settlement_adjustment(
    settlement_id: int,
    store_id: str,
    adj_amount: int,
    reason: str,
    created_by: str = ""
) -> bool:
    """
    정산 금액 조정 내역 추가.
    기존 행 UPDATE 대신 새 행 INSERT (세무 감사 추적 보장).
    adj_amount: 양수=추가, 음수=차감
    """
    if not reason.strip():
        logger.warning("정산 조정 거부: 사유 미입력")
        return False

    conn = get_conn()
    try:
        with conn:
            conn.execute("""
                INSERT INTO settlement_adjustments
                    (settlement_id, store_id, adj_amount, reason, created_by)
                VALUES (?, ?, ?, ?, ?)
            """, (settlement_id, store_id, adj_amount, reason, created_by))
            logger.info(
                f"정산 조정 추가 | settle={settlement_id} "
                f"금액={adj_amount:+,}원 | 사유={reason}"
            )
            return True
    except Exception as e:
        logger.error(f"정산 조정 실패 | settle={settlement_id}: {e}")
        return False
    finally:
        conn.close()


# ══════════════════════════════════════════
# 5. 조회 함수
# ══════════════════════════════════════════
def get_settlement(settlement_id: int, _conn=None) -> dict | None:
    """단건 조회"""
    close_after = _conn is None
    conn = _conn or get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM settlements WHERE settlement_id = ?",
            (settlement_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        if close_after:
            conn.close()


def get_store_settlements(store_id: str, status: str = None, limit: int = 50) -> list:
    """특정 매장의 정산 목록 조회 (선택적 상태 필터)"""
    conn = get_conn()
    try:
        if status:
            rows = conn.execute("""
                SELECT * FROM settlements
                WHERE store_id = ? AND status = ?
                ORDER BY created_at DESC LIMIT ?
            """, (store_id, status, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM settlements
                WHERE store_id = ?
                ORDER BY created_at DESC LIMIT ?
            """, (store_id, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_settlements_admin(status: str = None, role_type: str = None, limit: int = 100) -> list:
    """마스터 관리자용 전체 정산 목록"""
    conn = get_conn()
    try:
        filters, params = [], []
        if status:
            filters.append("status = ?")
            params.append(status)
        if role_type:
            filters.append("role_type = ?")
            params.append(role_type)
        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        params.append(limit)
        rows = conn.execute(f"""
            SELECT * FROM settlements
            {where}
            ORDER BY created_at DESC LIMIT ?
        """, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_settlement_adjustments(settlement_id: int) -> list:
    """특정 정산의 조정 이력 전체 조회"""
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT * FROM settlement_adjustments
            WHERE settlement_id = ?
            ORDER BY created_at ASC
        """, (settlement_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_settlement_summary(store_id: str) -> dict:
    """매장별 정산 요약 (상태별 건수 + 총액)"""
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT status,
                   COUNT(*)        AS cnt,
                   SUM(net_amount) AS total_net
            FROM settlements
            WHERE store_id = ?
            GROUP BY status
        """, (store_id,)).fetchall()
        return {r["status"]: {"count": r["cnt"], "total_net": r["total_net"] or 0}
                for r in rows}
    finally:
        conn.close()
