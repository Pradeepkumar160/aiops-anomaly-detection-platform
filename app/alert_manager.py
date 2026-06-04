import logging
import requests
from app.config import settings

logger = logging.getLogger(__name__)


def send_slack_alert(message: str):
    if not settings.slack_webhook_url:
        return
    resp = requests.post(
        settings.slack_webhook_url,
        json={"text": message},
        timeout=5,
    )
    resp.raise_for_status()
    logger.info("Slack alert sent")


def send_pagerduty_alert(metric: str, value: float, score: float):
    if not settings.pagerduty_routing_key:
        return
    payload = {
        "routing_key": settings.pagerduty_routing_key,
        "event_action": "trigger",
        "payload": {
            "summary": f"AIOps anomaly: {metric} = {value:.2f} (score {score:.4f})",
            "severity": "critical",
            "source": "aiops-platform",
            "custom_details": {"metric": metric, "value": value, "score": score},
        },
    }
    resp = requests.post(
        "https://events.pagerduty.com/v2/enqueue",
        json=payload,
        timeout=5,
    )
    resp.raise_for_status()
    logger.info("PagerDuty alert sent for %s", metric)
