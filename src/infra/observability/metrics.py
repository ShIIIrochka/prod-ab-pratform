from __future__ import annotations

from prometheus_client import Counter, Gauge


http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests.",
    ["method", "path", "status_code"],
)

http_errors_total = Counter(
    "http_errors_total",
    "Total number of HTTP responses with 5xx status codes.",
    ["method", "path", "status_code"],
)

decide_requests_total = Counter(
    "decide_requests_total",
    "Total number of /decide requests.",
)

events_received_total = Counter(
    "events_received_total",
    "Total number of events received by /events endpoint.",
)

events_rejected_total = Counter(
    "events_rejected_total",
    "Total number of rejected events in /events endpoint.",
)

events_duplicated_total = Counter(
    "events_duplicated_total",
    "Total number of duplicate events (deduplicated) in /events endpoint.",
)

guardrail_triggered_total = Counter(
    "guardrail_triggered_total",
    "Total number of guardrail triggers.",
    ["metric_key", "action"],
)

experiment_exposures_total = Counter(
    "experiment_exposures_total",
    "Total number of experiment exposures.",
    ["experiment_id", "variant"],
)

active_experiments = Gauge(
    "active_experiments",
    "Number of currently running experiments.",
)
