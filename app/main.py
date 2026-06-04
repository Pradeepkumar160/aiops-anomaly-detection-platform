"""
AIOps Anomaly Detection Platform — FastAPI Application
"""
from __future__ import annotations

import time
import logging
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

# ── Prometheus instrumentation ────────────────────────────────────────────
from prometheus_client import (
    Counter, Gauge, Histogram, Summary,
    generate_latest, CONTENT_TYPE_LATEST,
    CollectorRegistry, REGISTRY
)

# ── Internal modules ──────────────────────────────────────────────────────
from app.config import settings
from app.database import init_db, save_anomaly, list_anomalies
from app.prom_query import fetch_metrics          # renamed from prometheus_client.py
from app.anomaly_detector import AnomalyDetector
from app.alert_manager import send_slack_alert, send_pagerduty_alert
from app.grafana import create_annotation

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────
# Custom Prometheus Metrics
# ─────────────────────────────────────────────────────────────────────────
MODEL_LOADED   = Gauge("aiops_model_loaded",   "1 if isolation forest model is loaded")
DB_HEALTHY     = Gauge("aiops_db_healthy",     "1 if PostgreSQL is reachable")
ANOMALIES_TOTAL = Counter("aiops_anomalies_total", "Total anomalies detected", ["metric_name"])
DETECTION_CYCLES = Counter("aiops_detection_cycles_total", "Total detection cycles run")
ANOMALY_STATUS  = Gauge("aiops_anomaly_status",  "Current anomaly flag per metric", ["metric_name"])
ANOMALY_SCORE   = Gauge("aiops_anomaly_score",   "Latest isolation-forest score per metric", ["metric_name"])
METRIC_VALUE    = Gauge("aiops_metric_value",    "Latest raw metric value", ["metric_name"])
API_LATENCY     = Histogram(
    "aiops_api_request_duration_seconds",
    "API request latency",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
)
DETECTION_CYCLE_DURATION = Histogram(
    "aiops_detection_cycle_duration_seconds",
    "Time taken for one full detection cycle",
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

# ─────────────────────────────────────────────────────────────────────────
# Application State
# ─────────────────────────────────────────────────────────────────────────
detector = AnomalyDetector()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting AIOps Platform…")
    try:
        init_db()
        DB_HEALTHY.set(1)
        logger.info("Database initialised ✓")
    except Exception as exc:
        DB_HEALTHY.set(0)
        logger.warning("Database not available: %s", exc)

    try:
        detector.load()
        MODEL_LOADED.set(1)
        logger.info("Model loaded ✓")
    except FileNotFoundError:
        MODEL_LOADED.set(0)
        logger.info("No pre-trained model found — train via POST /train")

    yield  # ── app running ──

    logger.info("Shutting down AIOps Platform…")


# ─────────────────────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AIOps Anomaly Detection Platform",
    version="1.0.0",
    description="ML-powered infrastructure monitoring with Isolation Forest + Prophet",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Latency middleware ─────────────────────────────────────────────────────
@app.middleware("http")
async def record_latency(request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    path = request.url.path.split("?")[0]
    API_LATENCY.labels(method=request.method, endpoint=path).observe(elapsed)
    return response


# ─────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────────────────────────────────
class TrainRequest(BaseModel):
    values: List[float]

class DetectRequest(BaseModel):
    metric: str
    value: float


# ─────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
def health():
    """Health check — returns model + DB status."""
    return {
        "status": "ok",
        "model_loaded": detector.is_loaded,
        "db_healthy": _check_db(),
    }


@app.get("/metrics", tags=["ops"])
def metrics():
    """Prometheus scrape endpoint — exposes all aiops_* metrics."""
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


@app.get("/metrics/current", tags=["monitoring"])
def metrics_current():
    """Fetch latest raw values from Prometheus for all monitored metrics."""
    try:
        data = fetch_metrics(settings.prometheus_url)
        for name, val in data.items():
            METRIC_VALUE.labels(metric_name=name).set(val)
        return {"metrics": data}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Prometheus unreachable: {exc}")


@app.post("/train", tags=["ml"])
def train(body: TrainRequest):
    """Train (or retrain) the Isolation Forest on supplied values."""
    if len(body.values) < 10:
        raise HTTPException(status_code=422, detail="Provide at least 10 training values")
    detector.train(body.values)
    detector.save()
    MODEL_LOADED.set(1)
    return {"status": "trained", "samples": len(body.values)}


@app.post("/detect", tags=["ml"])
def detect(body: DetectRequest):
    """Run anomaly detection on a single metric value."""
    if not detector.is_loaded:
        raise HTTPException(status_code=503, detail="Model not trained — call POST /train first")

    score, is_anomaly = detector.predict(body.value)
    ANOMALY_SCORE.labels(metric_name=body.metric).set(score)
    ANOMALY_STATUS.labels(metric_name=body.metric).set(1 if is_anomaly else 0)

    if is_anomaly:
        ANOMALIES_TOTAL.labels(metric_name=body.metric).inc()
        try:
            save_anomaly(body.metric, body.value, score)
        except Exception:
            pass
        _fire_alerts(body.metric, body.value, score)

    return {
        "metric": body.metric,
        "value": body.value,
        "score": round(score, 4),
        "anomaly": is_anomaly,
    }


@app.post("/scan", tags=["ml"])
def scan():
    """Fetch all Prometheus metrics and run detection on each."""
    if not detector.is_loaded:
        raise HTTPException(status_code=503, detail="Model not trained — call POST /train first")

    start = time.time()
    try:
        raw = fetch_metrics(settings.prometheus_url)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Prometheus unreachable: {exc}")

    results = []
    for name, val in raw.items():
        METRIC_VALUE.labels(metric_name=name).set(val)
        score, is_anomaly = detector.predict(val)
        ANOMALY_SCORE.labels(metric_name=name).set(score)
        ANOMALY_STATUS.labels(metric_name=name).set(1 if is_anomaly else 0)

        if is_anomaly:
            ANOMALIES_TOTAL.labels(metric_name=name).inc()
            try:
                save_anomaly(name, val, score)
                create_annotation(name, val, score)
            except Exception:
                pass
            _fire_alerts(name, val, score)

        results.append({"metric": name, "value": val, "score": round(score, 4), "anomaly": is_anomaly})

    DETECTION_CYCLES.inc()
    DETECTION_CYCLE_DURATION.observe(time.time() - start)
    return {"results": results, "scanned": len(results)}


@app.get("/anomalies", tags=["history"])
def anomalies(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List stored anomaly history (paginated)."""
    try:
        rows = list_anomalies(limit=limit, offset=offset)
        return {"anomalies": rows, "limit": limit, "offset": offset}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────
def _check_db() -> bool:
    try:
        from app.database import engine
        with engine.connect():
            pass
        DB_HEALTHY.set(1)
        return True
    except Exception:
        DB_HEALTHY.set(0)
        return False


def _fire_alerts(metric: str, value: float, score: float):
    msg = f"🚨 *AIOps Anomaly* | `{metric}` = `{value:.2f}` | score = `{score:.4f}`"
    try:
        if settings.slack_webhook_url:
            send_slack_alert(msg)
    except Exception as exc:
        logger.warning("Slack alert failed: %s", exc)
    try:
        if settings.pagerduty_routing_key:
            send_pagerduty_alert(metric, value, score)
    except Exception as exc:
        logger.warning("PagerDuty alert failed: %s", exc)
