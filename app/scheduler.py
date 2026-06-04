"""
Background detection scheduler — runs every DETECTION_INTERVAL_SECONDS.
"""
import logging
import time
import requests
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

API_BASE = "http://aiops-api:8000"


def wait_for_api():
    logger.info("Waiting for AIOps API…")
    while True:
        try:
            r = requests.get(f"{API_BASE}/health", timeout=5)
            if r.status_code == 200:
                logger.info("API is up ✓")
                return
        except Exception:
            pass
        time.sleep(5)


def bootstrap_model():
    """Train an initial model if none exists."""
    try:
        h = requests.get(f"{API_BASE}/health", timeout=5).json()
        if h.get("model_loaded"):
            logger.info("Model already loaded, skipping bootstrap")
            return
        import numpy as np
        values = (20 + np.random.rand(200) * 50).tolist()
        r = requests.post(f"{API_BASE}/train", json={"values": values}, timeout=30)
        r.raise_for_status()
        logger.info("Bootstrap model trained ✓")
    except Exception as exc:
        logger.warning("Bootstrap training failed: %s", exc)


def run_detection():
    try:
        r = requests.post(f"{API_BASE}/scan", timeout=30)
        if r.status_code == 200:
            data = r.json()
            anomalies = [x for x in data.get("results", []) if x["anomaly"]]
            logger.info("Scan complete: %d metrics, %d anomalies", data.get("scanned", 0), len(anomalies))
        else:
            logger.warning("Scan returned %s", r.status_code)
    except Exception as exc:
        logger.error("Detection cycle failed: %s", exc)


def main():
    wait_for_api()
    bootstrap_model()
    interval = settings.detection_interval_seconds
    logger.info("Scheduler started — interval %ds", interval)
    while True:
        run_detection()
        time.sleep(interval)


if __name__ == "__main__":
    main()
