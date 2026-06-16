import psycopg2
import psycopg2.extras
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
import db_backend as db_postgres

router = APIRouter()

# ---------------------------------------------------------
# [1구역] 로젠택배 API 통신 모듈 (어댑터)
# 나중에 매뉴얼과 인증 키가 오면 이 부분의 코드만 덮어씌웁니다.
# ---------------------------------------------------------
def request_rosen_waybill(order_id: str, address: str, item_type: str):
    # TODO: 실제 로젠택배 API 연동 규격에 맞춰 송장 발급 로직을 작성합니다.
    print(f"[{order_id}] 로젠택배 서버로 운송장 요청 전송 (주소: {address}, 품목: {item_type})")


class IssueWaybillRequest(BaseModel):
    order_id: str


@router.post("/api/admin/market/issue-waybill")
def issue_waybill(req: IssueWaybillRequest, background_tasks: BackgroundTasks):
    order_id = req.order_id
    
    # 1. PostgreSQL 커넥션 획득
    conn = db_postgres.get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="데이터베이스 연결에 실패했습니다.")
        
    try:
        # 2. 수동 트랜잭션 제어를 위해 autocommit을 False로 설정
        conn.autocommit = False
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # 3. 무결성 방어 (FOR UPDATE 필수)
        # SELECT * FROM market_orders WHERE order_id = %s FOR UPDATE
        cur.execute("SELECT * FROM market_orders WHERE order_id = %s FOR UPDATE", (order_id,))
        order = cur.fetchone()
        
        if not order:
            conn.rollback()
            raise HTTPException(status_code=404, detail="존재하지 않는 주문번호입니다.")
            
        current_status = order.get("current_status")
        
        # 4. 상태 검증: 오직 'PAID' 상태일 때만 'PENDING(송장대기)' 상태로 전환 가능
        if current_status != 'PAID':
            conn.rollback()
            raise HTTPException(
                status_code=400, 
                detail=f"송장 대기 상태로 변경할 수 없는 주문입니다. 현재 상태: {current_status}"
            )
            
        # 5. 주문 상태 'PENDING'으로 변경 (UPDATE)
        cur.execute(
            """
            UPDATE market_orders 
            SET current_status = 'PENDING', updated_at = CURRENT_TIMESTAMP 
            WHERE order_id = %s
            """,
            (order_id,)
        )
        
        # 6. 이력 테이블 동시 기록 (INSERT)
        cur.execute(
            """
            INSERT INTO order_status_history (order_id, changed_status, reason, worker_identity)
            VALUES (%s, 'PENDING', '송장 발급 프로세스 시작', 'ADMIN')
            """,
            (order_id,)
        )
        
        # 7. 트랜잭션 커밋 (Atomicity 보장)
        conn.commit()
        
        # 8. 백그라운드 태스크 등록을 위한 데이터 추출
        base_address = order.get("base_address", "")
        detail_address = order.get("detail_address", "")
        full_address = f"{base_address} {detail_address}".strip()
        product_name = order.get("product_name", "")
        
        # 9. 백그라운드에서 비동기 로젠 API 호출 수행
        background_tasks.add_task(
            request_rosen_waybill,
            order_id=order_id,
            address=full_address,
            item_type=product_name
        )
        
        return {"status": "success", "message": "송장 발급 요청이 시작되었습니다."}
        
    except HTTPException:
        # FastAPI 예외는 이미 롤백이 되었거나, 예외를 그대로 상위로 전파
        raise
    except Exception as e:
        # 작업 도중 에러가 나면 롤백 처리
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"데이터베이스 트랜잭션 오류: {str(e)}")
    finally:
        conn.close()
