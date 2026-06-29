"""
Observer Pattern — STUB - Directii viitoare .
AnomalyObserver va fi notificat după fiecare nou ProductionLog și ar rula automat modelul de Isolation Forest.
Acum, anomaly.predict() e apelat direct din mqtt_listener.py.
"""
from models import ProductionLog


class AnomalyObserver:


    def on_log_created(self, log: ProductionLog) -> None:

        # directii viitoare

        raise NotImplementedError("AnomalyObserver not yet implemented — anomaly.predict() called directly")
