"""
IoT Simulator — publishes production data for S1, S2, S3 every 30 seconds.
S4 (QC Inspection) is always handled manually by the operator.
"""
import json
import logging
import os
import random
import time

import paho.mqtt.client as mqtt
import requests
from dotenv import load_dotenv

load_dotenv()

MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "flexmes")
WEB_URL = os.getenv("WEB_URL", "http://web:8000")
PUBLISH_INTERVAL = 30   # seconds between simulation cycles
STATIONS = ["s1", "s2", "s3"]   # S4 is manual only

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SIM] %(message)s")
logger = logging.getLogger(__name__)


def get_active_work_orders() -> list[dict]:
    """Fetch in_progress work orders from the FlexMES API."""
    try:
        resp = requests.get(f"{WEB_URL}/api/workorders/active", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.warning(f"Could not reach FlexMES API: {e}")
    return []

def get_prev_station_good(wo_id: int, station: str) -> int | None:
    """Get the qty_good from the previous station to generate realistic data."""
    station_ids = {"s1": 1, "s2": 2, "s3": 3, "s4": 4}
    station_id = station_ids.get(station, 1)
    try:
        resp = requests.get(
            f"{WEB_URL}/api/workorders/{wo_id}/prev_station_good",
            params={"station_id": station_id},
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("prev_good") or None
    except Exception as e:
        logger.warning(f"Could not get prev_station_good: {e}")
    return None


def publish_data(client: mqtt.Client, wo_id: int, station: str) -> None:
    """Publish production data respecting physical constraints."""
    max_input = get_prev_station_good(wo_id, station)

    if max_input is None or max_input == 0:
        logger.warning(f"Skipping publish for wo_id={wo_id} station={station} — no prev_good data")
        return

    # qty_good: intre 85% si 95% din input
    qty_good = random.randint(
        max(1, int(max_input * 0.85)),
        max(1, int(max_input * 0.95))
    )

    # qty_scrap: maxim 10% din input, dar nu mai mult decat ce ramane
    max_scrap = max_input - qty_good
    qty_scrap = random.randint(2, max(2, min(int(max_input * 0.10), max_scrap)))

    payload = {
        "work_order_id": wo_id,
        "qty_good": qty_good,
        "qty_scrap": qty_scrap,
    }
    topic = f"{MQTT_TOPIC_PREFIX}/{station}/log"
    client.publish(topic, json.dumps(payload))
    logger.info(f"Published → {topic}: {payload}")


def connect_mqtt() -> mqtt.Client:
    """Connect to Mosquitto with retry logic."""
    client = mqtt.Client()
    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.loop_start()
            logger.info(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
            return client
        except Exception as e:
            logger.warning(f"MQTT connection failed: {e}. Retrying in 5s...")
            time.sleep(5)


def wait_for_api() -> None:
    """Wait until the FlexMES web server is ready."""
    logger.info("Waiting for FlexMES API to be ready...")
    while True:
        try:
            resp = requests.get(f"{WEB_URL}/api/workorders/active", timeout=3)
            if resp.status_code == 200:
                logger.info("FlexMES API is ready")
                return
        except Exception:
            pass
        time.sleep(5)


def main():
    wait_for_api()
    client = connect_mqtt()

    while True:
        active_wos = get_active_work_orders()
        if not active_wos:
            logger.info("No active work orders. Waiting...")
        else:
            for wo in active_wos:
                station = wo["active_station"]
                publish_data(client, wo["id"], station)
                time.sleep(1)   # small delay between station publishes

        time.sleep(PUBLISH_INTERVAL)


if __name__ == "__main__":
    main()
