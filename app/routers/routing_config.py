from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from auth import is_valid_csrf_for_request, require_manager
from database import get_db
from models import Product, Station
from services.routing_service import RoutingService
from template_utils import tmpl

router = APIRouter()


@router.get("/routing")
def routing_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_manager),
):
    products = db.query(Product).filter_by(is_active=True).all()
    stations = db.query(Station).order_by(Station.sequence).all()

    product_routing_ids = {}
    product_routing_stations = {}
    for p in products:
        routings = RoutingService(db).get_for_product(p.id)
        product_routing_ids[p.id] = [r.station_id for r in routings]
        product_routing_stations[p.id] = [r.station for r in routings]

    return tmpl(
        request, "routing.html",
        products=products,
        stations=stations,
        product_routing_ids=product_routing_ids,
        product_routing_stations=product_routing_stations,
    )


@router.get("/api/routing/{product_id}")
def get_routing(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(require_manager),
):
    routings = RoutingService(db).get_for_product(product_id)
    return [{"station_id": r.station_id, "sequence": r.sequence} for r in routings]


@router.post("/api/routing/{product_id}")
async def save_routing(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(require_manager),
):
    csrf_token = request.headers.get("x-csrf-token")
    if not is_valid_csrf_for_request(request, csrf_token):
        return JSONResponse({"error": "CSRF token invalid"}, status_code=403)

    body = await request.json()
    station_ids = body.get("station_ids", [])
    try:
        RoutingService(db).save(product_id, station_ids)
        return {"status": "ok"}
    except Exception as e:
        detail = e.detail if hasattr(e, "detail") else str(e)
        return JSONResponse({"error": detail}, status_code=400)