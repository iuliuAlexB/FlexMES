"""Thread MQTT Listener. Ia date de la simulator si scrie in loguri."""
import json
import logging
import threading
import time
from datetime import datetime

import paho.mqtt.client as mqtt
from config import settings

logger = logging.getLogger(__name__)

_mqtt_feed: list[dict] = []
_FEED_MAX = 20


def get_mqtt_feed() -> list[dict]:
    return list(_mqtt_feed)


def _append_feed(entry: dict) -> None:
    _mqtt_feed.append(entry)
    while len(_mqtt_feed) > _FEED_MAX:
        _mqtt_feed.pop(0)


def _on_connect(client, userdata, flags, rc):
    topic = f"{settings.MQTT_TOPIC_PREFIX}/+/log"
    client.subscribe(topic)
    logger.info(f"MQTT subscribed to {topic} (rc={rc})")


def _on_message(client, userdata, msg):
    db_factory = userdata
    db = None
    try:
        payload = json.loads(msg.payload.decode())
        parts = msg.topic.split("/")
        station_code = parts[1].upper()

        work_order_id = payload.get("work_order_id")
        qty_good = int(payload.get("qty_good", 0))
        qty_scrap = int(payload.get("qty_scrap", 0))

        _append_feed({
            "topic": msg.topic,
            "station": station_code,
            "work_order_id": work_order_id,
            "qty_good": qty_good,
            "qty_scrap": qty_scrap,
            "timestamp": datetime.utcnow().isoformat(),
        })

        db = db_factory()
        from models import Station
        from services.operation_service import OperationService
        import anomaly

        station = db.query(Station).filter_by(code=station_code).first()
        if not station:
            logger.warning(f"Unknown station code: {station_code}")
            return

        op_service = OperationService(db)
        log = op_service.complete_via_mqtt(work_order_id, station.id, qty_good, qty_scrap)

        if log:
            is_anom = anomaly.predict(log)
            if is_anom:
                log.is_anomaly = True
                db.commit()
                logger.warning(f"Anomaly detected at {station_code} for WO {work_order_id}")
            if anomaly.should_retrain(db):
                anomaly.train(db)

    except Exception:
        if db:
            db.rollback()
        logger.exception("MQTT message handling error")
    finally:
        if db:
            db.close()


def start_mqtt_listener(db_factory) -> None:
    """Start MQTT client"""
    def run():
        client = mqtt.Client(userdata=db_factory)
        client.on_connect = _on_connect
        client.on_message = _on_message

        while True:
            try:
                client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
                client.loop_forever()
            except Exception as e:
                logger.error(f"MQTT connection failed: {e}. Retrying in 5s...")
                time.sleep(5)

    thread = threading.Thread(target=run, daemon=True, name="mqtt-listener")
    thread.start()
    logger.info("MQTT listener thread started")
