"""
PromQL helpers — renamed prom_query.py to avoid colliding with the
prometheus-client pip package.
"""
import logging
import requests

logger = logging.getLogger(__name__)

METRIC_QUERIES = {
    "cpu_usage": (
        '100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
    ),
    "memory_usage": (
        "100 - ((node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100)"
    ),
    "disk_usage": (
        '100 - ((node_filesystem_avail_bytes{fstype!~"tmpfs|overlay",mountpoint="/"}'
        ' / node_filesystem_size_bytes{fstype!~"tmpfs|overlay",mountpoint="/"}) * 100)'
    ),
    "network_errors": (
        "sum(rate(node_network_transmit_errs_total[5m]))"
        " + sum(rate(node_network_receive_errs_total[5m]))"
    ),
    "http_5xx": (
        'sum(rate(http_requests_total{status=~"5.."}[5m])) or vector(0)'
    ),
}


def _instant_query(base_url: str, promql: str) -> float | None:
    """Execute a single instant PromQL query and return the scalar."""
    try:
        resp = requests.get(
            f"{base_url}/api/v1/query",
            params={"query": promql},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("data", {}).get("result", [])
        if not results:
            return None
        return float(results[0]["value"][1])
    except Exception as exc:
        logger.warning("PromQL query failed (%s): %s", promql[:60], exc)
        return None


def fetch_metrics(prometheus_url: str) -> dict[str, float]:
    """
    Run all configured PromQL queries against *prometheus_url* and return
    a mapping of metric_name → current float value.
    Metrics that return None are omitted.
    """
    results: dict[str, float] = {}
    for name, query in METRIC_QUERIES.items():
        val = _instant_query(prometheus_url, query)
        if val is not None:
            results[name] = val
    return results
