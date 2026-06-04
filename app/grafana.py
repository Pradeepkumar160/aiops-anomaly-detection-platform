import logging
import requests
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)


def create_annotation(metric: str, value: float, score: float):
    if not settings.grafana_api_token:
        return
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    payload = {
        "time": now_ms,
        "tags": ["aiops", "anomaly", metric],
        "text": f"🚨 Anomaly: <b>{metric}</b> = {value:.2f} (score {score:.4f})",
    }
    headers = {"Authorization": f"Bearer {settings.grafana_api_token}"}
    try:
        resp = requests.post(
            f"{settings.grafana_url}/api/annotations",
            json=payload,
            headers=headers,
            timeout=5,
        )
        resp.raise_for_status()
        logger.info("Grafana annotation created for %s", metric)
    except Exception as exc:
        logger.warning("Grafana annotation failed: %s", exc)
