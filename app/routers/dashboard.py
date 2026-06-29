from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from database import get_db
from auth import require_manager, require_login
from models import WorkOrder, ProductionLog
from services.kpi_service import KpiService
from mqtt_listener import get_mqtt_feed
from template_utils import tmpl

router = APIRouter()


@router.get("/dashboard")
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_manager),
):
    wos = db.query(WorkOrder).order_by(WorkOrder.created_at.desc()).all()
    wo_list = _build_wo_list(db, wos)

    recent_cutoff = datetime.utcnow() - timedelta(hours=1)
    has_anomaly = db.query(ProductionLog).filter(
        ProductionLog.is_anomaly == True,
        ProductionLog.logged_at >= recent_cutoff,
    ).count() > 0

    return tmpl(request, "dashboard.html", wo_list=wo_list, has_anomaly=has_anomaly)


@router.get("/api/kpis")
def api_kpis(
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(require_manager),
):
    return KpiService(db).calculate_global()

@router.get("/api/workorders/cards")
def api_wo_cards(
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(require_manager),
):
    wos = db.query(WorkOrder).order_by(WorkOrder.created_at.desc()).all()
    return _build_wo_list(db, wos)


@router.get("/api/workorders/{wo_id}/chart")
def api_wo_chart(
    wo_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(require_login),
):
    from models import Station
    from sqlalchemy import func

    stations = db.query(Station).order_by(Station.sequence).all()
    labels, good, scrap = [], [], []
    for station in stations:
        g = db.query(func.sum(ProductionLog.qty_good)).filter_by(
            work_order_id=wo_id, station_id=station.id
        ).scalar() or 0
        s = db.query(func.sum(ProductionLog.qty_scrap)).filter_by(
            work_order_id=wo_id, station_id=station.id
        ).scalar() or 0
        labels.append(f"{station.code} {station.name}")
        good.append(g)
        scrap.append(s)
    return {"labels": labels, "good": good, "scrap": scrap}


@router.get("/api/mqtt/feed")
def api_mqtt_feed(
    request: Request,
    _: dict = Depends(require_login),
):
    return get_mqtt_feed()


def _build_wo_list(db, wos: list) -> list[dict]:
    result = []
    for wo in wos:
        op_status_map = {op.station_id: op.status for op in wo.operations}
        routings = sorted(wo.product.routings, key=lambda r: r.sequence)
        route_stations = [
            {"station": r.station, "op_status": op_status_map.get(r.station_id, "pending")}
            for r in routings
        ]
        kpis = KpiService(db).calculate_all(wo.id)
        # Check if this WO has any anomaly in production logs
        has_anomaly = db.query(ProductionLog).filter_by(
            work_order_id=wo.id, is_anomaly=True
        ).first() is not None
        result.append({
            "id": wo.id,
            "order_number": wo.order_number,
            "product_name": wo.product.name,
            "product_code": wo.product.code,
            "qty_planned": wo.qty_planned,
            "status": wo.status,
            "started_at": wo.started_at.isoformat() if wo.started_at else None,
            "completed_at": wo.completed_at.isoformat() if wo.completed_at else None,
            "route_stations": route_stations,
            "kpis": kpis,
            "has_anomaly": has_anomaly,
        })
    return result
