## Observability & Experiment Insights Runbook

### 1. Startup

- **Build & start stack**
  - `docker compose up --build`
- **Services**
  - `api` — FastAPI A/B backend (`http://localhost:80`)
  - `postgres` — DB (`localhost:5432`)
  - `prometheus` — metrics (`http://localhost:9090`)
  - `grafana` — UI (`http://localhost:3000`, login `admin/admin`)

### 2. Health & Readiness

- **Liveness**
  - `curl -i http://localhost:80/health`
  - Expected: `200 OK`, body `{"status": "ok"}`
- **Readiness**
  - `curl -i http://localhost:80/ready`
  - When DB & OpenSearch are reachable:
    - `200 OK`, body `{"status": "ready", "db_ok": true, "opensearch_ok": true}`
  - If DB or OpenSearch are down:
    - `503 Service Unavailable`, body `{"status": "not_ready", "db_ok": ..., "opensearch_ok": ...}`

### 3. Prometheus Metrics

- **Endpoint**
  - `curl http://localhost:80/metrics`
  - Should return Prometheus text format with:
    - `http_requests_total`
    - `http_errors_total`
    - `decide_requests_total`
    - `events_received_total`
    - `events_rejected_total`
    - `guardrail_triggered_total`
    - `experiment_exposures_total`
    - `active_experiments`
- **Generate traffic**
  - Call `/decide` and `/events` according to API docs to see counters increase.

### 4. Prometheus Scrape

- Config is in `prometheus.yml`
  - Job: `ab-platform-api`
  - Target: `api:80`, `metrics_path: /metrics`
- Verify in Prometheus UI:
  - Open `http://localhost:9090`
  - Run query: `http_requests_total` — should show series by `method`, `path`, `status_code`.

### 5. Grafana Experiment Insights Dashboard

- Import dashboard JSON:
  - Open Grafana → `Dashboards` → `New` → `Import`
  - Paste JSON from `docs/grafana_experiment_insights_dashboard.json`
  - Set Prometheus as the data source.
- Panels:
  - Exposures per variant (`experiment_exposures_total`)
  - Conversions per variant (`experiment_conversions_total` if configured)
  - Conversion rate per variant
  - Guardrail triggers (`guardrail_triggered_total`)
  - HTTP errors (`http_errors_total`)
  - Rejected events (`events_rejected_total`)
  - Variant distribution (bar gauge on `experiment_exposures_total`)

### 6. Demo Scenario (B9-3 + FX-8)

1. Ensure stack is up (`docker compose ps`).
2. Check `/health` and `/ready`.
3. Trigger several `/decide` and `/events` requests for a running experiment.
4. Confirm in Prometheus:
   - `decide_requests_total` and `experiment_exposures_total` are growing.
5. Open Grafana dashboard:
   - See exposures and conversion metrics split by `experiment_id` and `variant`.
   - Observe guardrail triggers and rejected events if you run negative scenarios.

