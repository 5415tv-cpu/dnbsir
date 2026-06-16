from fastapi import APIRouter, Query
import db_manager as db
import ai_manager
import json

router = APIRouter()

@router.get("/api/search")
async def search_products(q: str = Query(..., min_length=1)):
    """
    Highly Available Search (Redundant Routing)
    Primary: AI Semantic Search
    Backup: DB Keyword Search
    """
    all_products = db.get_all_products()
    
    # 1. Primary Node: AI Semantic Search
    try:
        model = ai_manager.get_gemini_client('gemini-3.1-pro')
        if model:
            product_list_str = json.dumps([{"id": p.get("product_id"), "name": p.get("name")} for p in all_products], ensure_ascii=False)
            prompt = f"사용자의 검색어 '{q}'에 부합하거나 의미가 유사한 상품의 ID 목록을 숫자 배열(JSON format)로만 반환해. 관련 상품이 없으면 빈 배열 []만 반환해. 부가 설명 절대 금지.\n상품목록: {product_list_str}"
            
            response = model.generate_content(prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            
            try:
                matched_ids = json.loads(text)
                if isinstance(matched_ids, list):
                    # Filter products by matched IDs
                    result = [p for p in all_products if p.get("product_id") in matched_ids]
                    return {"success": True, "source": "ai_primary", "data": result}
            except json.JSONDecodeError:
                print(f"[Search API] Failed to parse AI response: {text}")
                # Fall through to backup
    except Exception as e:
        print(f"[Search API] AI Search failed: {e}. Falling back to DB search.")

    # 2. Backup Node: Basic Keyword/DB Search
    try:
        q_lower = q.lower()
        result = [p for p in all_products if q_lower in str(p.get("name", "")).lower()]
        return {"success": True, "source": "db_backup", "data": result}
    except Exception as e:
        print(f"[Search API] DB Search failed: {e}")
        return {"success": False, "error": "All search nodes failed."}


@router.get("/api/track")
async def track_waybill(carrier_id: str = Query(..., description="Carrier ID"), track_id: str = Query(..., description="Tracking Number")):
    """
    Get real-time tracking logs for any carrier using tracker.delivery
    """
    import urllib.request
    import urllib.error
    import json
    url = f"https://apis.tracker.delivery/carriers/{carrier_id}/tracks/{track_id}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            return {"success": True, "source": "tracker.delivery", "data": data}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"success": False, "error_code": 404, "message": "해당 운송장 번호의 배송 정보가 존재하지 않거나 조회가 만료되었습니다."}
        return {"success": False, "error_code": e.code, "message": f"택배사 시스템 통신 실패 (상태코드: {e.code})"}
    except Exception as e:
        return {"success": False, "error_code": 500, "message": f"배송 정보 가져오기 실패: {str(e)}"}

