import logging
import numpy as np
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_model = None
_last_trained_count = 0
CONTAMINATION = 0.05


def _build_features(logs: list) -> np.ndarray:
    rows = []
    for log in logs:
        total = log.qty_good + log.qty_scrap
        scrap_rate = log.qty_scrap / total if total > 0 else 0.0
        hour = log.logged_at.hour if log.logged_at else 12
        rows.append([log.qty_good, log.qty_scrap, scrap_rate, hour, log.station_id])
    return np.array(rows) if rows else np.zeros((0, 5))


def train(db: Session) -> None:
    global _model, _last_trained_count
    from models import ProductionLog
    from sklearn.ensemble import IsolationForest

    logs = db.query(ProductionLog).all()
    if len(logs) < 50:
        logger.info("Not enough logs to train anomaly model (need >= 50)")
        return

    X = _build_features(logs)
    _model = IsolationForest(contamination=CONTAMINATION, random_state=42)
    _model.fit(X)
    _last_trained_count = len(logs)
    logger.info(f"Anomaly model trained on {len(logs)} logs")


def predict(log) -> bool:
    """Return True if the log is an anomaly"""
    if _model is None:
        return False

    total = log.qty_good + log.qty_scrap
    scrap_rate = log.qty_scrap / total if total > 0 else 0.0
    hour = log.logged_at.hour if log.logged_at else 12

    X = np.array([[log.qty_good, log.qty_scrap, scrap_rate, hour, log.station_id]])
    result = _model.predict(X)
    return bool(result[0] == -1)   # -1 = anomaly in Isolation Forest


def should_retrain(db: Session) -> bool:
    from models import ProductionLog
    count = db.query(ProductionLog).count()
    return count >= _last_trained_count + 100
