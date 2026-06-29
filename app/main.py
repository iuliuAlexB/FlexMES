import logging
from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from starlette.middleware.sessions import SessionMiddleware

from config import settings
from database import get_db, SessionLocal, engine
from auth import AuthRedirect
import models

from routers import auth as auth_router, dashboard, cockpit, routing_config, users, operator

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="FlexMES", description="Manufacturing Execution System")
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Rooutere
app.include_router(auth_router.router)
app.include_router(dashboard.router)
app.include_router(cockpit.router)
app.include_router(routing_config.router)
app.include_router(users.router)
app.include_router(operator.router)


#Auth redirect exception handler
@app.exception_handler(AuthRedirect)
async def auth_redirect_handler(request: Request, exc: AuthRedirect):
    return RedirectResponse(url=exc.url, status_code=302)


# Root redirect
@app.get("/")
def root(request: Request):
    from auth import get_session_user
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user["role"] == "operator":
        return RedirectResponse("/operator", status_code=302)
    return RedirectResponse("/dashboard", status_code=302)


# Simulator support: WO active
@app.get("/api/workorders/active")
def active_workorders(db: Session = Depends(get_db)):
    from models import Operation, Station
    wos = db.query(models.WorkOrder).filter_by(status="in_progress").all()
    result = []
    for wo in wos:
        active_op = (
            db.query(Operation)
            .filter_by(work_order_id=wo.id, status="in_progress")
            .first()
        )
        if not active_op:
            continue
        station = db.query(Station).filter_by(id=active_op.station_id).first()
        if not station:
            continue
        # Skip S4 : manual
        if station.code == "S4":
            continue
        result.append({
            "id": wo.id,
            "order_number": wo.order_number,
            "active_station": station.code.lower()
        })
    return result

@app.get("/api/workorders/{wo_id}/prev_station_good")
def prev_station_good(
    wo_id: int,
    station_id: int,
    db: Session = Depends(get_db)
):
    from models import WorkOrder, Operation, ProductionLog, Routing

    wo = db.query(WorkOrder).filter_by(id=wo_id).first()
    if not wo:
        return {"prev_good": None, "is_first_station": False, "qty_planned": 0}

    current_routing = db.query(Routing).filter_by(
        product_id=wo.product_id,
        station_id=station_id
    ).first()

    if not current_routing:
        return {"prev_good": None, "is_first_station": False, "qty_planned": wo.qty_planned}

    if current_routing.sequence == 1:
        return {
            "prev_good": wo.qty_planned,
            "is_first_station": True,
            "qty_planned": wo.qty_planned
        }

    prev_routing = db.query(Routing).filter_by(
        product_id=wo.product_id,
        sequence=current_routing.sequence - 1
    ).first()

    if not prev_routing:
        return {"prev_good": wo.qty_planned, "is_first_station": False, "qty_planned": wo.qty_planned}

    prev_good = db.query(func.sum(ProductionLog.qty_good)).filter_by(
        work_order_id=wo_id,
        station_id=prev_routing.station_id
    ).scalar() or 0

    return {
        "prev_good": prev_good,
        "is_first_station": False,
        "qty_planned": wo.qty_planned
    }


# Start applicatie
@app.on_event("startup")
def startup():
    import seed
    import anomaly
    import mqtt_listener

    models.Base.metadata.create_all(engine)

    db = SessionLocal()
    try:
        seed.run_seed(db)
        anomaly.train(db)
    finally:
        db.close()

    mqtt_listener.start_mqtt_listener(SessionLocal)
