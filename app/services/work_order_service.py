from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from models import WorkOrder, Product, Routing, ProductionLog


class WorkOrderService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, product_id: int, qty_planned: int, created_by: int) -> WorkOrder:
        product = self.db.query(Product).filter_by(id=product_id, is_active=True).first()
        if not product:
            raise HTTPException(400, "Produsul nu există sau este inactiv")

        routing_exists = self.db.query(Routing).filter_by(product_id=product_id).first()
        if not routing_exists:
            raise HTTPException(400, "Produsul nu are routing definit")

        order_number = self._next_order_number()
        wo = WorkOrder(
            order_number=order_number,
            product_id=product_id,
            qty_planned=qty_planned,
            status="planned",
            created_by=created_by,
        )
        self.db.add(wo)
        self.db.commit()
        self.db.refresh(wo)
        return wo

    def start(self, wo_id: int) -> WorkOrder:
        wo = self._get_or_404(wo_id)
        if wo.status != "planned":
            raise HTTPException(400, "Comanda trebuie să fie în starea 'planificat'")
        if not wo.product.is_active:
            raise HTTPException(400, "Produsul asociat este inactiv")

        routings = (
            self.db.query(Routing)
            .filter_by(product_id=wo.product_id)
            .order_by(Routing.sequence)
            .all()
        )
        if not routings:
            raise HTTPException(400, "Produsul nu are routing definit")

        from services.operation_service import OperationService
        OperationService(self.db).generate_for_wo(wo_id, routings)

        wo.status = "in_progress"
        wo.started_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(wo)
        return wo

    def cancel(self, wo_id: int) -> WorkOrder:
        wo = self._get_or_404(wo_id)
        if wo.status in ("completed", "cancelled"):
            raise HTTPException(400, "Comanda nu poate fi anulată în starea curentă")

        if wo.status == "in_progress":
            log_count = self.db.query(ProductionLog).filter_by(work_order_id=wo_id).count()
            if log_count > 0:
                raise HTTPException(400, "Nu se poate anula o comandă cu log-uri de producție înregistrate")

        wo.status = "cancelled"
        wo.cancelled_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(wo)
        return wo

    def auto_complete(self, wo_id: int) -> None:
        """Called automatically when the last operation completes."""
        wo = self.db.query(WorkOrder).filter_by(id=wo_id).first()
        if not wo or wo.status != "in_progress":
            return
        from models import Operation
        ops = self.db.query(Operation).filter_by(work_order_id=wo_id).all()
        if all(op.status == "completed" for op in ops):
            wo.status = "completed"
            wo.completed_at = datetime.utcnow()
            self.db.commit()

    def _get_or_404(self, wo_id: int) -> WorkOrder:
        wo = self.db.query(WorkOrder).filter_by(id=wo_id).first()
        if not wo:
            raise HTTPException(404, "Comanda de producție nu există")
        return wo

    def _next_order_number(self) -> str:
        count = self.db.query(WorkOrder).count()
        while True:
            candidate = f"WO-{count + 1:03d}"
            if not self.db.query(WorkOrder).filter_by(order_number=candidate).first():
                return candidate
            count += 1
