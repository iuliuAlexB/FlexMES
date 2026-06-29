from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import WorkOrder, ProductionLog, Station
import kpi


class KpiService:
    def __init__(self, db: Session):
        self.db = db

    def calculate_fpy(self, wo_id: int) -> float | None:
        return kpi.get_fpy(self.db, wo_id)

    def calculate_throughput(self, wo_id: int) -> float | None:
        return kpi.get_throughput(self.db, wo_id)

    def calculate_scrap_rate(self, wo_id: int) -> float | None:
        return kpi.get_scrap_rate(self.db, wo_id)

    def calculate_all(self, wo_id: int) -> dict:
        return {
            "fpy": self.calculate_fpy(wo_id),
            "throughput": self.calculate_throughput(wo_id),
            "scrap_rate": self.calculate_scrap_rate(wo_id),
        }

    def calculate_global(self) -> dict:
        """
        KPI globale calculate pe ultimele 24 de ore cu sumele totale agregate,
        ISO 22400-2:2014
        """
        cutoff = datetime.utcnow() - timedelta(hours=24)

        s1 = self.db.query(Station).filter_by(code="S1").first()
        s4 = self.db.query(Station).filter_by(code="S4").first()

        if not s1 or not s4:
            return {"fpy": None, "throughput": None, "scrap_rate": None}

        # S1 input — total material intrat in linie in ultimele 24h
        s1_logs = self.db.query(
            func.sum(ProductionLog.qty_good).label("good"),
            func.sum(ProductionLog.qty_scrap).label("scrap")
        ).filter(
            ProductionLog.station_id == s1.id,
            ProductionLog.logged_at >= cutoff
        ).first()

        s1_input = (s1_logs.good or 0) + (s1_logs.scrap or 0)

        # S4 good — produse finite iesite din linie in ultimele 24h
        s4_good = self.db.query(func.sum(ProductionLog.qty_good)).filter(
            ProductionLog.station_id == s4.id,
            ProductionLog.logged_at >= cutoff
        ).scalar() or 0

        # Total scrap — toate rebuturile de pe toate statiile in ultimele 24h
        total_scrap = self.db.query(func.sum(ProductionLog.qty_scrap)).filter(
            ProductionLog.logged_at >= cutoff
        ).scalar() or 0

        # Global FPY
        fpy = round(s4_good / s1_input * 100, 2) if s1_input > 0 and s4_good > 0 else None

        # Global Throughput — produse finite / 24h (fereastra fixa)
        throughput = round(s4_good / 24, 2) if s4_good > 0 else None

        # Global Scrap Rate
        scrap_rate = round(total_scrap / s1_input * 100, 2) if s1_input > 0 else None

        return {
            "fpy": fpy,
            "throughput": throughput,
            "scrap_rate": scrap_rate,
        }
