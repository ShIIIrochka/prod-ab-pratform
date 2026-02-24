#!/usr/bin/env python3
"""
Check Experiment Insights / report data_quality and metrics endpoint.

Assumes an experiment with traffic already exists (e.g. run smoke_decide_events_report.py first),
or pass EXPERIMENT_ID and time window. Prints data_quality and /metrics snippet.

Env: BASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD; optional EXPERIMENT_ID, FROM_TIME, TO_TIME (unix).
Exit: 0 on success, 1 on failure.
"""

from __future__ import annotations

import os
import sys
import time

import requests


BASE_URL = os.environ.get("BASE_URL", "http://localhost:80").rstrip("/")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin_pass")
EXPERIMENT_ID = os.environ.get("EXPERIMENT_ID", "")
FROM_TIME = int(os.environ.get("FROM_TIME", str(int(time.time()) - 86400)))
TO_TIME = int(os.environ.get("TO_TIME", str(int(time.time()) + 3600)))


def log(msg: str) -> None:
    print(f"[insights] {msg}")


def main() -> int:
    session = requests.Session()
    session.headers["Content-Type"] = "application/json"

    log("Logging in...")
    r = session.post(
        f"{BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    if r.status_code != 200:
        log(f"Login failed: {r.status_code} {r.text}")
        return 1
    session.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    if not EXPERIMENT_ID:
        log(
            "No EXPERIMENT_ID; listing experiments to pick first running one..."
        )
        r = session.get(f"{BASE_URL}/experiments", timeout=10)
        if r.status_code != 200:
            log(f"List experiments failed: {r.status_code} {r.text}")
            return 1
        experiments = r.json()
        running = [e for e in experiments if e.get("status") == "running"]
        if not running:
            log(
                "No running experiment. Run smoke_decide_events_report.py first or set EXPERIMENT_ID."
            )
            return 1
        exp_id = running[0]["id"]
        log(f"Using experiment {exp_id}")
    else:
        exp_id = EXPERIMENT_ID

    log(f"Fetching report from_time={FROM_TIME} to_time={TO_TIME}...")
    r = session.get(
        f"{BASE_URL}/experiments/{exp_id}/report",
        params={"from_time": FROM_TIME, "to_time": TO_TIME},
        timeout=10,
    )
    if r.status_code != 200:
        log(f"Report failed: {r.status_code} {r.text}")
        return 1
    report = r.json()
    dq = report.get("data_quality")
    if dq:
        log(
            f"data_quality: total_attributed_events={dq.get('total_attributed_events')}"
        )
        log(
            f"data_quality: variant_event_counts={dq.get('variant_event_counts')}"
        )
    else:
        log("Report has no data_quality block.")
    log(f"Variants: {len(report.get('variants', []))}")

    log("Fetching /metrics (first 2K)...")
    r = session.get(f"{BASE_URL}/metrics", timeout=5)
    if r.status_code != 200:
        log(f"Metrics failed: {r.status_code}")
        return 1
    text = r.text[:2048]
    for name in (
        "events_received_total",
        "events_rejected_total",
        "events_duplicated_total",
        "experiment_exposures_total",
    ):
        if name in text:
            log(f"  Found metric: {name}")

    log("Insights check OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
