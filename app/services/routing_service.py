from fastapi import HTTPException
from sqlalchemy.orm import Session
from models import Routing, Station, WorkOrder


class RoutingService:
    def __init__(self, db: Session):
        self.db = db

    def get_for_product(self, product_id: int) -> list[Routing]:
        return (
            self.db.query(Routing)
            .filter_by(product_id=product_id)
            .order_by(Routing.sequence)
            .all()
        )

    def save(self, product_id: int, station_ids: list[int]) -> list[Routing]:
        """Save routing for a product. Validates S4 presence and no active WOs."""
        if not station_ids:
            raise HTTPException(400, "Rutele nu pot fi goale")

        s4 = self.db.query(Station).filter_by(code="S4").first()
        if s4 and s4.id not in station_ids:
            raise HTTPException(400, "S4 QC Inspection trebuie să fie prezent în orice routing")

        self.validate_no_active_wos(product_id)

        self.db.query(Routing).filter_by(product_id=product_id).delete()

        routings = []
        for seq, station_id in enumerate(station_ids, start=1):
            r = Routing(product_id=product_id, station_id=station_id, sequence=seq)
            self.db.add(r)
            routings.append(r)

        self.db.commit()
        return routings

    def validate_no_active_wos(self, product_id: int) -> None:
        active = (
            self.db.query(WorkOrder)
            .filter(
                WorkOrder.product_id == product_id,
                WorkOrder.status.in_(["planned", "in_progress"]),
            )
            .count()
        )
        if active > 0:
            raise HTTPException(400, "Nu se poate modifica routing-ul unui produs cu comenzi active")
