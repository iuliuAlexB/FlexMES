from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from auth import require_csrf, require_manager, flash
from models import WorkOrder, Product
from services.work_order_service import WorkOrderService
from template_utils import tmpl

router = APIRouter()


@router.get("/cockpit")
def cockpit(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_manager),
):
    from sqlalchemy import func
    from models import ProductionLog, Station

    wos = db.query(WorkOrder).order_by(WorkOrder.created_at.desc()).all()
    products = db.query(Product).filter_by(is_active=True).all()

    s4 = db.query(Station).filter_by(code="S4").first()

    wo_data = []
    for wo in wos:
        if wo.status == "completed" and s4:
            good_qty = db.query(func.sum(ProductionLog.qty_good)).filter_by(
                work_order_id=wo.id,
                station_id=s4.id
            ).scalar() or 0

            scrap_qty = db.query(func.sum(ProductionLog.qty_scrap)).filter_by(
                work_order_id=wo.id
            ).scalar() or 0
        else:
            good_qty = None
            scrap_qty = None

        wo_data.append({
            "wo": wo,
            "good_qty": good_qty,
            "scrap_qty": scrap_qty,
        })

    return tmpl(request, "cockpit.html", wo_data=wo_data, products=products)


@router.get("/api/workorders/status")
def wo_status(
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(require_manager),
):
    from sqlalchemy import func
    from models import ProductionLog, Station

    wos = db.query(WorkOrder).order_by(WorkOrder.created_at.desc()).all()
    s4 = db.query(Station).filter_by(code="S4").first()
    result = []

    for wo in wos:
        active_op = next(
            (op for op in wo.operations if op.status == "in_progress"), None
        )
        if active_op:
            station_display = f"{active_op.station.code} {active_op.station.name}"
        elif wo.status == "completed":
            station_display = "✓ Toate finalizate"
        else:
            station_display = "—"

        if wo.status == "completed" and s4:
            good_qty = db.query(func.sum(ProductionLog.qty_good)).filter_by(
                work_order_id=wo.id, station_id=s4.id
            ).scalar() or 0
            scrap_qty = db.query(func.sum(ProductionLog.qty_scrap)).filter_by(
                work_order_id=wo.id
            ).scalar() or 0
        else:
            good_qty = None
            scrap_qty = None

        result.append({
            "id": wo.id,
            "status": wo.status,
            "station_display": station_display,
            "good_qty": good_qty,
            "scrap_qty": scrap_qty,
            "completed_at": wo.completed_at.strftime("%d.%m %H:%M") if wo.completed_at else None,
        })

    return result


@router.post("/workorders")
def create_workorder(
    request: Request,
    product_id: int = Form(...),
    qty_planned: int = Form(...),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
    current_user: dict = Depends(require_manager),
):
    try:
        WorkOrderService(db).create(product_id, qty_planned, current_user["id"])
        flash(request, "Comandă de producție creată cu succes", "success")
    except Exception as e:
        flash(request, str(e.detail if hasattr(e, "detail") else e), "danger")
    return RedirectResponse("/cockpit", status_code=302)


@router.post("/workorders/{wo_id}/start")
def start_workorder(
    wo_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
    current_user: dict = Depends(require_manager),
):
    try:
        WorkOrderService(db).start(wo_id)
        flash(request, "Comanda a fost lansată în producție", "success")
    except Exception as e:
        flash(request, str(e.detail if hasattr(e, "detail") else e), "danger")
    return RedirectResponse("/cockpit", status_code=302)


@router.post("/workorders/{wo_id}/cancel")
def cancel_workorder(
    wo_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
    current_user: dict = Depends(require_manager),
):
    try:
        WorkOrderService(db).cancel(wo_id)
        flash(request, "Comanda a fost anulată", "success")
    except Exception as e:
        flash(request, str(e.detail if hasattr(e, "detail") else e), "danger")
    return RedirectResponse("/cockpit", status_code=302)