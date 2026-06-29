"""Calcul KPIs  (ISO 22400) - KpiService"""
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session


def get_fpy(db: Session, wo_id: int) -> float | None:
    """First Pass Yield = qty_good@S4 / (qty_good@S1 + qty_scrap@S1) × 100."""
    from models import ProductionLog, Station

    s1 = db.query(Station).filter_by(code="S1").first()
    s4 = db.query(Station).filter_by(code="S4").first()
    if not s1 or not s4:
        return None

    s1_logs = db.query(
        func.sum(ProductionLog.qty_good).label("good"),
        func.sum(ProductionLog.qty_scrap).label("scrap")
    ).filter_by(work_order_id=wo_id, station_id=s1.id).first()

    s1_input = (s1_logs.good or 0) + (s1_logs.scrap or 0)

    s4_good = db.query(func.sum(ProductionLog.qty_good)).filter_by(
        work_order_id=wo_id, station_id=s4.id
    ).scalar() or 0

    if s1_input == 0 or s4_good == 0:
        return None

    return round(s4_good / s1_input * 100, 2)


def get_throughput(db: Session, wo_id: int) -> float | None:
    """Throughput = qty_good@S4 / elapsed hours."""
    from models import ProductionLog, WorkOrder, Station

    wo = db.query(WorkOrder).filter_by(id=wo_id).first()
    if not wo or not wo.started_at:
        return None

    end_time = wo.completed_at or datetime.utcnow()
    elapsed_hours = (end_time - wo.started_at).total_seconds() / 3600

    if elapsed_hours < (10 / 60):  # less than 10 minutes
        return None

    s4 = db.query(Station).filter_by(code="S4").first()
    if not s4:
        return None

    s4_good = db.query(func.sum(ProductionLog.qty_good)).filter_by(
        work_order_id=wo_id, station_id=s4.id
    ).scalar() or 0

    return round(s4_good / elapsed_hours, 2) if elapsed_hours > 0 else None


def get_scrap_rate(db: Session, wo_id: int) -> float | None:
    """Scrap Rate = SUM(qty_scrap all stations) / (qty_good@S1 + qty_scrap@S1) × 100."""
    from models import ProductionLog, Station

    s1 = db.query(Station).filter_by(code="S1").first()
    if not s1:
        return None

    s1_logs = db.query(
        func.sum(ProductionLog.qty_good).label("good"),
        func.sum(ProductionLog.qty_scrap).label("scrap")
    ).filter_by(work_order_id=wo_id, station_id=s1.id).first()

    s1_input = (s1_logs.good or 0) + (s1_logs.scrap or 0)

    if s1_input == 0:
        return None

    total_scrap = db.query(func.sum(ProductionLog.qty_scrap)).filter_by(
        work_order_id=wo_id
    ).scalar() or 0

    return round(total_scrap / s1_input * 100, 2)