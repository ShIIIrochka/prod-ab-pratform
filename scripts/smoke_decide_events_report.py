#!/usr/bin/env python3
"""
Smoke script: decide -> events -> report.

Run after `docker compose up -d` (and migrations). Uses ADMIN_EMAIL/ADMIN_PASSWORD
to login, creates flag/event-types/metric/experiment, runs decide and events,
then fetches report and checks data_quality.

Env: BASE_URL (default http://localhost:80), ADMIN_EMAIL, ADMIN_PASSWORD.
Exit: 0 on success, 1 on failure.
"""

from __future__ import annotations

import os
import sys

import requests


BASE_URL = os.environ.get("BASE_URL", "http://localhost:80").rstrip("/")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin_pass")

FLAG_KEY = "smoke_button_color"
EXP_NAME = "Smoke Test Experiment"
SUBJECTS = ["smoke-alice", "smoke-bob"]


def log(msg: str) -> None:
    print(f"[smoke] {msg}")


def main() -> int:
    session = requests.Session()
    session.headers["Content-Type"] = "application/json"

    # 1. Login
    log("Logging in...")
    r = session.post(
        f"{BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    if r.status_code != 200:
        log(f"Login failed: {r.status_code} {r.text}")
        return 1
    token = r.json()["access_token"]
    session.headers["Authorization"] = f"Bearer {token}"

    # 2. Create feature flag
    log("Creating feature flag...")
    r = session.post(
        f"{BASE_URL}/feature-flags",
        json={
            "key": FLAG_KEY,
            "value_type": "string",
            "default_value": "green",
        },
        timeout=10,
    )
    if r.status_code not in (201, 400):
        log(f"Feature flag failed: {r.status_code} {r.text}")
        return 1

    # 3. Event types
    for key, name, requires_exp in [
        ("exposure", "Exposure", False),
        ("smoke_conversion", "Smoke Conversion", True),
    ]:
        log(f"Creating event type {key}...")
        r = session.post(
            f"{BASE_URL}/event-types",
            json={
                "key": key,
                "name": name,
                "description": "",
                "required_params": {},
                "requires_exposure": requires_exp,
            },
            timeout=10,
        )
        if r.status_code not in (201, 400):
            log(f"Event type {key} failed: {r.status_code} {r.text}")
            return 1

    # 4. Metric
    log("Creating metric...")
    r = session.post(
        f"{BASE_URL}/metrics",
        json={
            "key": "smoke_conversion_rate",
            "name": "Smoke Conversion Rate",
            "calculation_rule": (
                '{"type":"RATIO","numerator":{"type":"COUNT","event_type_key":"smoke_conversion"},'
                '"denominator":{"type":"COUNT","event_type_key":"exposure"}}'
            ),
            "aggregation_unit": "user",
        },
        timeout=10,
    )
    if r.status_code not in (201, 400):
        log(f"Metric failed: {r.status_code} {r.text}")
        return 1

    # 5. Create experiment
    log("Creating experiment...")
    r = session.post(
        f"{BASE_URL}/experiments",
        json={
            "flag_key": FLAG_KEY,
            "name": EXP_NAME,
            "audience_fraction": 1.0,
            "variants": [
                {
                    "name": "control",
                    "value": "green",
                    "weight": 0.5,
                    "is_control": True,
                },
                {
                    "name": "treatment",
                    "value": "blue",
                    "weight": 0.5,
                    "is_control": False,
                },
            ],
            "target_metric_key": "smoke_conversion_rate",
            "metric_keys": ["smoke_conversion_rate"],
        },
        timeout=10,
    )
    if r.status_code != 201:
        log(f"Experiment create failed: {r.status_code} {r.text}")
        return 1
    exp_id = r.json()["id"]
    log(f"Experiment id: {exp_id}")

    # 6. Review and launch
    for step, path in [
        ("send-to-review", "send-to-review"),
        ("approve", "approve"),
        ("launch", "launch"),
    ]:
        log(f"Experiment {step}...")
        url = f"{BASE_URL}/experiments/{exp_id}/{path}"
        payload = {} if step != "approve" else {"comment": "ok"}
        r = session.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            log(f"Experiment {step} failed: {r.status_code} {r.text}")
            return 1
    if r.json().get("status") != "running":
        log("Experiment not running after launch")
        return 1

    # 7. Decide for subjects
    decisions = {}
    for subj in SUBJECTS:
        r = session.post(
            f"{BASE_URL}/decide",
            json={
                "subject_id": subj,
                "flag_keys": [FLAG_KEY],
                "attributes": {},
            },
            timeout=10,
        )
        if r.status_code != 200:
            log(f"Decide failed: {r.status_code} {r.text}")
            return 1
        dec = r.json().get("decisions", {}).get(FLAG_KEY)
        if not dec:
            log("No decision in response")
            return 1
        decisions[subj] = dec

    # 8. Send events (exposure + conversion)
    import time

    ts = int(time.time())
    events = []
    for subj in SUBJECTS:
        dec = decisions[subj]
        decision_id = dec["id"]
        variant = dec.get("variant_name", "control")
        events.append(
            {
                "event_type_key": "exposure",
                "decision_id": decision_id,
                "timestamp": ts,
                "props": {"variant": variant},
            }
        )
        events.append(
            {
                "event_type_key": "smoke_conversion",
                "decision_id": decision_id,
                "timestamp": ts + 10,
                "props": {},
            }
        )
    r = session.post(
        f"{BASE_URL}/events",
        json={"events": events},
        timeout=10,
    )
    if r.status_code != 200:
        log(f"Events failed: {r.status_code} {r.text}")
        return 1
    body = r.json()
    if body.get("rejected", 0) > 0 and body.get("accepted", 0) == 0:
        log(f"All events rejected: {body}")
        return 1
    log(
        f"Events: accepted={body.get('accepted')}, duplicates={body.get('duplicates')}, rejected={body.get('rejected')}"
    )

    # 9. Report
    from_time = ts - 3600
    to_time = ts + 3600
    r = session.get(
        f"{BASE_URL}/experiments/{exp_id}/report",
        params={"from_time": from_time, "to_time": to_time},
        timeout=10,
    )
    if r.status_code != 200:
        log(f"Report failed: {r.status_code} {r.text}")
        return 1
    report = r.json()
    if not report.get("variants"):
        log("Report has no variants")
        return 1
    dq = report.get("data_quality")
    if dq is None:
        log("Report missing data_quality block")
        return 1
    if dq.get("total_attributed_events", 0) < 1:
        log("No attributed events in report")
        return 1
    log(
        f"Report: variants={len(report['variants'])}, data_quality.total_attributed_events={dq.get('total_attributed_events')}"
    )

    log("Smoke OK: decide -> events -> report passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
