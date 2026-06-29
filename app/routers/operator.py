from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from auth import require_csrf, require_login, flash
from models import Operation, ProductionLog, Station
from services.operation_service import OperationService
import anomaly
from template_utils import tmpl

router = APIRouter()


@router.get("/operator")
def operator_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_login),
):
    s4 = db.query(Station).filter_by(code="S4").first()
    s4_ops = []
    if s4:
        s4_ops = (
            db.query(Operation)
            .filter_by(station_id=s4.id, status="in_progress")
            .all()
        )

    recent_logs = (
        db.query(ProductionLog)
        .order_by(ProductionLog.logged_at.desc())
        .limit(10)
        .all()
    )

    return tmpl(
        request, "operator.html",
        s4_ops=s4_ops,
        recent_logs=recent_logs,
    )


@router.get("/api/s4/queue")
def s4_queue(
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(require_login),
):
    s4 = db.query(Station).filter_by(code="S4").first()
    if not s4:
        return []

    ops = db.query(Operation).filter_by(station_id=s4.id, status="in_progress").all()
    result = []
    for op in ops:
        wo = op.work_order
        result.append({
            "operation_id": op.id,
            "work_order_id": wo.id,
            "order_number": wo.order_number,
            "product_name": wo.product.name,
            "product_code": wo.product.code,
            "qty_planned": wo.qty_planned,
            "route_ops": [
                {"code": o.station.code, "status": o.status}
                for o in sorted(wo.operations, key=lambda x: x.sequence)
            ],
        })
    return result


@router.post("/api/s4/complete")
def s4_complete(
    request: Request,
    work_order_id: int = Form(...),
    qty_good: int = Form(...),
    qty_scrap: int = Form(...),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
    current_user: dict = Depends(require_login),
):
    try:
        op_service = OperationService(db)
        log = op_service.complete_manual_s4(work_order_id, qty_good, qty_scrap, current_user["id"])

        is_anom = anomaly.predict(log)
        if is_anom:
            log.is_anomaly = True
            db.commit()

        if anomaly.should_retrain(db):
            anomaly.train(db)

        flash(request, "Inspecție QC finalizată. Comanda de producție a fost închisă automat.", "success")
    except Exception as e:
        flash(request, str(e.detail if hasattr(e, "detail") else e), "danger")

    return RedirectResponse("/operator", status_code=302)