from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import db_manager as db

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/market", response_class=HTMLResponse)
async def market_page(request: Request):
    products = db.get_all_products()
    return templates.TemplateResponse("market.html", {"request": request, "products": products})

class MarketOrderRequest(BaseModel):
    product_id: int
    name: str
    phone: str
    address: str

@router.post("/api/market/order")
async def create_market_order(order: MarketOrderRequest):
    product = db.get_product_detail(order.product_id)
    if not product:
        return {"success": False, "error": "상품 정보를 찾을 수 없습니다."}
        
    store_id = product.get('store_id', 'unknown')
    price = product.get('price', 0)
    product_name = product.get('name', 'Unknown Product')

    success, msg = db.decrease_product_inventory(order.product_id, 1)
    
    if not success:
        return {"success": False, "error": msg}
        
    db.save_order(store_id, order.product_id, product_name, price, 1, order.name, order.phone, order.address)
    print(f"New Order Saved: {order.name}, {product_name}, {price}")
    
    return {"success": True}
