import logging
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from models import Operation, ProductionLog, Station, WorkOrder

logger = logging.getLogger(__name__)


class OperationService:
    def __init__(self, db: Session):
        self.db = db

    def generate_for_wo(self, wo_id: int, routings: list) -> list[Operation]:
        """Create all operations for a WO from its routing. First op is in_progress."""
        ops = []
        for i, routing in enumerate(routings):
            op = Operation(
                work_order_id=wo_id,
                station_id=routing.station_id,
                sequence=routing.sequence,
                status="in_progress" if i == 0 else "pending",
                started_at=datetime.utcnow() if i == 0 else None,
                started_by=1,
            )
            self.db.add(op)
            ops.append(op)
        self.db.commit()
        return ops

    def complete_via_mqtt(
        self, wo_id: int, station_id: int, qty_good: int, qty_scrap: int
    ) -> ProductionLog | None:
        logger.info(
            "complete_via_mqtt called: wo_id=%s station_id=%s qty_good=%s qty_scrap=%s",
            wo_id, station_id, qty_good, qty_scrap,
        )
        try:
            op = self.db.query(Operation).filter_by(
                work_order_id=wo_id, station_id=station_id, status="in_progress"
            ).first()
            if not op:
                logger.warning(
                    "complete_via_mqtt: no in_progress operation found for wo_id=%s station_id=%s",
                    wo_id, station_id,
                )
                return None
            logger.info(
                "complete_via_mqtt: found op id=%s sequence=%s status=%s",
                op.id, op.sequence, op.status,
            )
            log = ProductionLog(
                operation_id=op.id,
                work_order_id=wo_id,
                station_id=station_id,
                operator_id=1,   # mqtt_system
                qty_good=qty_good,
                qty_scrap=qty_scrap,
                source="mqtt",
            )
            self.db.add(log)
            op_sequence = op.sequence
            op.status = "completed"
            op.completed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(log)
            logger.info("complete_via_mqtt: log id=%s committed, advancing sequence", log.id)

            self.unlock_next(wo_id, op_sequence)
            self._check_auto_complete(wo_id)
            return log
        except Exception:
            logger.exception(
                "complete_via_mqtt: unhandled exception for wo_id=%s station_id=%s",
                wo_id, station_id,
            )

    def complete_manual_s4(
        self, wo_id: int, qty_good: int, qty_scrap: int, operator_id: int
    ) -> ProductionLog:
        """Complete S4 QC Inspection manually by an operator."""
        s4 = self.db.query(Station).filter_by(code="S4").first()
        if not s4:
            raise HTTPException(404, "Stația S4 nu există")

        op = self.db.query(Operation).filter_by(
            work_order_id=wo_id, station_id=s4.id, status="in_progress"
        ).first()
        if not op:
            raise HTTPException(400, "Nu există operație activă la S4 pentru această comandă")

        if qty_good < 0 or qty_scrap < 0:
            raise HTTPException(400, "Cantitățile nu pot fi negative")
        if qty_good + qty_scrap == 0:
            raise HTTPException(400, "Cel puțin o unitate trebuie raportată")

        # Validate against previous station output — ISO 22400 physical constraint
        wo = self.db.query(WorkOrder).filter_by(id=wo_id).first()
        prev_station_good = self._get_prev_station_good(wo_id, s4.id, wo.product_id)
        if prev_station_good is not None and qty_good + qty_scrap > prev_station_good:
            raise HTTPException(
                400,
                f"Total unități procesate ({qty_good + qty_scrap}) depășește "
                f"producția stației anterioare ({prev_station_good} unități bune). "
                f"Verificați cantitățile introduse."
            )

        log = ProductionLog(
            operation_id=op.id,
            work_order_id=wo_id,
            station_id=s4.id,
            operator_id=operator_id,
            qty_good=qty_good,
            qty_scrap=qty_scrap,
            source="manual",
        )
        self.db.add(log)
        op.status = "completed"
        op.completed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(log)

        self.unlock_next(wo_id, op.sequence)
        self._check_auto_complete(wo_id)
        return log

    def unlock_next(self, wo_id: int, completed_sequence: int) -> None:
        """Move the next pending operation to in_progress."""
        next_op = (
            self.db.query(Operation)
            .filter(
                Operation.work_order_id == wo_id,
                Operation.sequence == completed_sequence + 1,
                Operation.status == "pending",
            )
            .first()
        )
        if next_op:
            next_op.status = "in_progress"
            next_op.started_at = datetime.utcnow()
            self.db.commit()

    def _check_auto_complete(self, wo_id: int) -> None:
        total = self.db.query(Operation).filter_by(work_order_id=wo_id).count()
        done = self.db.query(Operation).filter_by(work_order_id=wo_id, status="completed").count()
        if total > 0 and total == done:
            from services.work_order_service import WorkOrderService
            WorkOrderService(self.db).auto_complete(wo_id)

    def _get_prev_station_good(
            self, wo_id: int, station_id: int, product_id: int
    ) -> int | None:
        """Returns qty_good from previous station, or qty_planned if first station."""
        from models import Routing,WorkOrder

        current_routing = self.db.query(Routing).filter_by(
            product_id=product_id,
            station_id=station_id
        ).first()

        if not current_routing:
            return None

        # First station — limit is qty_planned
        if current_routing.sequence == 1:
            wo = self.db.query(WorkOrder).filter_by(id=wo_id).first()
            return wo.qty_planned if wo else None

        # Find previous station in routing
        prev_routing = self.db.query(Routing).filter_by(
            product_id=product_id,
            sequence=current_routing.sequence - 1
        ).first()

        if not prev_routing:
            return None

        from sqlalchemy import func
        prev_good = self.db.query(func.sum(ProductionLog.qty_good)).filter_by(
            work_order_id=wo_id,
            station_id=prev_routing.station_id
        ).scalar()

        return prev_good or None