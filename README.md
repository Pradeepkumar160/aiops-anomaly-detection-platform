# 🤖 AIOps Anomaly Detection Platform                        

> **ML-powered Kubernetes infrastructure monitoring** — detect anomalies in Prometheus metrics in real-time, fire alerts to Slack & PagerDuty, and auto-annotate Grafana dashboards.

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/scikit--learn-IsolationForest-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white"/>
  <img src="https://img.shields.io/badge/Kubernetes-Deployment-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white"/>
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white"/>
  <img src="https://img.shields.io/badge/Prometheus-Monitoring-E6522C?style=for-the-badge&logo=prometheus&logoColor=white"/>
  <img src="https://img.shields.io/badge/Grafana-Dashboards-F46800?style=for-the-badge&logo=grafana&logoColor=white"/>
  <img src="https://img.shields.io/badge/PostgreSQL-Storage-4169E1?style=for-the-badge&logo=postgresql&logoColor=white"/>
</p>

---

## 📌 What It Does

The **AIOps Anomaly Detection Platform** continuously scrapes live Prometheus metrics from your Kubernetes cluster, runs them through a trained **Isolation Forest** ML model, and instantly alerts your team when something looks wrong — no manual thresholds, no noise.

- 🔍 **Auto-detects** CPU spikes, memory leaks, disk pressure, network errors, pod crash-loops
- 🧠 **ML-based** anomaly scoring (not brittle static thresholds)
- 📣 **Fires alerts** to Slack and PagerDuty the moment an anomaly is detected
- 📊 **Annotates Grafana** dashboards automatically for visual context
- 🕒 **Runs on a schedule** — every 60 seconds by default, fully configurable
- 🗃️ **Persists history** to PostgreSQL for trend analysis

---

## 🏗️ Architecture

```
Kubernetes Cluster / Docker Compose
         │
         ▼
  Prometheus ──── Node Exporter
         │
         ▼
  AIOps Engine (Python / FastAPI)
    ├── Isolation Forest (sklearn)   ← anomaly scoring
    ├── Prophet (time-series)        ← optional forecasting
    └── APScheduler                  ← detection every 60s
         │
         ├──► Slack Webhook          ← instant team alerts
         ├──► PagerDuty Events API   ← on-call escalation
         ├──► Grafana Annotations    ← visual markers on dashboards
         └──► PostgreSQL             ← anomaly history & audit log
```

---

## 📁 Project Structure

```
aiops-platform/
├── app/
│   ├── config.py              # Centralised env-var settings (Pydantic)
│   ├── main.py                # FastAPI REST API + Prometheus metrics
│   ├── scheduler.py           # Background detection loop (APScheduler)
│   ├── prom_query.py          # PromQL query helpers
│   ├── anomaly_detector.py    # Isolation Forest + Prophet logic
│   ├── alert_manager.py       # Slack + PagerDuty alert dispatch
│   ├── grafana.py             # Grafana annotation client
│   └── database.py            # PostgreSQL CRUD (SQLAlchemy)
├── models/                    # Persisted .pkl model files
├── data/                      # Optional CSV for offline training
├── docker/
│   └── Dockerfile             # Multi-stage production build
├── kubernetes/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml.example
│   ├── deployment.yaml        # API + Scheduler deployments
│   ├── service.yaml
│   ├── pvc.yaml
│   └── hpa.yaml               # Horizontal Pod Autoscaler
├── prometheus/
│   └── prometheus.yml         # Scrape configs
├── grafana/
│   └── provisioning/
│       ├── datasources/datasource.yaml
│       └── dashboards/
│           ├── dashboards.yaml
│           └── aiops_overview.json
├── scripts/
│   ├── train_initial_model.py # Bootstrap model training
│   └── simulate_anomaly.py    # Inject fake anomalies for testing
├── .env.example
├── .gitignore
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Monitoring | Prometheus, Node Exporter, Grafana |
| ML Engine | Isolation Forest (scikit-learn), Prophet |
| API | FastAPI, Uvicorn |
| Storage | PostgreSQL (SQLAlchemy ORM) |
| Alerting | Slack Webhooks, PagerDuty Events API v2 |
| Scheduling | APScheduler |
| Containerisation | Docker, Docker Compose |
| Orchestration | Kubernetes (Deployments, HPA, PVC) |

---

## ⚡ Quick Start — Docker Compose

### 1. Clone & Configure

```bash
git clone https://github.com/Pradeepkumar160/aiops-anomaly-detection-platform.git
cd aiops-anomaly-detection-platform
cp .env.example .env
# Fill in your Slack webhook, PagerDuty key, Grafana token
```

### 2. Build & Run

```bash
docker-compose up --build
```

### 3. Access Services

| Service | URL | Default Credentials |
|---|---|---|
| AIOps API + Swagger | http://localhost:8000/docs | — |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3000 | admin / admin |
| PostgreSQL | localhost:5432 | postgres / password |

### 4. Test Anomaly Detection

```bash
# Health check
curl http://localhost:8000/health

# Live metrics from Prometheus
curl http://localhost:8000/metrics/current

# Inject a fake high CPU value to trigger an alert
python scripts/simulate_anomaly.py --metric cpu_usage --value 95.0

# View anomaly history
curl http://localhost:8000/anomalies
```

---

## ☸️ Kubernetes Deployment

### 1. Build & Push Your Image

```bash
docker build -t your-registry/aiops-platform:latest -f docker/Dockerfile .
docker push your-registry/aiops-platform:latest
```

> Update the `image:` field in `kubernetes/deployment.yaml` to match your registry path.

### 2. Create Namespace & Secrets

```bash
kubectl apply -f kubernetes/namespace.yaml

kubectl create secret generic aiops-secrets -n aiops \
  --from-literal=slack-webhook-url='YOUR_SLACK_WEBHOOK_URL' \
  --from-literal=pagerduty-routing-key='YOUR_PAGERDUTY_KEY' \
  --from-literal=grafana-api-token='YOUR_GRAFANA_TOKEN' \
  --from-literal=postgres-password='YOUR_DB_PASSWORD'
```

### 3. Apply All Manifests

```bash
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/pvc.yaml
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
kubectl apply -f kubernetes/hpa.yaml
```

### 4. Verify

```bash
kubectl get pods -n aiops
kubectl logs -f deployment/aiops-api -n aiops
kubectl logs -f deployment/aiops-scheduler -n aiops
```

---

## 🔌 API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check — DB + model status |
| `GET` | `/anomalies` | List stored anomalies (paginated) |
| `POST` | `/detect` | Run detection on a single value |
| `POST` | `/scan` | Full detection scan against Prometheus |
| `POST` | `/train` | Train or retrain the ML model |
| `GET` | `/metrics/current` | Fetch all live Prometheus metric values |
| `GET` | `/docs` | Interactive Swagger UI |

### Train the Model

```bash
curl -X POST http://localhost:8000/train \
  -H "Content-Type: application/json" \
  -d '{"values": [30,32,28,35,31,33,29,30,32,31,29,34,30,32,28,35,31,33,29,30]}'
```

### Detect a Single Value

```bash
curl -X POST http://localhost:8000/detect \
  -H "Content-Type: application/json" \
  -d '{"metric": "cpu_usage", "value": 92.5}'
```

---

## 📡 Monitored Metrics

| Metric | PromQL Expression |
|---|---|
| CPU Usage | `100 - avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100` |
| Memory Usage | `100 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100` |
| Disk Usage | `100 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100` |
| Network Errors | `sum(rate(node_network_transmit_errs_total[5m])) + sum(rate(node_network_receive_errs_total[5m]))` |
| Pod Restarts | `sum(kube_pod_container_status_restarts_total)` |
| HTTP 5xx Errors | `sum(rate(http_requests_total{status=~"5.."}[5m]))` |

---

## ⚙️ Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `PROMETHEUS_URL` | `http://prometheus:9090` | Prometheus base URL |
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |
| `GRAFANA_URL` | `http://grafana:3000` | Grafana base URL |
| `SLACK_WEBHOOK_URL` | — | Slack Incoming Webhook URL |
| `PAGERDUTY_ROUTING_KEY` | — | PagerDuty Events API v2 routing key |
| `GRAFANA_API_TOKEN` | — | Grafana service account token |
| `DETECTION_INTERVAL_SECONDS` | `60` | Detection loop frequency |
| `CONTAMINATION` | `0.02` | Expected anomaly fraction (0.0–0.5) |

---

## 📝 Notes

- **Credentials**: Populate `.env` (Docker Compose) or Kubernetes secrets before starting — the app will fail health checks without them.
- **Model retraining**: The bootstrapped model is a seed. Call `POST /train` with real historical metric data for production-grade accuracy.
- **Prophet (optional)**: Adds ~200 MB to the image. Remove from `requirements.txt` if time-series forecasting isn't needed.
- **Scrape targets**: Edit `prometheus/prometheus.yml` to add your real Kubernetes nodes, cAdvisor endpoints, or application services.
- **Never commit `.env`** — it's in `.gitignore`. Use `.env.example` as the template.

---

## 👤 Author

**Pradeep Kumar** — [GitHub](https://github.com/Pradeepkumar160) · [LinkedIn](https://linkedin.com/in/07pradeepk/)

> Final-year B.Tech CSE @ Lovely Professional University · Full-Stack | DevOps | AI/ML

---

<p align="center">⭐ If this project helped you, consider giving it a star!</p>
